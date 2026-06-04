"""
Feature engineering service.
Covers: log/Box-Cox transforms, scaling (Standard/MinMax/Robust),
categorical encoding (OHE, ordinal, target), datetime decomposition,
and feature selection (correlation filter + variance filter).
"""
import math
from pathlib import Path
import pandas as pd
import numpy as np
from app.services.store import ensure_dataset_file
from app.services.object_storage import upload_dataset_artifact
from typing import Any

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "datasets"


def _numeric(series: pd.Series, dropna: bool = False) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
    return s.dropna() if dropna else s


def _nonconstant_numeric_frame(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    sub = df[cols].apply(lambda s: _numeric(s))
    usable = [c for c in sub.columns if sub[c].dropna().nunique() > 1]
    return sub[usable]


def _safe(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    return v


def _load_df(dataset_id: str) -> pd.DataFrame | None:
    p = DATA_DIR / f"{dataset_id}.parquet"
    if not p.exists():
        ensure_dataset_file(dataset_id, p.name)
    if p.exists():
        return pd.read_parquet(p)
    c = DATA_DIR / f"{dataset_id}.csv"
    if not c.exists():
        ensure_dataset_file(dataset_id, c.name)
    if c.exists():
        return pd.read_csv(c)
    return None


# ── Preview helpers ────────────────────────────────────────────────────────────

def _preview_numeric_transform(series: pd.Series, transform: str) -> dict:
    """Return before/after sample stats for a numeric transform."""
    s = _numeric(series, dropna=True)
    if len(s) == 0:
        return {"error": "No numeric values"}

    before = {"min": _safe(s.min()), "max": _safe(s.max()),
               "mean": _safe(s.mean()), "std": _safe(s.std()),
               "skewness": _safe(s.skew())}

    try:
        if transform == "log":
            if (s <= 0).any():
                # shift so min = 1
                shift = 1 - s.min()
                result = np.log1p(s + shift)
                note = f"Applied log1p(x + {round(shift, 4)}) to handle non-positive values"
            else:
                result = np.log(s)
                note = "Applied log(x)"
        elif transform == "log1p":
            if (s < 0).any():
                return {"error": "log1p requires non-negative values"}
            result = np.log1p(s)
            note = "Applied log1p(x)"
        elif transform == "sqrt":
            if (s < 0).any():
                return {"error": "sqrt requires non-negative values"}
            result = np.sqrt(s)
            note = "Applied sqrt(x)"
        elif transform == "boxcox":
            from scipy.stats import boxcox
            if (s <= 0).any():
                shift = 1 - s.min()
                result, lam = boxcox(s + shift)
                note = f"Box-Cox λ={round(lam, 4)}, shifted by {round(shift, 4)}"
            else:
                result, lam = boxcox(s)
                note = f"Box-Cox λ={round(lam, 4)}"
            result = pd.Series(result)
        elif transform == "standard":
            std = s.std()
            result = (s - s.mean()) / std if std != 0 else s * 0
            note = f"StandardScaler: mean={round(s.mean(), 4)}, std={round(std, 4)}"
        elif transform == "minmax":
            mn, mx = s.min(), s.max()
            result = (s - mn) / (mx - mn) if mx != mn else s * 0
            note = f"MinMaxScaler: [{round(mn, 4)}, {round(mx, 4)}] → [0, 1]"
        elif transform == "robust":
            q25, q75 = s.quantile(0.25), s.quantile(0.75)
            iqr = q75 - q25
            result = (s - s.median()) / iqr if iqr != 0 else s * 0
            note = f"RobustScaler: median={round(s.median(), 4)}, IQR={round(iqr, 4)}"
        else:
            return {"error": f"Unknown transform: {transform}"}

        after = {"min": _safe(result.min()), "max": _safe(result.max()),
                 "mean": _safe(result.mean()), "std": _safe(result.std()),
                 "skewness": _safe(result.skew())}
        return {"before": before, "after": after, "note": note}

    except Exception as e:
        return {"error": str(e)}


def suggest_feature_ops(df: pd.DataFrame, schema: list, ignored_op_ids: list | None = None, target: str | None = None) -> list:
    """Generate feature engineering suggestions for the dataset."""
    suggestions = []
    ignored = set(ignored_op_ids or [])

    def has_any(*cols: str) -> bool:
        return any(c in df.columns for c in cols)

    def add_suggestion(item: dict) -> None:
        if item["id"] not in ignored:
            suggestions.append(item)

    for col_info in schema:
        col = col_info["name"]
        if col not in df.columns:
            continue
        if target and col == target:
            continue
        if "__" in col:
            continue
        ctype = col_info["type"]
        null_count = int(df[col].isna().sum())

        # Missingness can be predictive, especially when nulls are systematic.
        if null_count > 0 and not has_any(f"{col}__missing"):
            add_suggestion({
                "id": f"missing_indicator::{col}",
                "column": col,
                "op": "missing_indicator",
                "label": f'Add missingness indicator for "{col}"',
                "detail": f"{null_count} missing rows → binary flag for possible MNAR signal.",
                "category": "missingness",
            })

        # Skewed numeric → suggest transform
        if ctype in ("integer", "float"):
            skew = col_info.get("skewness")
            if skew is not None and abs(skew) > 1.0:
                rec = "log" if col_info.get("min", 0) > 0 else "log_shift"
                new_col = f"{col}__{rec}"
                if not has_any(new_col):
                    add_suggestion({
                        "id": f"transform::{col}::{rec}",
                        "column": col,
                        "op": "transform",
                        "transform": rec,
                        "label": f'Log-transform "{col}"',
                        "detail": f"Skewness = {skew}. Uses a safe shift when values are non-positive.",
                        "category": "transform",
                        "preview": _preview_numeric_transform(df[col], "log" if rec == "log_shift" else rec),
                    })

            # Suggest StandardScaler for any non-binary numeric
            nuniq = df[col].nunique()
            if nuniq > 2 and not has_any(f"{col}__scaled"):
                add_suggestion({
                    "id": f"scale::{col}::standard",
                    "column": col,
                    "op": "scale",
                    "transform": "standard",
                    "label": f'Standardize "{col}" (z-score)',
                    "detail": "Centres to mean=0, std=1. Good for most ML algorithms.",
                    "category": "scale",
                    "preview": _preview_numeric_transform(df[col], "standard"),
                })
            if nuniq >= 10 and not has_any(f"{col}__qbin"):
                add_suggestion({
                    "id": f"bin::{col}::quantile",
                    "column": col,
                    "op": "bin",
                    "method": "quantile",
                    "label": f'Quantile-bin "{col}"',
                    "detail": "Creates 5 ordered bins to capture non-linear numeric patterns.",
                    "category": "bin",
                })

        # Categorical encoding
        if ctype in ("categorical", "text", "boolean"):
            nuniq = df[col].nunique()
            target_is_usable = target and target in df.columns and target != col and df[target].notna().sum() >= 8
            if nuniq <= 10:
                already_encoded = any(c.startswith(f"{col}_") for c in df.columns)
                if already_encoded:
                    continue
                add_suggestion({
                    "id": f"encode::{col}::ohe",
                    "column": col,
                    "op": "encode",
                    "encoding": "ohe",
                    "label": f'One-hot encode "{col}"',
                    "detail": f"{nuniq} unique values → {nuniq} binary columns.",
                    "category": "encode",
                })
            else:
                if target_is_usable and not has_any(f"{col}__target_enc"):
                    add_suggestion({
                        "id": f"target_encode::{col}::{target}",
                        "column": col,
                        "op": "target_encode",
                        "encoding": "target",
                        "label": f'Target encode "{col}"',
                        "detail": f'Uses leakage-reduced category means against target "{target}".',
                        "category": "encode",
                    })
                    continue
                if has_any(f"{col}__freq"):
                    continue
                add_suggestion({
                    "id": f"encode::{col}::frequency",
                    "column": col,
                    "op": "encode",
                    "encoding": "frequency",
                    "label": f'Frequency encode "{col}"',
                    "detail": f"{nuniq} unique values. Replaces categories with their observed frequency.",
                    "category": "encode",
                })

        # Datetime decomposition
        if ctype == "datetime":
            if has_any(f"{col}__year", f"{col}__month", f"{col}__day", f"{col}__dayofweek"):
                continue
            add_suggestion({
                "id": f"datetime::{col}",
                "column": col,
                "op": "datetime_decompose",
                "label": f'Decompose "{col}" into date parts',
                "detail": "Extracts year, month, day, day_of_week, hour (if time present).",
                "category": "datetime",
            })

    # Time-series lag/window features: conservative, only first datetime x first few numeric columns.
    datetime_cols = [c["name"] for c in schema if c.get("type") == "datetime" and c["name"] in df.columns and "__" not in c["name"]]
    numeric_base_cols = [
        c["name"] for c in schema
        if c.get("type") in ("integer", "float") and c["name"] in df.columns and "__" not in c["name"]
    ]
    if datetime_cols and numeric_base_cols:
        date_col = datetime_cols[0]
        for col in numeric_base_cols[:3]:
            if not has_any(f"{col}__lag1"):
                add_suggestion({
                    "id": f"timeseries::{date_col}::{col}::lag1",
                    "column": col,
                    "op": "timeseries",
                    "label": f'Create lag-1 feature for "{col}"',
                    "detail": f'Sorts by "{date_col}" and shifts {col} by one row.',
                    "category": "timeseries",
                })
            if not has_any(f"{col}__roll3_mean"):
                add_suggestion({
                    "id": f"timeseries::{date_col}::{col}::roll3",
                    "column": col,
                    "op": "timeseries",
                    "label": f'Create rolling mean for "{col}"',
                    "detail": f'Sorts by "{date_col}" and creates 3-row rolling mean.',
                    "category": "timeseries",
                })

    # Feature selection: high-correlation pairs (suggest dropping weaker)
    numeric_cols = [
        c["name"] for c in schema
        if c["type"] in ("integer", "float") and c["name"] in df.columns and "__" not in c["name"]
    ]
    if len(numeric_cols) >= 2:
        sub = _nonconstant_numeric_frame(df, numeric_cols)
        numeric_cols = list(sub.columns)
    if len(numeric_cols) >= 2:
        corr = sub.corr().abs()
        seen = set()
        for i, a in enumerate(numeric_cols):
            for b in numeric_cols[i+1:]:
                key = tuple(sorted([a, b]))
                if key in seen:
                    continue
                seen.add(key)
                v = corr.loc[a, b] if a in corr.index and b in corr.columns else None
                if v is not None and v >= 0.9:
                    # drop the one with lower variance
                    var_a = _safe(sub[a].var())
                    var_b = _safe(sub[b].var())
                    drop = b if (var_a or 0) >= (var_b or 0) else a
                    add_suggestion({
                        "id": f"drop_redundant::{drop}",
                        "column": drop,
                        "op": "drop_redundant",
                        "label": f'Drop redundant column "{drop}"',
                        "detail": f'Correlation with {"" + a if drop == b else b} = {round(float(v), 2)}. Highly redundant.',
                        "category": "selection",
                    })

    # Zero/near-zero variance filter
    for col_info in schema:
        col = col_info["name"]
        if col not in df.columns or "__" in col or col_info["type"] not in ("integer", "float"):
            continue
        s = _numeric(df[col], dropna=True)
        if len(s) > 0:
            cv = s.std() / s.mean() if s.mean() != 0 else 0
            if abs(cv) < 0.01 and s.nunique() <= 2:
                add_suggestion({
                    "id": f"drop_low_variance::{col}",
                    "column": col,
                    "op": "drop_low_variance",
                    "label": f'Drop near-constant column "{col}"',
                    "detail": f"Coefficient of variation = {round(abs(cv), 4)}. Adds almost no information.",
                    "category": "selection",
                })

    return suggestions


def apply_feature_ops(dataset_id: str, op_ids: list, schema: list) -> dict:
    """Apply selected feature engineering operations, return new column info."""
    df = _load_df(dataset_id)
    if df is None:
        return {"error": "Dataset not found"}

    df = df.copy()
    log = []
    applied: list[str] = []
    new_cols: list[dict[str, Any]] = []

    for op_id in op_ids:
        parts = op_id.split("::")
        op = parts[0]

        # ── Drop ops ──────────────────────────────────────────────────────────
        if op in ("drop_redundant", "drop_low_variance"):
            col = parts[1]
            if col in df.columns:
                df = df.drop(columns=[col])
                log.append(f'Dropped column "{col}"')
                applied.append(op_id)

        # ── Numeric transforms ────────────────────────────────────────────────
        elif op == "transform":
            col, transform = parts[1], parts[2]
            if col not in df.columns:
                continue
            s = _numeric(df[col])
            new_col = f"{col}__{transform}"
            if new_col in df.columns:
                log.append(f'Skipped "{new_col}" because it already exists')
                continue
            try:
                if transform in ("log", "log_shift"):
                    shift = max(0, 1 - s.min())
                    df[new_col] = np.log(s + shift)
                    log.append(f'Created "{new_col}" = log({col} + {round(shift, 4)})')
                elif transform == "log1p":
                    if (s <= -1).any():
                        shift = -s.min()
                        df[new_col] = np.log1p(s + shift)
                        log.append(f'Created "{new_col}" = log1p({col} + {round(shift, 4)})')
                    else:
                        df[new_col] = np.log1p(s)
                        log.append(f'Created "{new_col}" = log1p({col})')
                elif transform == "sqrt":
                    df[new_col] = np.sqrt(s.clip(lower=0))
                    log.append(f'Created "{new_col}" = sqrt({col})')
                elif transform == "boxcox":
                    from scipy.stats import boxcox
                    shift = max(0, 1 - s.dropna().min())
                    vals, lam = boxcox(s.dropna() + shift)
                    df[new_col] = np.nan
                    df.loc[s.notna(), new_col] = vals
                    log.append(f'Created "{new_col}" = BoxCox({col}, λ={round(lam, 4)})')
                new_cols.append({"name": new_col, "source": col, "op": transform})
                applied.append(op_id)
            except Exception as e:
                log.append(f'Transform "{transform}" on "{col}" failed: {e}')

        # ── Missingness indicators ───────────────────────────────────────────
        elif op == "missing_indicator":
            col = parts[1]
            if col not in df.columns:
                continue
            new_col = f"{col}__missing"
            if new_col in df.columns:
                log.append(f'Skipped "{new_col}" because it already exists')
                continue
            df[new_col] = df[col].isna().astype(int)
            new_cols.append({"name": new_col, "source": col, "op": "missing_indicator"})
            log.append(f'Created "{new_col}" = 1 when {col} is missing')
            applied.append(op_id)

        # ── Numeric binning ─────────────────────────────────────────────────
        elif op == "bin":
            col, method = parts[1], parts[2]
            if col not in df.columns:
                continue
            new_col = f"{col}__qbin"
            if new_col in df.columns:
                log.append(f'Skipped "{new_col}" because it already exists')
                continue
            try:
                s = _numeric(df[col])
                if method == "quantile":
                    bins = pd.qcut(s, q=min(5, max(2, s.nunique())), labels=False, duplicates="drop")
                    df[new_col] = bins
                    new_cols.append({"name": new_col, "source": col, "op": "quantile_bin"})
                    log.append(f'Created "{new_col}" = quantile bins for {col}')
                    applied.append(op_id)
            except Exception as e:
                log.append(f'Binning "{col}" failed: {e}')

        # ── Scaling ──────────────────────────────────────────────────────────
        elif op == "scale":
            col, method = parts[1], parts[2]
            if col not in df.columns:
                continue
            s = _numeric(df[col])
            new_col = f"{col}__scaled"
            if new_col in df.columns:
                log.append(f'Skipped "{new_col}" because it already exists')
                continue
            try:
                if method == "standard":
                    mean, std = s.mean(), s.std()
                    df[new_col] = (s - mean) / std if std != 0 else s * 0
                    log.append(f'Created "{new_col}" = StandardScaler({col})')
                elif method == "minmax":
                    mn, mx = s.min(), s.max()
                    df[new_col] = (s - mn) / (mx - mn) if mx != mn else s * 0
                    log.append(f'Created "{new_col}" = MinMaxScaler({col})')
                elif method == "robust":
                    med = s.median()
                    iqr = s.quantile(0.75) - s.quantile(0.25)
                    df[new_col] = (s - med) / iqr if iqr != 0 else s * 0
                    log.append(f'Created "{new_col}" = RobustScaler({col})')
                new_cols.append({"name": new_col, "source": col, "op": f"scale_{method}"})
                applied.append(op_id)
            except Exception as e:
                log.append(f'Scale "{method}" on "{col}" failed: {e}')

        # ── Encoding ─────────────────────────────────────────────────────────
        elif op == "encode":
            col, method = parts[1], parts[2]
            if col not in df.columns:
                continue
            try:
                if method == "ohe":
                    dummies = pd.get_dummies(df[col], prefix=col, dtype=int)
                    dummies = dummies[[c for c in dummies.columns if c not in df.columns]]
                    if dummies.empty:
                        log.append(f'Skipped one-hot encoding "{col}" because encoded columns already exist')
                        continue
                    df = pd.concat([df, dummies], axis=1)
                    for c in dummies.columns:
                        new_cols.append({"name": c, "source": col, "op": "ohe"})
                    log.append(f'One-hot encoded "{col}" → {list(dummies.columns)}')
                    applied.append(op_id)
                elif method == "ordinal":
                    cats = df[col].dropna().unique()
                    mapping = {v: i for i, v in enumerate(sorted(cats, key=str))}
                    new_col = f"{col}__ordinal"
                    if new_col in df.columns:
                        log.append(f'Skipped "{new_col}" because it already exists')
                        continue
                    df[new_col] = df[col].map(mapping)
                    new_cols.append({"name": new_col, "source": col, "op": "ordinal"})
                    log.append(f'Ordinal encoded "{col}" → "{new_col}" ({len(mapping)} levels)')
                    applied.append(op_id)
                elif method == "frequency":
                    new_col = f"{col}__freq"
                    if new_col in df.columns:
                        log.append(f'Skipped "{new_col}" because it already exists')
                        continue
                    freq = df[col].value_counts(normalize=True, dropna=True)
                    df[new_col] = df[col].map(freq).fillna(0)
                    new_cols.append({"name": new_col, "source": col, "op": "frequency"})
                    log.append(f'Frequency encoded "{col}" → "{new_col}"')
                    applied.append(op_id)
            except Exception as e:
                log.append(f'Encode "{method}" on "{col}" failed: {e}')

        # ── Target encoding ─────────────────────────────────────────────────
        elif op == "target_encode":
            col, target = parts[1], parts[2]
            if col not in df.columns or target not in df.columns or col == target:
                continue
            new_col = f"{col}__target_enc"
            if new_col in df.columns:
                log.append(f'Skipped "{new_col}" because it already exists')
                continue
            try:
                y_raw = df[target]
                if pd.api.types.is_numeric_dtype(y_raw):
                    y = pd.to_numeric(y_raw, errors="coerce").replace([np.inf, -np.inf], np.nan)
                else:
                    top_class = y_raw.dropna().astype(str).value_counts().index[0]
                    y = (y_raw.astype(str) == top_class).astype(float).where(y_raw.notna())

                work = pd.DataFrame({"cat": df[col], "target": y})
                global_mean = float(work["target"].mean())
                grouped = work.groupby("cat")["target"].agg(["sum", "count"])
                sums = df[col].map(grouped["sum"]).astype(float)
                counts = df[col].map(grouped["count"]).astype(float)
                own = y.astype(float)
                # Leave-one-out with smoothing toward global mean.
                smoothing = 10.0
                numerator = (sums - own.fillna(0)) + global_mean * smoothing
                denominator = (counts - own.notna().astype(float)).clip(lower=0) + smoothing
                encoded = numerator / denominator
                df[new_col] = encoded.fillna(global_mean)
                new_cols.append({"name": new_col, "source": col, "op": "target_encode", "target": target})
                log.append(f'Target encoded "{col}" using "{target}" → "{new_col}"')
                applied.append(op_id)
            except Exception as e:
                log.append(f'Target encoding "{col}" failed: {e}')

        # ── Datetime decomposition ─────────────────────────────────────────
        elif op in ("datetime", "datetime_decompose"):
            col = parts[1]
            if col not in df.columns:
                continue
            try:
                dt = pd.to_datetime(df[col], errors="coerce")
                created = []
                for part, extractor in [
                    ("year", lambda s: s.dt.year),
                    ("month", lambda s: s.dt.month),
                    ("day", lambda s: s.dt.day),
                    ("dayofweek", lambda s: s.dt.dayofweek),
                    ("hour", lambda s: s.dt.hour),
                ]:
                    new_col = f"{col}__{part}"
                    if new_col in df.columns:
                        continue
                    vals = extractor(dt)
                    if part != "hour" or vals.max() > 0:
                        df[new_col] = vals
                        new_cols.append({"name": new_col, "source": col, "op": f"dt_{part}"})
                        created.append(new_col)
                if created:
                    log.append(f'Decomposed datetime "{col}" into date parts')
                    applied.append(op_id)
                else:
                    log.append(f'Skipped datetime decomposition for "{col}" because date parts already exist')
            except Exception as e:
                log.append(f'Datetime decompose on "{col}" failed: {e}')

        # ── Time-series lag/window features ─────────────────────────────────
        elif op == "timeseries":
            date_col, col, method = parts[1], parts[2], parts[3]
            if date_col not in df.columns or col not in df.columns:
                continue
            try:
                ordered = df.assign(__dt_sort=pd.to_datetime(df[date_col], errors="coerce")).sort_values("__dt_sort")
                s = _numeric(ordered[col])
                if method == "lag1":
                    new_col = f"{col}__lag1"
                    if new_col in df.columns:
                        log.append(f'Skipped "{new_col}" because it already exists')
                        continue
                    ordered[new_col] = s.shift(1)
                    df[new_col] = ordered.sort_index()[new_col]
                    new_cols.append({"name": new_col, "source": col, "op": "lag1"})
                    log.append(f'Created "{new_col}" sorted by "{date_col}"')
                    applied.append(op_id)
                elif method == "roll3":
                    new_col = f"{col}__roll3_mean"
                    if new_col in df.columns:
                        log.append(f'Skipped "{new_col}" because it already exists')
                        continue
                    ordered[new_col] = s.rolling(window=3, min_periods=1).mean()
                    df[new_col] = ordered.sort_index()[new_col]
                    new_cols.append({"name": new_col, "source": col, "op": "roll3_mean"})
                    log.append(f'Created "{new_col}" sorted by "{date_col}"')
                    applied.append(op_id)
            except Exception as e:
                log.append(f'Time-series feature "{method}" on "{col}" failed: {e}')

    # Save engineered dataset
    feat_path = DATA_DIR / f"{dataset_id}_feat.parquet"
    try:
        df.to_parquet(feat_path, index=False)
        upload_dataset_artifact(dataset_id, feat_path)
    except Exception:
        feat_path = DATA_DIR / f"{dataset_id}_feat.csv"
        df.to_csv(feat_path, index=False)
        upload_dataset_artifact(dataset_id, feat_path)

    return {
        "log": log,
        "new_columns": new_cols,
        "applied_op_ids": applied,
        "shape": {"rows": len(df), "columns": len(df.columns)},
    }


def get_feat_csv(dataset_id: str) -> bytes | None:
    p = DATA_DIR / f"{dataset_id}_feat.parquet"
    if not p.exists():
        ensure_dataset_file(dataset_id, p.name)
    if p.exists():
        return pd.read_parquet(p).to_csv(index=False).encode("utf-8")
    c = DATA_DIR / f"{dataset_id}_feat.csv"
    if not c.exists():
        ensure_dataset_file(dataset_id, c.name)
    if c.exists():
        return c.read_bytes()
    return None


def promote_engineered(dataset_id: str) -> dict:
    """Replace the active dataset's parquet with the engineered version,
    keeping a backup of what existed before so it can be restored."""
    import shutil
    feat_parquet = DATA_DIR / f"{dataset_id}_feat.parquet"
    feat_csv     = DATA_DIR / f"{dataset_id}_feat.csv"
    main_parquet = DATA_DIR / f"{dataset_id}.parquet"
    backup       = DATA_DIR / f"{dataset_id}_pre_feat.parquet"

    src = feat_parquet if feat_parquet.exists() else (feat_csv if feat_csv.exists() else None)
    if src is None:
        ensure_dataset_file(dataset_id, feat_parquet.name)
        ensure_dataset_file(dataset_id, feat_csv.name)
        src = feat_parquet if feat_parquet.exists() else (feat_csv if feat_csv.exists() else None)
    if src is None:
        return {"error": "No engineered data found — run feature engineering first"}

    # Backup current main once (don't overwrite an existing backup)
    if main_parquet.exists() and not backup.exists():
        shutil.copy(main_parquet, backup)
        upload_dataset_artifact(dataset_id, backup)

    if src.suffix == ".parquet":
        df = pd.read_parquet(src)
    else:
        df = pd.read_csv(src)

    df.to_parquet(main_parquet, index=False)
    upload_dataset_artifact(dataset_id, main_parquet)
    return {"ok": True, "df": df}
