import json
import math
from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "datasets"

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
    if raw_path.exists():
        return pd.read_parquet(raw_path)
    csv_path = DATA_DIR / f"{dataset_id}.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return None


# ── Chart relevance: decide whether a column is worth charting ──
def is_id_like(col_info: dict, df: pd.DataFrame) -> bool:
    """High-cardinality columns that are basically unique identifiers."""
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

        # Skip charts that carry no information
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
                vals = series.astype(float)
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
                results.append({
                    "column": col, "type": "histogram", "col_type": col_type,
                    "bins": bins,
                    "stats": {
                        "min": _safe(vals.min()), "max": _safe(vals.max()),
                        "mean": _safe(vals.mean()), "median": _safe(vals.median()),
                        "std": _safe(vals.std()),
                        "q25": _safe(vals.quantile(0.25)),
                        "q75": _safe(vals.quantile(0.75)),
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
            # only chart text if it's low-cardinality enough to be category-ish
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
                    # bucket by month for a timeline
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


def compute_correlation(df: pd.DataFrame, schema: list) -> dict | None:
    numeric_cols = [
        c["name"] for c in schema
        if c["type"] in ("integer", "float") and c["name"] in df.columns
        and not is_id_like(c, df)
    ]
    if len(numeric_cols) < 2:
        return None

    sub = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    corr = sub.corr(method="pearson")

    matrix = []
    for col_a in numeric_cols:
        for col_b in numeric_cols:
            val = corr.loc[col_a, col_b] if col_a in corr.index and col_b in corr.columns else None
            matrix.append({"x": col_a, "y": col_b, "value": _safe(val)})

    return {"columns": numeric_cols, "matrix": matrix}


def compute_scatter_pairs(df: pd.DataFrame, schema: list, correlation: dict) -> list:
    """Generate scatter data for the top 3 most correlated numeric pairs."""
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
        sub = df[[a, b]].apply(pd.to_numeric, errors="coerce").dropna()
        # sample to max 200 points for performance
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
        series = pd.to_numeric(df[col], errors="coerce").dropna()
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


def compute_observations(df: pd.DataFrame, schema: list, correlation: dict, outliers: list) -> list:
    """Generate plain-English analytical observations."""
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
    correlation = compute_correlation(df, schema)
    outliers = compute_outliers(df, schema)

    return {
        "dataset_id": dataset["id"],
        "filename": dataset.get("filename"),
        "observations": compute_observations(df, schema, correlation, outliers),
        "distributions": compute_distributions(df, schema),
        "correlation": correlation,
        "scatter_pairs": compute_scatter_pairs(df, schema, correlation),
        "outliers": outliers,
        "nulls": compute_nulls(df, schema),
    }
