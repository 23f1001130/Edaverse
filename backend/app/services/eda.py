import json
import math
from pathlib import Path
import pandas as pd
import numpy as np
from app.services.store import ensure_dataset_file

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
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


def _load_df(dataset: dict) -> pd.DataFrame:
    dataset_id = dataset["id"]
    raw_path = DATA_DIR / f"{dataset_id}.parquet"
    if not raw_path.exists():
        ensure_dataset_file(dataset_id, raw_path.name)
    if raw_path.exists():
        return pd.read_parquet(raw_path)
    csv_path = DATA_DIR / f"{dataset_id}.csv"
    if not csv_path.exists():
        ensure_dataset_file(dataset_id, csv_path.name)
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return None


def is_id_like(col_info: dict, df: pd.DataFrame) -> bool:
    col = col_info["name"]
    if col not in df.columns:
        return False
    total = len(df[col].dropna())
    if total == 0:
        return False
    unique_ratio = df[col].nunique() / total
    name_signal = any(k in col.lower() for k in ("id", "uuid", "key", "code", "number", "ref"))
    return unique_ratio > 0.95 and (name_signal or col_info["type"] in ("text", "categorical"))


def compute_distributions(df: pd.DataFrame, schema: list) -> list:
    results = []
    for col_info in schema:
        col = col_info["name"]
        if col not in df.columns:
            continue
        col_type = col_info["type"]
        series = df[col].dropna()

        if len(series) == 0:
            continue
        if col_info.get("null_pct", 0) >= 100:
            continue
        if is_id_like(col_info, df):
            results.append({
                "column": col, "type": "skipped", "col_type": col_type,
                "reason": "Unique identifier — no distribution to show",
                "unique": int(df[col].nunique()),
            })
            continue

        if col_type in ("integer", "float"):
            try:
                vals = _numeric(series, dropna=True)
                if len(vals) == 0:
                    results.append({
                        "column": col, "type": "skipped", "col_type": col_type,
                        "reason": "No finite numeric values",
                    })
                    continue
                if vals.nunique() <= 1:
                    results.append({
                        "column": col, "type": "skipped", "col_type": col_type,
                        "reason": f"Constant value ({_safe(vals.iloc[0])})",
                    })
                    continue
                counts, edges = np.histogram(vals, bins=20)
                bins = [
                    {"range": f"{_safe(edges[i]):.2g}–{_safe(edges[i+1]):.2g}",
                     "count": int(counts[i])}
                    for i in range(len(counts))
                ]
                q1 = _safe(vals.quantile(0.25))
                q3 = _safe(vals.quantile(0.75))
                median = _safe(vals.median())
                skewness = _safe(vals.skew()) if len(vals) > 2 else None
                # box plot whisker data
                iqr = (q3 - q1) if (q1 is not None and q3 is not None) else None
                whisker_lo = _safe(vals[vals >= (q1 - 1.5 * (q3 - q1))].min()) if iqr else None
                whisker_hi = _safe(vals[vals <= (q3 + 1.5 * (q3 - q1))].max()) if iqr else None
                results.append({
                    "column": col, "type": "histogram", "col_type": col_type,
                    "bins": bins,
                    "stats": {
                        "min": _safe(vals.min()), "max": _safe(vals.max()),
                        "mean": _safe(vals.mean()), "median": median,
                        "std": _safe(vals.std()),
                        "q25": q1, "q75": q3,
                        "skewness": skewness,
                    },
                    "boxplot": {
                        "min": _safe(vals.min()), "q25": q1, "median": median,
                        "q75": q3, "max": _safe(vals.max()),
                        "whisker_lo": whisker_lo, "whisker_hi": whisker_hi,
                        "outlier_count": int(((vals < (q1 - 1.5 * (q3 - q1))) | (vals > (q3 + 1.5 * (q3 - q1)))).sum()) if iqr else 0,
                    }
                })
            except Exception:
                pass

        elif col_type in ("categorical", "boolean"):
            try:
                nuniq = series.nunique()
                if nuniq <= 1:
                    results.append({
                        "column": col, "type": "skipped", "col_type": col_type,
                        "reason": f"Single value ({series.iloc[0]})",
                    })
                    continue
                vc_full = series.value_counts()
                vc = vc_full.head(10)
                nn = series.dropna()
                results.append({
                    "column": col, "type": "barchart", "col_type": col_type,
                    "values": [{"value": str(k), "count": int(v)} for k, v in vc.items()],
                    "total_unique": int(nuniq),
                    "cat_stats": {
                        "unique": int(nuniq),
                        "top": str(vc_full.index[0]) if len(vc_full) else None,
                        "freq": int(vc_full.iloc[0]) if len(vc_full) else 0,
                        "freq_pct": round(vc_full.iloc[0] / len(nn) * 100, 1) if len(nn) else 0,
                        "count": int(len(nn)),
                    },
                })
            except Exception:
                pass

        elif col_type == "text":
            try:
                nuniq = series.nunique()
                if nuniq <= 20:
                    vc = series.value_counts().head(10)
                    results.append({
                        "column": col, "type": "barchart", "col_type": "text",
                        "values": [{"value": str(k), "count": int(v)} for k, v in vc.items()],
                        "total_unique": int(nuniq),
                    })
                else:
                    results.append({
                        "column": col, "type": "skipped", "col_type": "text",
                        "reason": f"Free text — {nuniq} unique values",
                    })
            except Exception:
                pass

        elif col_type == "datetime":
            try:
                parsed = pd.to_datetime(series, errors="coerce").dropna()
                if len(parsed) > 0:
                    by_period = parsed.dt.to_period("M").value_counts().sort_index()
                    timeline = [
                        {"period": str(p), "count": int(c)}
                        for p, c in by_period.items()
                    ]
                    results.append({
                        "column": col, "type": "timeline", "col_type": col_type,
                        "timeline": timeline,
                        "min": str(parsed.min()), "max": str(parsed.max()),
                        "count": len(parsed),
                    })
            except Exception:
                pass

    return results


def compute_correlation(df: pd.DataFrame, schema: list, method: str = "pearson") -> dict | None:
    numeric_cols = [
        c["name"] for c in schema
        if c["type"] in ("integer", "float") and c["name"] in df.columns
        and not is_id_like(c, df)
    ]
    if len(numeric_cols) < 2:
        return None

    sub = _nonconstant_numeric_frame(df, numeric_cols)
    numeric_cols = list(sub.columns)
    if len(numeric_cols) < 2:
        return None
    method = method if method in ("pearson", "spearman") else "pearson"
    corr = sub.corr(method=method)

    matrix = []
    for col_a in numeric_cols:
        for col_b in numeric_cols:
            val = corr.loc[col_a, col_b] if col_a in corr.index and col_b in corr.columns else None
            matrix.append({"x": col_a, "y": col_b, "value": _safe(val)})

    return {"columns": numeric_cols, "matrix": matrix, "method": method}


def compute_scatter_pairs(df: pd.DataFrame, schema: list, correlation: dict) -> list:
    if not correlation:
        return []
    seen = set()
    pairs = []
    for cell in correlation["matrix"]:
        a, b, v = cell["x"], cell["y"], cell["value"]
        if a == b or v is None:
            continue
        key = tuple(sorted([a, b]))
        if key in seen:
            continue
        seen.add(key)
        pairs.append((a, b, abs(v), v))

    pairs.sort(key=lambda x: x[2], reverse=True)
    top = [p for p in pairs if p[2] >= 0.3][:3]

    scatters = []
    for a, b, _, signed in top:
        sub = df[[a, b]].apply(lambda s: _numeric(s)).dropna()
        if len(sub) > 200:
            sub = sub.sample(200, random_state=1)
        points = [{"x": _safe(r[a]), "y": _safe(r[b])} for _, r in sub.iterrows()]
        scatters.append({"x_col": a, "y_col": b, "correlation": _safe(signed), "points": points})
    return scatters


def compute_outliers(df: pd.DataFrame, schema: list) -> list:
    results = []
    for col_info in schema:
        col = col_info["name"]
        if col_info["type"] not in ("integer", "float") or col not in df.columns:
            continue
        if is_id_like(col_info, df):
            continue
        series = _numeric(df[col], dropna=True)
        if len(series) < 10:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = series[(series < lower) | (series > upper)]
        if len(outliers) > 0:
            examples = sorted(outliers.tolist(), key=lambda x: abs(x - series.median()), reverse=True)[:3]
            results.append({
                "column": col,
                "count": int(len(outliers)),
                "pct": round(len(outliers) / len(series) * 100, 1),
                "bounds": {"lower": _safe(lower), "upper": _safe(upper)},
                "examples": [_safe(e) for e in examples],
            })
    return results


def compute_missingness_cooccurrence(df: pd.DataFrame, schema: list) -> dict | None:
    """Compute missingness co-occurrence matrix for columns with any nulls."""
    null_cols = [
        c["name"] for c in schema
        if c.get("null_pct", 0) > 0 and c["name"] in df.columns
    ]
    if len(null_cols) < 2:
        return None

    miss = df[null_cols].isna().astype(int)
    total = len(df)
    matrix = []
    for a in null_cols:
        for b in null_cols:
            both = int((miss[a] & miss[b]).sum())
            matrix.append({
                "x": a, "y": b,
                "both_missing": both,
                "pct": round(both / total * 100, 1) if total else 0,
            })

    # Flag column pairs that are very likely MNAR
    # (co-occurrence much higher than expected by chance)
    flagged = []
    seen = set()
    for a in null_cols:
        for b in null_cols:
            if a == b:
                continue
            key = tuple(sorted([a, b]))
            if key in seen:
                continue
            seen.add(key)
            pa = miss[a].mean()
            pb = miss[b].mean()
            expected = pa * pb
            actual = (miss[a] & miss[b]).mean()
            if expected > 0 and actual / expected > 2 and actual > 0.02:
                flagged.append({
                    "a": a, "b": b,
                    "actual_pct": round(actual * 100, 1),
                    "expected_pct": round(expected * 100, 1),
                    "lift": round(actual / expected, 1),
                })
    flagged.sort(key=lambda x: x["lift"], reverse=True)

    return {"columns": null_cols, "matrix": matrix, "flagged_pairs": flagged[:5]}


def compute_missingness_matrix(df: pd.DataFrame, schema: list) -> dict | None:
    """Small row x column missingness matrix for a missingno-style overview."""
    missing_cols = [
        c["name"] for c in sorted(schema, key=lambda x: x.get("null_pct", 0), reverse=True)
        if c.get("null_pct", 0) > 0 and c["name"] in df.columns
    ][:24]
    if not missing_cols:
        return None

    total = len(df)
    if total == 0:
        return None
    step = max(total // 80, 1)
    sampled = df[missing_cols].iloc[::step].head(80)
    rows = []
    for idx, row in sampled.iterrows():
        rows.append({
            "row": int(idx) if isinstance(idx, (int, np.integer)) else str(idx),
            "values": [bool(pd.isna(row[c])) for c in missing_cols],
        })
    return {"columns": missing_cols, "rows": rows, "total_rows": total}


def compute_numeric_profile(df: pd.DataFrame, schema: list, outliers: list) -> dict:
    outlier_by_col = {o["column"]: o for o in outliers}
    columns = []
    for c in schema:
        col = c["name"]
        if c.get("type") not in ("integer", "float") or col not in df.columns or is_id_like(c, df):
            continue
        skew = c.get("skewness")
        abs_skew = abs(skew) if skew is not None else None
        columns.append({
            "column": col,
            "skewness": _safe(skew),
            "abs_skewness": _safe(abs_skew),
            "null_pct": _safe(c.get("null_pct", 0)),
            "outlier_count": int(outlier_by_col.get(col, {}).get("count", 0)),
            "outlier_pct": _safe(outlier_by_col.get(col, {}).get("pct", 0)),
            "mean": _safe(c.get("mean")),
            "std": _safe(c.get("std")),
            "unique": int(df[col].nunique(dropna=True)),
        })
    columns.sort(key=lambda x: (x["abs_skewness"] or 0, x["outlier_pct"] or 0), reverse=True)
    return {
        "columns": columns[:30],
        "skewed_count": sum(1 for c in columns if (c["abs_skewness"] or 0) > 1),
        "outlier_columns": sum(1 for c in columns if c["outlier_count"] > 0),
    }


def compute_categorical_profile(df: pd.DataFrame, schema: list) -> dict:
    columns = []
    for c in schema:
        col = c["name"]
        if c.get("type") not in ("categorical", "text", "boolean") or col not in df.columns:
            continue
        non_null = df[col].dropna()
        total = len(df)
        count = len(non_null)
        unique = int(non_null.nunique()) if count else 0
        top = None
        freq = 0
        if count:
            vc = non_null.value_counts()
            top = str(vc.index[0])
            freq = int(vc.iloc[0])
        freq_pct = round(freq / count * 100, 1) if count else 0
        cardinality_ratio = round(unique / max(count, 1) * 100, 1)
        id_like = is_id_like(c, df)
        if id_like:
            strategy = "identifier"
        elif unique <= 10:
            strategy = "one-hot"
        elif unique <= 50:
            strategy = "ordinal/frequency"
        else:
            strategy = "high-cardinality"
        columns.append({
            "column": col,
            "type": c.get("type"),
            "unique": unique,
            "count": count,
            "null_pct": _safe(round((total - count) / total * 100, 1) if total else 0),
            "top": top,
            "freq_pct": freq_pct,
            "cardinality_ratio": cardinality_ratio,
            "strategy": strategy,
            "is_imbalanced": freq_pct >= 95 and unique > 1,
        })
    columns.sort(key=lambda x: (x["strategy"] == "identifier", x["unique"]), reverse=True)
    return {
        "columns": columns[:30],
        "high_cardinality_count": sum(1 for c in columns if c["strategy"] in ("identifier", "high-cardinality")),
        "imbalanced_count": sum(1 for c in columns if c["is_imbalanced"]),
    }


def compute_pca_projection(df: pd.DataFrame, schema: list) -> dict | None:
    numeric_cols = [
        c["name"] for c in schema
        if c.get("type") in ("integer", "float") and c["name"] in df.columns and not is_id_like(c, df)
    ][:25]
    if len(numeric_cols) < 2 or len(df) < 3:
        return None

    sub = df[numeric_cols].apply(lambda s: _numeric(s))
    sub = sub.dropna(axis=1, how="all")
    if sub.shape[1] < 2:
        return None
    sub = sub.fillna(sub.median(numeric_only=True)).dropna(axis=0)
    if len(sub) < 3:
        return None
    if len(sub) > 500:
        sub = sub.sample(500, random_state=1)

    std = sub.std().replace(0, np.nan)
    scaled = ((sub - sub.mean()) / std).replace([np.inf, -np.inf], np.nan).dropna(axis=1)
    if scaled.shape[1] < 2:
        return None

    matrix = scaled.to_numpy(dtype=float)
    matrix = matrix - matrix.mean(axis=0)
    try:
        _, singular_values, vt = np.linalg.svd(matrix, full_matrices=False)
    except Exception:
        return None
    coords = matrix @ vt[:2].T
    denom = float((singular_values ** 2).sum())
    explained = (singular_values[:2] ** 2 / denom * 100).tolist() if denom else [0, 0]
    points = [
        {"x": _safe(coords[i, 0]), "y": _safe(coords[i, 1]), "row": int(idx) if isinstance(idx, (int, np.integer)) else str(idx)}
        for i, idx in enumerate(scaled.index)
    ]
    return {
        "points": points,
        "columns": list(scaled.columns),
        "explained_variance": [_safe(v) for v in explained],
    }


def compute_pivot_heatmap(df: pd.DataFrame, schema: list) -> dict | None:
    cat_cols = [
        c["name"] for c in schema
        if c.get("type") in ("categorical", "text", "boolean") and c["name"] in df.columns
        and 2 <= df[c["name"]].nunique(dropna=True) <= 12
    ]
    if len(cat_cols) < 2:
        return None
    a, b = sorted(cat_cols, key=lambda col: df[col].nunique(dropna=True), reverse=True)[:2]
    work = df[[a, b]].dropna().copy()
    if work.empty:
        return None
    top_a = work[a].value_counts().head(8).index
    top_b = work[b].value_counts().head(8).index
    table = pd.crosstab(work[a], work[b]).reindex(index=top_a, columns=top_b, fill_value=0)
    cells = []
    max_count = int(table.to_numpy().max()) if not table.empty else 0
    for row in table.index:
        for col in table.columns:
            cells.append({"x": str(col), "y": str(row), "count": int(table.loc[row, col])})
    return {
        "x": b,
        "y": a,
        "x_values": [str(v) for v in table.columns],
        "y_values": [str(v) for v in table.index],
        "cells": cells,
        "max_count": max_count,
    }


def _schema_by_name(schema: list) -> dict:
    return {c["name"]: c for c in schema}


def _correlation_ratio(categories: pd.Series, values: pd.Series) -> float | None:
    work = pd.DataFrame({"cat": categories, "val": values}).dropna()
    if len(work) < 3:
        return None
    overall = work["val"].mean()
    total = ((work["val"] - overall) ** 2).sum()
    if total == 0:
        return None
    between = 0.0
    for _, group in work.groupby("cat"):
        between += len(group) * (group["val"].mean() - overall) ** 2
    return float(between / total)


def _cramers_v(a: pd.Series, b: pd.Series) -> float | None:
    table = pd.crosstab(a, b)
    if table.shape[0] < 2 or table.shape[1] < 2:
        return None
    try:
        from scipy.stats import chi2_contingency
        chi2 = chi2_contingency(table, correction=False)[0]
    except Exception:
        expected = np.outer(table.sum(axis=1), table.sum(axis=0)) / table.to_numpy().sum()
        with np.errstate(divide="ignore", invalid="ignore"):
            chi2 = np.nansum((table.to_numpy() - expected) ** 2 / expected)
    n = table.to_numpy().sum()
    denom = n * (min(table.shape) - 1)
    if denom <= 0:
        return None
    return float(math.sqrt(chi2 / denom))


def compute_target_analysis(dataset: dict, target: str) -> dict:
    df = _load_df(dataset)
    if df is None:
        rows = dataset.get("sample_rows", [])
        if not rows:
            return {"error": "No data available for target analysis"}
        df = pd.DataFrame(rows)

    schema = dataset.get("schema", [])
    by_name = _schema_by_name(schema)
    if target not in df.columns or target not in by_name:
        return {"error": "Target column not found"}

    target_info = by_name[target]
    target_type = target_info.get("type")
    target_non_null = df[target].dropna()
    unique = int(target_non_null.nunique()) if len(target_non_null) else 0
    is_numeric_target = target_type in ("integer", "float") and unique > 10
    task = "regression" if is_numeric_target else "classification"

    result = {
        "target": {"name": target, "type": target_type, "task": task, "unique": unique, "null_pct": target_info.get("null_pct", 0)},
        "distribution": None,
        "numeric_relationships": [],
        "categorical_relationships": [],
        "recommendations": [],
    }

    if task == "regression":
        y = _numeric(df[target])
        y_valid = y.dropna()
        if len(y_valid) > 0:
            counts, edges = np.histogram(y_valid, bins=min(20, max(5, int(math.sqrt(len(y_valid))))))
            result["distribution"] = {
                "type": "histogram",
                "bins": [{"range": f"{_safe(edges[i]):.2g}-{_safe(edges[i+1]):.2g}", "count": int(counts[i])} for i in range(len(counts))],
                "stats": {"mean": _safe(y_valid.mean()), "std": _safe(y_valid.std()), "min": _safe(y_valid.min()), "max": _safe(y_valid.max())},
            }

        for c in schema:
            col = c["name"]
            if col == target or col not in df.columns or is_id_like(c, df):
                continue
            if c.get("type") in ("integer", "float"):
                x = _numeric(df[col])
                work = pd.DataFrame({"x": x, "y": y}).dropna()
                if len(work) < 3 or work["x"].nunique() <= 1 or work["y"].nunique() <= 1:
                    continue
                corr = work["x"].corr(work["y"])
                if pd.isna(corr):
                    continue
                sample = work.sample(min(180, len(work)), random_state=1) if len(work) > 180 else work
                result["numeric_relationships"].append({
                    "feature": col,
                    "kind": "numeric_scatter",
                    "score": _safe(abs(corr)),
                    "correlation": _safe(corr),
                    "points": [{"x": _safe(r["x"]), "y": _safe(r["y"])} for _, r in sample.iterrows()],
                })
            elif c.get("type") in ("categorical", "text", "boolean") and df[col].nunique(dropna=True) <= 20:
                work = pd.DataFrame({"cat": df[col], "y": y}).dropna()
                if len(work) < 3:
                    continue
                eta = _correlation_ratio(work["cat"], work["y"])
                groups = []
                for val, group in work.groupby("cat"):
                    groups.append({
                        "value": str(val),
                        "mean": _safe(group["y"].mean()),
                        "median": _safe(group["y"].median()),
                        "count": int(len(group)),
                    })
                groups.sort(key=lambda g: g["count"], reverse=True)
                result["categorical_relationships"].append({
                    "feature": col,
                    "kind": "category_vs_numeric",
                    "score": _safe(eta),
                    "groups": groups[:12],
                })

    else:
        classes = target_non_null.astype(str).value_counts().head(8)
        result["distribution"] = {
            "type": "classes",
            "values": [{"value": str(k), "count": int(v)} for k, v in classes.items()],
        }
        target_cat = df[target].astype(str).where(df[target].notna())

        for c in schema:
            col = c["name"]
            if col == target or col not in df.columns or is_id_like(c, df):
                continue
            if c.get("type") in ("integer", "float"):
                x = _numeric(df[col])
                work = pd.DataFrame({"x": x, "target": target_cat}).dropna()
                if len(work) < 3 or work["target"].nunique() < 2:
                    continue
                eta = _correlation_ratio(work["target"], work["x"])
                groups = []
                for val, group in work.groupby("target"):
                    groups.append({
                        "class": str(val),
                        "mean": _safe(group["x"].mean()),
                        "median": _safe(group["x"].median()),
                        "count": int(len(group)),
                    })
                groups.sort(key=lambda g: g["count"], reverse=True)
                result["numeric_relationships"].append({
                    "feature": col,
                    "kind": "numeric_by_class",
                    "score": _safe(eta),
                    "groups": groups[:12],
                })
            elif c.get("type") in ("categorical", "text", "boolean") and df[col].nunique(dropna=True) <= 20:
                work = pd.DataFrame({"feature": df[col].astype(str).where(df[col].notna()), "target": target_cat}).dropna()
                if len(work) < 3 or work["feature"].nunique() < 2 or work["target"].nunique() < 2:
                    continue
                score = _cramers_v(work["feature"], work["target"])
                feature_vals = work["feature"].value_counts().head(10).index
                target_vals = work["target"].value_counts().head(8).index
                table = pd.crosstab(work["feature"], work["target"]).reindex(index=feature_vals, columns=target_vals, fill_value=0)
                cells = []
                for row in table.index:
                    for col_val in table.columns:
                        cells.append({"x": str(col_val), "y": str(row), "count": int(table.loc[row, col_val])})
                result["categorical_relationships"].append({
                    "feature": col,
                    "kind": "category_crosstab",
                    "score": _safe(score),
                    "x_values": [str(v) for v in table.columns],
                    "y_values": [str(v) for v in table.index],
                    "cells": cells,
                    "max_count": int(table.to_numpy().max()) if not table.empty else 0,
                })

    result["numeric_relationships"].sort(key=lambda x: x.get("score") or 0, reverse=True)
    result["categorical_relationships"].sort(key=lambda x: x.get("score") or 0, reverse=True)
    result["numeric_relationships"] = result["numeric_relationships"][:8]
    result["categorical_relationships"] = result["categorical_relationships"][:8]

    for rel in (result["numeric_relationships"] + result["categorical_relationships"])[:6]:
        score = rel.get("score")
        if score is None:
            continue
        if score >= 0.5:
            strength = "strong"
        elif score >= 0.25:
            strength = "moderate"
        else:
            strength = "weak"
        result["recommendations"].append({
            "feature": rel["feature"],
            "strength": strength,
            "score": score,
            "text": f'{rel["feature"]} has a {strength} relationship with {target}.',
        })

    return result


def compute_observations(df: pd.DataFrame, schema: list, correlation: dict, outliers: list) -> list:
    obs = []

    # Missing data
    high_null = sorted(
        [c for c in schema if c.get("null_pct", 0) >= 10],
        key=lambda c: c["null_pct"], reverse=True
    )
    for c in high_null[:3]:
        sev = "severe" if c["null_pct"] >= 50 else "notable"
        obs.append({
            "type": "missing", "severity": "high" if c["null_pct"] >= 50 else "medium",
            "text": f'{c["name"]} has {c["null_pct"]}% missing values ({sev}) — '
                    f'this will affect any analysis using this column.'
        })

    # Unique keys
    for c in schema:
        if c["name"] in df.columns:
            total = len(df[c["name"]].dropna())
            if total > 0 and df[c["name"]].nunique() == total and total == len(df):
                obs.append({
                    "type": "key", "severity": "info",
                    "text": f'{c["name"]} is fully unique with no nulls — likely a primary key, safe to use as an index.'
                })
                break

    # Skewed columns
    skewed = sorted(
        [c for c in schema if c.get("skewness") is not None and abs(c["skewness"]) > 1.0],
        key=lambda c: abs(c["skewness"]), reverse=True
    )
    for c in skewed[:3]:
        direction = "right (positive)" if c["skewness"] > 0 else "left (negative)"
        obs.append({
            "type": "skew", "severity": "medium",
            "text": f'{c["name"]} is heavily skewed {direction} (skew={c["skewness"]}) — '
                    f'consider a log or Box-Cox transform before modelling.'
        })

    # Correlations
    if correlation:
        seen = set()
        strong = []
        for cell in correlation["matrix"]:
            a, b, v = cell["x"], cell["y"], cell["value"]
            if a == b or v is None:
                continue
            key = tuple(sorted([a, b]))
            if key in seen:
                continue
            seen.add(key)
            if abs(v) >= 0.5:
                strong.append((a, b, v))
        strong.sort(key=lambda x: abs(x[2]), reverse=True)
        for a, b, v in strong[:3]:
            direction = "positively" if v > 0 else "negatively"
            strength = "strongly" if abs(v) >= 0.7 else "moderately"
            obs.append({
                "type": "correlation", "severity": "info",
                "text": f'{a} and {b} are {strength} {direction} correlated ({v:.2f})'
                        + (' — consider dropping one to reduce redundancy.' if abs(v) >= 0.9 else '.')
            })

    # Outliers
    for o in outliers[:3]:
        obs.append({
            "type": "outlier", "severity": "medium",
            "text": f'{o["column"]} has {o["count"]} outliers ({o["pct"]}%) outside '
                    f'[{o["bounds"]["lower"]} – {o["bounds"]["upper"]}], e.g. {o["examples"]}.'
        })

    # Time series detection
    dt_cols = [c["name"] for c in schema if c["type"] == "datetime"]
    if dt_cols:
        obs.append({
            "type": "timeseries", "severity": "info",
            "text": f'{dt_cols[0]} is a datetime column — this dataset may be a time series, '
                    f'consider trend analysis over time.'
        })

    if not obs:
        obs.append({
            "type": "clean", "severity": "info",
            "text": "No major data quality issues detected — clean dataset, ready for analysis."
        })

    return obs


def compute_nulls(df: pd.DataFrame, schema: list) -> list:
    return [
        {"column": c["name"], "null_count": c["null_count"],
         "null_pct": c["null_pct"], "total": len(df)}
        for c in schema
    ]


def compute_eda(dataset: dict) -> dict:
    df = _load_df(dataset)
    if df is None:
        rows = dataset.get("sample_rows", [])
        if not rows:
            return {"error": "No data available for EDA"}
        df = pd.DataFrame(rows)

    schema = dataset.get("schema", [])
    correlation = compute_correlation(df, schema, "pearson")
    spearman = compute_correlation(df, schema, "spearman")
    outliers = compute_outliers(df, schema)

    return {
        "dataset_id": dataset["id"],
        "filename": dataset.get("filename"),
        "observations": compute_observations(df, schema, correlation, outliers),
        "distributions": compute_distributions(df, schema),
        "correlation": correlation,
        "correlation_spearman": spearman,
        "scatter_pairs": compute_scatter_pairs(df, schema, correlation),
        "outliers": outliers,
        "nulls": compute_nulls(df, schema),
        "missingness": compute_missingness_cooccurrence(df, schema),
        "missingness_matrix": compute_missingness_matrix(df, schema),
        "numeric_profile": compute_numeric_profile(df, schema, outliers),
        "categorical_profile": compute_categorical_profile(df, schema),
        "pca": compute_pca_projection(df, schema),
        "pivot_heatmap": compute_pivot_heatmap(df, schema),
    }
