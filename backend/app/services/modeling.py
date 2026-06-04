import html
import math
from pathlib import Path

import numpy as np
import pandas as pd

from app.services.eda import compute_eda, _load_df

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "datasets"


def _safe(v):
    if v is None:
        return None
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 4)
    except Exception:
        return v


def _schema_by_name(schema: list) -> dict:
    return {c["name"]: c for c in schema}


def _read_dataset_file(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        if path.suffix == ".parquet":
            return pd.read_parquet(path)
        return pd.read_csv(path)
    except Exception:
        return None


def _df_summary(df: pd.DataFrame) -> dict:
    total_cells = max(int(df.shape[0] * df.shape[1]), 1)
    nulls = int(df.isna().sum().sum())
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "total_nulls": nulls,
        "null_pct": _safe(nulls / total_cells * 100),
        "duplicate_rows": int(df.duplicated().sum()) if len(df) else 0,
    }


def _compare_frames(before: pd.DataFrame, after: pd.DataFrame, label: str) -> dict:
    before_cols = set(before.columns)
    after_cols = set(after.columns)
    shared = sorted(before_cols & after_cols)
    added = sorted(after_cols - before_cols)
    dropped = sorted(before_cols - after_cols)
    null_changes = []
    type_changes = []

    before_rows = max(len(before), 1)
    after_rows = max(len(after), 1)
    for col in shared:
        before_null = int(before[col].isna().sum())
        after_null = int(after[col].isna().sum())
        before_pct = before_null / before_rows * 100
        after_pct = after_null / after_rows * 100
        delta = after_pct - before_pct
        if abs(delta) >= 0.1 or before_null != after_null:
            null_changes.append({
                "column": col,
                "before_null_pct": _safe(before_pct),
                "after_null_pct": _safe(after_pct),
                "delta_pct": _safe(delta),
                "before_nulls": before_null,
                "after_nulls": after_null,
            })
        before_type = str(before[col].dtype)
        after_type = str(after[col].dtype)
        if before_type != after_type:
            type_changes.append({"column": col, "before": before_type, "after": after_type})

    null_changes.sort(key=lambda x: abs(x["delta_pct"] or 0), reverse=True)
    return {
        "label": label,
        "available": True,
        "before": _df_summary(before),
        "after": _df_summary(after),
        "row_delta": int(len(after) - len(before)),
        "column_delta": int(len(after.columns) - len(before.columns)),
        "added_columns": added[:40],
        "dropped_columns": dropped[:40],
        "null_changes": null_changes[:20],
        "type_changes": type_changes[:20],
    }


def compute_before_after_comparison(dataset: dict) -> dict:
    dataset_id = dataset["id"]
    current = _load_df(dataset)
    if current is None:
        return {"error": "Current dataset data not found"}

    original = _read_dataset_file(DATA_DIR / f"{dataset_id}_original.parquet")
    if original is None:
        original = _read_dataset_file(DATA_DIR / f"{dataset_id}_original.csv")
    pre_feat = _read_dataset_file(DATA_DIR / f"{dataset_id}_pre_feat.parquet")
    if pre_feat is None:
        pre_feat = _read_dataset_file(DATA_DIR / f"{dataset_id}_pre_feat.csv")

    comparisons = []
    if original is not None:
        comparisons.append(_compare_frames(original, current, "Original vs current"))
    if pre_feat is not None:
        comparisons.append(_compare_frames(pre_feat, current, "Before feature engineering vs current"))

    return {
        "dataset_id": dataset_id,
        "filename": dataset.get("filename"),
        "current": _df_summary(current),
        "comparisons": comparisons,
        "has_history": bool(comparisons),
    }


def _prepare_features(df: pd.DataFrame, schema: list, target: str, max_features: int = 80):
    parts = []
    feature_sources = []
    for col_info in schema:
        col = col_info["name"]
        if col == target or col not in df.columns:
            continue
        ctype = col_info.get("type")
        if ctype in ("integer", "float"):
            s = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
            if s.notna().sum() < 3 or s.nunique(dropna=True) <= 1:
                continue
            parts.append(s.fillna(s.median()).to_frame(col))
            feature_sources.append((col, [col]))
        elif ctype in ("categorical", "text", "boolean"):
            nunique = df[col].nunique(dropna=True)
            if nunique <= 1:
                continue
            if nunique <= 12:
                dummies = pd.get_dummies(df[col].fillna("__missing__").astype(str), prefix=col, dtype=float)
                cols = list(dummies.columns)
                parts.append(dummies)
                feature_sources.append((col, cols))
            else:
                freq_col = f"{col}__freq_model"
                freq = df[col].value_counts(normalize=True, dropna=True)
                parts.append(df[col].map(freq).fillna(0).astype(float).to_frame(freq_col))
                feature_sources.append((col, [freq_col]))
    if not parts:
        return None, []
    x = pd.concat(parts, axis=1)
    if x.shape[1] > max_features:
        variances = x.var().sort_values(ascending=False).head(max_features).index
        x = x[variances]
        feature_sources = [(src, [c for c in cols if c in x.columns]) for src, cols in feature_sources]
        feature_sources = [(src, cols) for src, cols in feature_sources if cols]
    std = x.std().replace(0, np.nan)
    x = ((x - x.mean()) / std).replace([np.inf, -np.inf], np.nan).fillna(0)
    return x, feature_sources


def _split_indices(n: int, seed: int = 7):
    rng = np.random.default_rng(seed)
    idx = np.arange(n)
    rng.shuffle(idx)
    test_size = max(1, int(n * 0.25))
    return idx[test_size:], idx[:test_size]


def _ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float = 1.0):
    x_aug = np.c_[np.ones(len(x)), x]
    eye = np.eye(x_aug.shape[1])
    eye[0, 0] = 0
    return np.linalg.pinv(x_aug.T @ x_aug + alpha * eye) @ x_aug.T @ y


def _ridge_predict(x: np.ndarray, coef: np.ndarray):
    return np.c_[np.ones(len(x)), x] @ coef


def _r2(y_true, y_pred):
    denom = float(((y_true - y_true.mean()) ** 2).sum())
    if denom == 0:
        return None
    return 1 - float(((y_true - y_pred) ** 2).sum()) / denom


def _accuracy(y_true, y_pred):
    return float((y_true == y_pred).mean()) if len(y_true) else None


def compute_model_importance(dataset: dict, target: str) -> dict:
    df = _load_df(dataset)
    if df is None:
        rows = dataset.get("sample_rows", [])
        if not rows:
            return {"error": "No data available for model importance"}
        df = pd.DataFrame(rows)

    schema = dataset.get("schema", [])
    by_name = _schema_by_name(schema)
    if target not in df.columns or target not in by_name:
        return {"error": "Target column not found"}

    x, feature_sources = _prepare_features(df, schema, target)
    if x is None or x.shape[1] == 0:
        return {"error": "No usable features for baseline model"}

    target_info = by_name[target]
    target_type = target_info.get("type")
    y_raw = df[target]
    is_regression = target_type in ("integer", "float") and y_raw.nunique(dropna=True) > 10
    mask = y_raw.notna()
    if is_regression:
        y = pd.to_numeric(y_raw, errors="coerce").replace([np.inf, -np.inf], np.nan)
        mask = y.notna()
    else:
        y = y_raw.astype(str)

    x = x.loc[mask]
    y = y.loc[mask]
    if len(x) < 8:
        return {"error": "Need at least 8 non-null target rows for model importance"}

    train_idx, test_idx = _split_indices(len(x))
    x_np = x.to_numpy(dtype=float)
    rng = np.random.default_rng(11)

    if is_regression:
        y_np = y.to_numpy(dtype=float)
        coef = _ridge_fit(x_np[train_idx], y_np[train_idx], alpha=1.0)
        pred = _ridge_predict(x_np[test_idx], coef)
        baseline = _r2(y_np[test_idx], pred)
        metric_name = "r2"
        lower_is_better = False
        coef_abs = np.abs(coef[1:])
    else:
        classes = sorted(y.unique(), key=str)
        y_codes = np.array([classes.index(v) for v in y], dtype=int)
        y_train_onehot = np.zeros((len(train_idx), len(classes)))
        y_train_onehot[np.arange(len(train_idx)), y_codes[train_idx]] = 1
        coef = _ridge_fit(x_np[train_idx], y_train_onehot, alpha=1.0)
        scores = _ridge_predict(x_np[test_idx], coef)
        pred_codes = scores.argmax(axis=1)
        baseline = _accuracy(y_codes[test_idx], pred_codes)
        metric_name = "accuracy"
        lower_is_better = False
        coef_abs = np.abs(coef[1:]).mean(axis=1)

    if baseline is None:
        return {"error": "Baseline model could not be scored"}

    col_to_source = {}
    for source, cols in feature_sources:
        for col in cols:
            col_to_source[col] = source

    importances = {}
    for j, col in enumerate(x.columns):
        x_perm = x_np[test_idx].copy()
        rng.shuffle(x_perm[:, j])
        if is_regression:
            score = _r2(y_np[test_idx], _ridge_predict(x_perm, coef))
        else:
            score = _accuracy(y_codes[test_idx], _ridge_predict(x_perm, coef).argmax(axis=1))
        drop = baseline - score if score is not None else 0
        source = col_to_source.get(col, col)
        item = importances.setdefault(source, {"feature": source, "permutation_importance": 0.0, "coefficient_importance": 0.0})
        item["permutation_importance"] += max(0.0, float(drop))
        item["coefficient_importance"] += float(coef_abs[j])

    rows = list(importances.values())
    rows.sort(key=lambda r: (r["permutation_importance"], r["coefficient_importance"]), reverse=True)
    for r in rows:
        r["permutation_importance"] = _safe(r["permutation_importance"])
        r["coefficient_importance"] = _safe(r["coefficient_importance"])

    return {
        "target": target,
        "task": "regression" if is_regression else "classification",
        "metric": metric_name,
        "baseline_score": _safe(baseline),
        "rows_used": int(len(x)),
        "features_used": int(x.shape[1]),
        "importance": rows[:20],
        "note": "Permutation importance is measured as validation score drop after shuffling each source feature.",
    }


def build_html_report(dataset: dict, target: str | None = None) -> str:
    eda = compute_eda(dataset)
    comparison = compute_before_after_comparison(dataset)
    model = None
    if target:
        try:
            model = compute_model_importance(dataset, target)
        except Exception:
            model = None

    def esc(v):
        return html.escape(str(v))

    obs = "".join(f"<li>{esc(o.get('text', ''))}</li>" for o in eda.get("observations", []))
    nulls = sorted(eda.get("nulls", []), key=lambda x: x.get("null_pct", 0), reverse=True)[:10]
    null_rows = "".join(f"<tr><td>{esc(n['column'])}</td><td>{n['null_pct']}%</td><td>{n['null_count']}</td></tr>" for n in nulls)
    num_rows = "".join(
        f"<tr><td>{esc(r['column'])}</td><td>{r.get('skewness')}</td><td>{r.get('outlier_count')}</td><td>{r.get('outlier_pct')}%</td></tr>"
        for r in eda.get("numeric_profile", {}).get("columns", [])[:12]
    )
    cat_rows = "".join(
        f"<tr><td>{esc(r['column'])}</td><td>{r.get('unique')}</td><td>{r.get('freq_pct')}%</td><td>{esc(r.get('strategy'))}</td></tr>"
        for r in eda.get("categorical_profile", {}).get("columns", [])[:12]
    )
    model_rows = ""
    if model and "importance" in model:
        model_rows = "".join(
            f"<tr><td>{esc(r['feature'])}</td><td>{r['permutation_importance']}</td><td>{r['coefficient_importance']}</td></tr>"
            for r in model["importance"][:15]
        )
    comparison_html = ""
    if comparison.get("comparisons"):
        blocks = []
        for comp in comparison["comparisons"]:
            added = ", ".join(esc(c) for c in comp.get("added_columns", [])[:16]) or "None"
            dropped = ", ".join(esc(c) for c in comp.get("dropped_columns", [])[:16]) or "None"
            null_rows_cmp = "".join(
                f"<tr><td>{esc(r['column'])}</td><td>{r['before_null_pct']}%</td><td>{r['after_null_pct']}%</td><td>{r['delta_pct']}%</td></tr>"
                for r in comp.get("null_changes", [])[:10]
            )
            blocks.append(
                f"<h3>{esc(comp['label'])}</h3>"
                f"<div class='grid'>"
                f"<div class='card'><div class='muted'>Rows changed</div><div class='value'>{comp['row_delta']}</div></div>"
                f"<div class='card'><div class='muted'>Columns changed</div><div class='value'>{comp['column_delta']}</div></div>"
                f"<div class='card'><div class='muted'>Null % before</div><div class='value'>{comp['before']['null_pct']}%</div></div>"
                f"<div class='card'><div class='muted'>Null % after</div><div class='value'>{comp['after']['null_pct']}%</div></div>"
                f"</div><p><b>Added columns:</b> {added}</p><p><b>Dropped columns:</b> {dropped}</p>"
                f"<table><tr><th>Column</th><th>Before null %</th><th>After null %</th><th>Delta</th></tr>{null_rows_cmp}</table>"
            )
        comparison_html = "<h2>Before/After Comparison</h2>" + "".join(blocks)

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Dataflow EDA Report</title>
<style>
body{{font-family:Inter,Segoe UI,Arial,sans-serif;margin:32px;color:#111827;line-height:1.45}}
h1,h2{{margin-bottom:8px}} .muted{{color:#6b7280}} table{{border-collapse:collapse;width:100%;margin:12px 0 24px}}
td,th{{border:1px solid #e5e7eb;padding:8px;text-align:left;font-size:13px}} th{{background:#f9fafb}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}} .card{{border:1px solid #e5e7eb;border-radius:8px;padding:14px}}
.value{{font-size:24px;font-weight:700}} ul{{padding-left:20px}}
</style></head>
<body>
<h1>{esc(dataset.get('filename', 'Dataset'))}</h1>
<p class="muted">Generated by Dataflow local EDA pipeline.</p>
<div class="grid">
<div class="card"><div class="muted">Rows</div><div class="value">{dataset.get('shape', {}).get('rows')}</div></div>
<div class="card"><div class="muted">Columns</div><div class="value">{dataset.get('shape', {}).get('columns')}</div></div>
<div class="card"><div class="muted">Skewed numerics</div><div class="value">{eda.get('numeric_profile', {}).get('skewed_count', 0)}</div></div>
<div class="card"><div class="muted">High-cardinality categoricals</div><div class="value">{eda.get('categorical_profile', {}).get('high_cardinality_count', 0)}</div></div>
</div>
<h2>Key Observations</h2><ul>{obs}</ul>
<h2>Missingness</h2><table><tr><th>Column</th><th>Null %</th><th>Null count</th></tr>{null_rows}</table>
<h2>Numeric Triage</h2><table><tr><th>Column</th><th>Skewness</th><th>Outliers</th><th>Outlier %</th></tr>{num_rows}</table>
<h2>Categorical Triage</h2><table><tr><th>Column</th><th>Unique</th><th>Top share</th><th>Encoding signal</th></tr>{cat_rows}</table>
{comparison_html}
{f'<h2>Model Importance: {esc(target)}</h2><p class="muted">{esc(model.get("task"))} baseline {esc(model.get("metric"))}: {esc(model.get("baseline_score"))}</p><table><tr><th>Feature</th><th>Permutation importance</th><th>Coefficient importance</th></tr>{model_rows}</table>' if model_rows else ''}
</body></html>"""
