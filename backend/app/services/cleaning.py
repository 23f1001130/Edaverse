import math
from pathlib import Path
import pandas as pd
import numpy as np
from app.services.store import ensure_dataset_file
from app.services.object_storage import upload_dataset_artifact

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "datasets"

STRING_NULLS = {"null", "none", "na", "n/a", "nan", "nil", "missing", "-", "--", "?", "unknown", ""}


def _finite_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()


def _knn_fill_numeric(df: pd.DataFrame, target_col: str, k: int = 5) -> tuple[pd.Series, int]:
    """Small local KNN imputer for one numeric column, using other numeric columns."""
    numeric_df = df.apply(lambda s: pd.to_numeric(s, errors="coerce")).replace([np.inf, -np.inf], np.nan)
    if target_col not in numeric_df.columns:
        return numeric_df[target_col], 0
    predictors = [
        c for c in numeric_df.columns
        if c != target_col and numeric_df[c].notna().sum() >= max(5, len(numeric_df) * 0.5)
    ][:12]
    target = numeric_df[target_col].copy()
    missing_idx = target[target.isna()].index
    if len(missing_idx) == 0 or len(predictors) < 2:
        return target, 0

    donor_mask = target.notna() & numeric_df[predictors].notna().any(axis=1)
    donors = numeric_df.loc[donor_mask, predictors]
    donor_y = target.loc[donor_mask]
    if len(donors) < k:
        return target.fillna(target.median()), int(target.isna().sum())

    med = donors.median()
    spread = donors.std().replace(0, np.nan).fillna(1)
    donors_scaled = ((donors.fillna(med) - med) / spread).to_numpy(dtype=float)
    filled = 0
    for idx in missing_idx:
        row = numeric_df.loc[idx, predictors]
        if row.notna().sum() == 0:
            continue
        row_scaled = ((row.fillna(med) - med) / spread).to_numpy(dtype=float)
        distances = np.sqrt(((donors_scaled - row_scaled) ** 2).sum(axis=1))
        nearest = np.argsort(distances)[:min(k, len(donor_y))]
        target.loc[idx] = float(donor_y.iloc[nearest].median())
        filled += 1
    return target.fillna(target.median()), filled


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


def _save_df(dataset_id: str, df: pd.DataFrame) -> None:
    try:
        path = DATA_DIR / f"{dataset_id}.parquet"
        df.to_parquet(path, index=False)
        upload_dataset_artifact(dataset_id, path)
    except Exception:
        path = DATA_DIR / f"{dataset_id}.csv"
        df.to_csv(path, index=False)
        upload_dataset_artifact(dataset_id, path)


def suggest_fixes(df: pd.DataFrame, schema: list, ignored_fix_ids: list | None = None) -> list:
    """Analyze each column and propose concrete cleaning actions."""
    suggestions = []
    ignored = set(ignored_fix_ids or [])

    def add_suggestion(item: dict) -> None:
        if item["id"] not in ignored:
            suggestions.append(item)

    # 0. String-encoded null detection
    for col_info in schema:
        col = col_info["name"]
        if col not in df.columns:
            continue
        if df[col].dtype == object:
            non_null = df[col].dropna().astype(str)
            mask = non_null.str.strip().str.lower().isin(STRING_NULLS)
            count = int(mask.sum())
            if count > 0:
                pct = round(count / len(df[col]) * 100, 1)
                examples = list(non_null[mask].value_counts().head(3).index)
                add_suggestion({
                    "id": f"fix_string_nulls::{col}",
                    "column": col,
                    "issue": f"{count} string-encoded nulls ({pct}%)",
                    "action": "fix_string_nulls",
                    "label": f'Clean string nulls in "{col}"',
                    "detail": f"Values like {', '.join(repr(e) for e in examples)} will be treated as missing and filled.",
                    "severity": "medium",
                })

    for col_info in schema:
        col = col_info["name"]
        if col not in df.columns:
            continue
        ctype = col_info["type"]
        series = df[col]
        # Always compute null_pct live from the actual df — never trust the
        # cached schema value, which goes stale after promote/restore.
        total = len(series)
        null_pct = round(series.isna().sum() / total * 100, 1) if total > 0 else 0

        # 1. High null columns → suggest drop
        if null_pct >= 60:
            add_suggestion({
                "id": f"drop_column::{col}",
                "column": col,
                "issue": f"{null_pct}% missing values",
                "action": "drop_column",
                "label": f'Drop column "{col}"',
                "detail": "Too sparse to be useful in most analyses.",
                "severity": "high",
            })

        # 2. Moderate nulls in numeric → suggest fill with median
        elif 0 < null_pct < 60 and ctype in ("integer", "float"):
            numeric_cols = [
                c["name"] for c in schema
                if c["name"] != col and c["name"] in df.columns and c.get("type") in ("integer", "float")
            ]
            enough_knn_context = len(numeric_cols) >= 2 and df[numeric_cols].notna().any(axis=1).sum() >= 10
            if enough_knn_context:
                add_suggestion({
                    "id": f"knn_impute::{col}",
                    "column": col,
                    "issue": f"{null_pct}% missing values",
                    "action": "knn_impute",
                    "label": f'KNN-impute nulls in "{col}"',
                    "detail": "Uses nearby rows from other numeric columns; falls back to median if needed.",
                    "severity": "medium",
                })
            else:
                med = _finite_numeric(series).median()
                add_suggestion({
                    "id": f"fill_median::{col}",
                    "column": col,
                    "issue": f"{null_pct}% missing values",
                    "action": "fill_median",
                    "label": f'Fill nulls in "{col}" with median',
                    "detail": f"Median = {round(med, 2) if not pd.isna(med) else 'n/a'}",
                    "severity": "medium",
                })

        # 3. Moderate nulls in categorical → fill with 'Unknown'
        elif 0 < null_pct < 60 and ctype in ("categorical", "text", "boolean"):
            add_suggestion({
                "id": f"fill_unknown::{col}",
                "column": col,
                "issue": f"{null_pct}% missing values",
                "action": "fill_unknown",
                "label": f'Fill nulls in "{col}" with "Unknown"',
                "detail": "Keeps rows usable for categorical analysis.",
                "severity": "medium",
            })

        # 4. Whitespace in text columns
        if ctype in ("text", "categorical") and series.dtype == object:
            non_null = series.dropna().astype(str)
            if len(non_null) > 0 and (non_null != non_null.str.strip()).any():
                add_suggestion({
                    "id": f"trim::{col}",
                    "column": col,
                    "issue": "Leading/trailing whitespace",
                    "action": "trim_whitespace",
                    "label": f'Trim whitespace in "{col}"',
                    "detail": "Prevents duplicate categories like 'A' vs 'A '.",
                    "severity": "low",
                })

        # 5. Outlier capping for numeric columns (IQR method)
        if ctype in ("integer", "float"):
            numeric = _finite_numeric(series)
            if len(numeric) >= 10:
                q1, q3 = numeric.quantile(0.25), numeric.quantile(0.75)
                iqr = q3 - q1
                if iqr > 0:
                    lower = q1 - 1.5 * iqr
                    upper = q3 + 1.5 * iqr
                    n_out = int(((numeric < lower) | (numeric > upper)).sum())
                    if n_out > 0:
                        pct_out = round(n_out / len(numeric) * 100, 1)
                        add_suggestion({
                            "id": f"cap_outliers::{col}",
                            "column": col,
                            "issue": f"{n_out} outliers ({pct_out}%) outside IQR fence",
                            "action": "cap_outliers",
                            "label": f'Cap outliers in "{col}" to IQR fences',
                            "detail": f"Clip to [{round(lower, 2)}, {round(upper, 2)}]",
                            "severity": "medium",
                        })

    # 6. Duplicate rows
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        add_suggestion({
            "id": "drop_duplicates",
            "column": None,
            "issue": f"{dup_count} duplicate rows",
            "action": "drop_duplicates",
            "label": f"Remove {dup_count} duplicate rows",
            "detail": "Identical rows can skew counts and aggregations.",
            "severity": "medium",
        })

    return suggestions


def apply_fixes(df: pd.DataFrame, fix_ids: list, schema: list) -> tuple[pd.DataFrame, list, list]:
    """Apply selected fixes and return cleaned df + change log."""
    log = []
    applied = []
    df = df.copy()
    type_by_col = {c.get("name"): c.get("type") for c in schema}

    for fix_id in fix_ids:
        if fix_id == "drop_duplicates":
            before = len(df)
            df = df.drop_duplicates().reset_index(drop=True)
            removed = before - len(df)
            log.append(f"Removed {removed} duplicate rows")
            if removed > 0:
                applied.append(fix_id)
            continue

        if "::" not in fix_id:
            continue
        action, col = fix_id.split("::", 1)
        if col not in df.columns and action != "drop_column":
            continue

        if action == "drop_column":
            if col in df.columns:
                df = df.drop(columns=[col])
                log.append(f'Dropped column "{col}"')
                applied.append(fix_id)

        elif action == "fill_median":
            numeric = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
            med = numeric.median()
            filled = int(df[col].isna().sum())
            df[col] = numeric.fillna(med)
            log.append(f'Filled {filled} nulls in "{col}" with median ({round(med, 2)})')
            if filled > 0:
                applied.append(fix_id)

        elif action == "knn_impute":
            before = int(df[col].isna().sum())
            imputed, filled = _knn_fill_numeric(df, col)
            df[col] = imputed
            log.append(f'KNN-imputed {filled} nulls in "{col}"')
            if before > 0 and filled > 0:
                applied.append(fix_id)

        elif action == "fill_unknown":
            filled = int(df[col].isna().sum())
            df[col] = df[col].fillna("Unknown")
            log.append(f'Filled {filled} nulls in "{col}" with "Unknown"')
            if filled > 0:
                applied.append(fix_id)

        elif action in ("trim", "trim_whitespace"):
            before = df[col].copy()
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
            changed = int((before != df[col]).fillna(False).sum())
            log.append(f'Trimmed whitespace in "{col}"')
            if changed > 0:
                applied.append(fix_id)

        elif action == "fix_string_nulls":
            before = int(df[col].isna().sum())
            df[col] = df[col].apply(
                lambda x: np.nan if (isinstance(x, str) and x.strip().lower() in STRING_NULLS) else x
            )
            after = int(df[col].isna().sum())
            converted = after - before
            if converted > 0:
                if type_by_col.get(col) in ("integer", "float"):
                    numeric = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
                    med = numeric.median()
                    df[col] = numeric.fillna(med)
                    log.append(f'Converted {converted} string-nulls in "{col}" and filled missing values with median ({round(med, 2)})')
                else:
                    df[col] = df[col].fillna("Unknown")
                    log.append(f'Converted {converted} string-nulls in "{col}" and filled missing values with "Unknown"')
                applied.append(fix_id)
            else:
                log.append(f'Converted 0 string-nulls in "{col}" to missing values')

        elif action == "cap_outliers":
            numeric = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
            q1, q3 = numeric.quantile(0.25), numeric.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                capped = int(((numeric < lower) | (numeric > upper)).sum())
                df[col] = numeric.clip(lower=lower, upper=upper)
                log.append(f'Capped {capped} outliers in "{col}" to [{round(lower, 2)}, {round(upper, 2)}]')
                if capped > 0:
                    applied.append(fix_id)

    return df, log, applied


def clean_dataset(dataset_id: str, fix_ids: list, schema: list) -> dict:
    df = _load_df(dataset_id)
    if df is None:
        return {"error": "Dataset data not found"}

    cleaned, log, applied = apply_fixes(df, fix_ids, schema)

    clean_path = DATA_DIR / f"{dataset_id}_clean.parquet"
    try:
        cleaned.to_parquet(clean_path, index=False)
        upload_dataset_artifact(dataset_id, clean_path)
    except Exception:
        clean_path = DATA_DIR / f"{dataset_id}_clean.csv"
        cleaned.to_csv(clean_path, index=False)
        upload_dataset_artifact(dataset_id, clean_path)

    return {
        "log": log,
        "rows_before": len(df),
        "rows_after": len(cleaned),
        "cols_before": len(df.columns),
        "cols_after": len(cleaned.columns),
        "applied_fix_ids": applied,
    }


def get_clean_csv(dataset_id: str) -> bytes | None:
    p = DATA_DIR / f"{dataset_id}_clean.parquet"
    if not p.exists():
        ensure_dataset_file(dataset_id, p.name)
    if p.exists():
        return pd.read_parquet(p).to_csv(index=False).encode("utf-8")
    c = DATA_DIR / f"{dataset_id}_clean.csv"
    if not c.exists():
        ensure_dataset_file(dataset_id, c.name)
    if c.exists():
        return c.read_bytes()
    return None


def promote_cleaned(dataset_id: str) -> dict:
    import shutil
    clean_parquet = DATA_DIR / f"{dataset_id}_clean.parquet"
    clean_csv = DATA_DIR / f"{dataset_id}_clean.csv"
    main_parquet = DATA_DIR / f"{dataset_id}.parquet"
    backup_parquet = DATA_DIR / f"{dataset_id}_original.parquet"

    src = clean_parquet if clean_parquet.exists() else (clean_csv if clean_csv.exists() else None)
    if src is None:
        ensure_dataset_file(dataset_id, clean_parquet.name)
        ensure_dataset_file(dataset_id, clean_csv.name)
        src = clean_parquet if clean_parquet.exists() else (clean_csv if clean_csv.exists() else None)
    if src is None:
        return {"error": "No cleaned data found — run cleaning first"}

    if main_parquet.exists() and not backup_parquet.exists():
        shutil.copy(main_parquet, backup_parquet)
        upload_dataset_artifact(dataset_id, backup_parquet)

    if src.suffix == ".parquet":
        df = pd.read_parquet(src)
    else:
        df = pd.read_csv(src)

    df.to_parquet(main_parquet, index=False)
    upload_dataset_artifact(dataset_id, main_parquet)
    return {"ok": True, "df": df}


def has_original_backup(dataset_id: str) -> bool:
    backup = DATA_DIR / f"{dataset_id}_original.parquet"
    if not backup.exists():
        ensure_dataset_file(dataset_id, backup.name)
    return backup.exists()


def restore_original(dataset_id: str) -> dict:
    import shutil
    backup = DATA_DIR / f"{dataset_id}_original.parquet"
    main = DATA_DIR / f"{dataset_id}.parquet"
    if not backup.exists():
        ensure_dataset_file(dataset_id, backup.name)
    if not backup.exists():
        return {"error": "No original backup found"}
    shutil.copy(backup, main)
    upload_dataset_artifact(dataset_id, main)
    df = pd.read_parquet(main)
    return {"ok": True, "df": df}
