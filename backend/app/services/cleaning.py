import math
from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "datasets"


def _load_df(dataset_id: str) -> pd.DataFrame | None:
    p = DATA_DIR / f"{dataset_id}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    c = DATA_DIR / f"{dataset_id}.csv"
    if c.exists():
        return pd.read_csv(c)
    return None


def _save_df(dataset_id: str, df: pd.DataFrame) -> None:
    try:
        df.to_parquet(DATA_DIR / f"{dataset_id}.parquet", index=False)
    except Exception:
        df.to_csv(DATA_DIR / f"{dataset_id}.csv", index=False)


def suggest_fixes(df: pd.DataFrame, schema: list) -> list:
    """Analyze each column and propose concrete cleaning actions."""
    suggestions = []

    for col_info in schema:
        col = col_info["name"]
        if col not in df.columns:
            continue
        ctype = col_info["type"]
        series = df[col]
        null_pct = col_info.get("null_pct", 0)
        total = len(series)

        # 1. High null columns → suggest drop
        if null_pct >= 60:
            suggestions.append({
                "id": f"drop_column::{col}",
                "column": col,
                "issue": f"{null_pct}% missing values",
                "action": "drop_column",
                "label": f"Drop column \"{col}\"",
                "detail": "Too sparse to be useful in most analyses.",
                "severity": "high",
            })

        # 2. Moderate nulls in numeric → suggest fill with median
        elif 0 < null_pct < 60 and ctype in ("integer", "float"):
            med = pd.to_numeric(series, errors="coerce").median()
            suggestions.append({
                "id": f"fill_median::{col}",
                "column": col,
                "issue": f"{null_pct}% missing values",
                "action": "fill_median",
                "label": f"Fill nulls in \"{col}\" with median",
                "detail": f"Median = {round(med, 2) if not pd.isna(med) else 'n/a'}",
                "severity": "medium",
            })

        # 3. Moderate nulls in categorical → fill with mode or 'Unknown'
        elif 0 < null_pct < 60 and ctype in ("categorical", "text", "boolean"):
            suggestions.append({
                "id": f"fill_unknown::{col}",
                "column": col,
                "issue": f"{null_pct}% missing values",
                "action": "fill_unknown",
                "label": f"Fill nulls in \"{col}\" with \"Unknown\"",
                "detail": "Keeps rows usable for categorical analysis.",
                "severity": "medium",
            })

        # 4. Whitespace in text columns
        if ctype in ("text", "categorical") and series.dtype == object:
            non_null = series.dropna().astype(str)
            if len(non_null) > 0 and (non_null != non_null.str.strip()).any():
                suggestions.append({
                    "id": f"trim::{col}",
                    "column": col,
                    "issue": "Leading/trailing whitespace",
                    "action": "trim_whitespace",
                    "label": f"Trim whitespace in \"{col}\"",
                    "detail": "Prevents duplicate categories like 'A' vs 'A '.",
                    "severity": "low",
                })

    # 5. Duplicate rows
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        suggestions.append({
            "id": "drop_duplicates",
            "column": None,
            "issue": f"{dup_count} duplicate rows",
            "action": "drop_duplicates",
            "label": f"Remove {dup_count} duplicate rows",
            "detail": "Identical rows can skew counts and aggregations.",
            "severity": "medium",
        })

    return suggestions


def apply_fixes(df: pd.DataFrame, fix_ids: list, schema: list) -> tuple[pd.DataFrame, list]:
    """Apply selected fixes and return cleaned df + change log."""
    log = []
    df = df.copy()

    for fix_id in fix_ids:
        if fix_id == "drop_duplicates":
            before = len(df)
            df = df.drop_duplicates().reset_index(drop=True)
            log.append(f"Removed {before - len(df)} duplicate rows")
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

        elif action == "fill_median":
            numeric = pd.to_numeric(df[col], errors="coerce")
            med = numeric.median()
            filled = int(df[col].isna().sum())
            df[col] = numeric.fillna(med)
            log.append(f'Filled {filled} nulls in "{col}" with median ({round(med, 2)})')

        elif action == "fill_unknown":
            filled = int(df[col].isna().sum())
            df[col] = df[col].fillna("Unknown")
            log.append(f'Filled {filled} nulls in "{col}" with "Unknown"')

        elif action == "trim_whitespace":
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
            log.append(f'Trimmed whitespace in "{col}"')

    return df, log


def clean_dataset(dataset_id: str, fix_ids: list, schema: list) -> dict:
    df = _load_df(dataset_id)
    if df is None:
        return {"error": "Dataset data not found"}

    cleaned, log = apply_fixes(df, fix_ids, schema)

    # Save cleaned version as a NEW parquet (don't overwrite original)
    clean_path = DATA_DIR / f"{dataset_id}_clean.parquet"
    try:
        cleaned.to_parquet(clean_path, index=False)
    except Exception:
        cleaned.to_csv(DATA_DIR / f"{dataset_id}_clean.csv", index=False)

    return {
        "log": log,
        "rows_before": len(df),
        "rows_after": len(cleaned),
        "cols_before": len(df.columns),
        "cols_after": len(cleaned.columns),
    }


def get_clean_csv(dataset_id: str) -> bytes | None:
    p = DATA_DIR / f"{dataset_id}_clean.parquet"
    if p.exists():
        return pd.read_parquet(p).to_csv(index=False).encode("utf-8")
    c = DATA_DIR / f"{dataset_id}_clean.csv"
    if c.exists():
        return c.read_bytes()
    return None