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
    schema = dataset.get("schema", [])
    shape = dataset.get("shape", {}) or {}
    rows = shape.get("rows") or comparison.get("current", {}).get("rows") or 0
    cols = shape.get("columns") or comparison.get("current", {}).get("columns") or len(schema)

    def esc(v):
        return html.escape("" if v is None else str(v))

    def pct(v, suffix: str = "%"):
        if v is None:
            return "n/a"
        return f"{v}{suffix}"

    def fmt(v):
        if v is None:
            return "n/a"
        if isinstance(v, float):
            return f"{v:,.4g}"
        if isinstance(v, int):
            return f"{v:,}"
        return esc(v)

    def bar(value, max_value=100, color="var(--accent)"):
        try:
            width = max(0, min(100, float(value) / max(float(max_value), 1) * 100))
        except Exception:
            width = 0
        return f"<span class='bar'><span style='width:{width:.1f}%;background:{color}'></span></span>"

    def badge(text, tone="neutral"):
        return f"<span class='badge {tone}'>{esc(text)}</span>"

    def empty_row(cols_count: int, text: str):
        return f"<tr><td colspan='{cols_count}' class='empty'>{esc(text)}</td></tr>"

    def infer_target_column():
        signals = {
            "target": 5, "label": 5, "outcome": 5, "class": 4, "result": 4,
            "churn": 5, "survived": 5, "default": 5, "fraud": 5, "converted": 5,
            "conversion": 4, "sale": 3, "sales": 3, "revenue": 4, "price": 3,
            "amount": 2, "value": 2, "rating": 3, "score": 3,
        }
        candidates = []
        for col in schema:
            name = col.get("name", "")
            lower = name.lower()
            ctype = col.get("type")
            if ctype == "datetime" or any(k in lower for k in ("id", "uuid", "key", "timestamp")):
                continue
            unique = col.get("unique")
            null_pct = col.get("null_pct") or 0
            score = 0
            for token, weight in signals.items():
                if token in lower:
                    score += weight
            if ctype in ("categorical", "boolean") and (unique is None or 2 <= unique <= 30):
                score += 2
            if ctype in ("integer", "float") and (unique is None or unique > 10):
                score += 1
            if null_pct > 30:
                score -= 2
            if score > 0:
                candidates.append({"name": name, "type": ctype, "score": score, "null_pct": null_pct})
        candidates.sort(key=lambda c: (c["score"], -c["null_pct"]), reverse=True)
        return candidates[0] if candidates else None

    inferred_target = infer_target_column()
    model_target = target or (inferred_target["name"] if inferred_target and inferred_target["score"] >= 6 else None)
    model = None
    if model_target:
        try:
            model = compute_model_importance(dataset, model_target)
        except Exception:
            model = None

    total_cells = max(int(rows or 0) * max(int(cols or 0), 1), 1)
    total_nulls = sum(int(c.get("null_count", 0) or 0) for c in schema)
    missing_pct = round(total_nulls / total_cells * 100, 1)
    duplicate_rows = comparison.get("current", {}).get("duplicate_rows", 0) or 0
    duplicate_pct = round(duplicate_rows / max(int(rows or 0), 1) * 100, 1)
    outlier_cols = eda.get("numeric_profile", {}).get("outlier_columns", 0) or 0
    skewed_cols = eda.get("numeric_profile", {}).get("skewed_count", 0) or 0
    high_card_cols = eda.get("categorical_profile", {}).get("high_cardinality_count", 0) or 0
    imbalanced_cols = eda.get("categorical_profile", {}).get("imbalanced_count", 0) or 0
    health_score = int(max(0, min(100, 100 - missing_pct * 1.2 - duplicate_pct * 1.5 - outlier_cols * 3 - high_card_cols * 2 - skewed_cols)))
    health_tone = "good" if health_score >= 80 else "warn" if health_score >= 55 else "bad"
    health_label = "Analysis ready" if health_score >= 80 else "Needs analyst review" if health_score >= 55 else "High data risk"

    type_counts = {}
    for col in schema:
        type_counts[col.get("type", "unknown")] = type_counts.get(col.get("type", "unknown"), 0) + 1
    type_cards = "".join(
        f"<div class='type-pill'><span>{esc(k.title())}</span><strong>{v}</strong></div>"
        for k, v in sorted(type_counts.items(), key=lambda kv: kv[0])
    )

    observations = eda.get("observations", [])
    obs_cards = "".join(
        f"<li><span>{esc(o.get('text', ''))}</span></li>"
        for o in observations[:8]
    ) or "<li><span>No major automated observations were produced.</span></li>"

    nulls = sorted(
        [n for n in eda.get("nulls", []) if (n.get("null_pct") or 0) > 0],
        key=lambda x: x.get("null_pct", 0),
        reverse=True,
    )[:12]
    null_rows = "".join(
        f"<tr><td><strong>{esc(n['column'])}</strong></td><td>{pct(n.get('null_pct'))}</td>"
        f"<td>{fmt(n.get('null_count'))}</td><td>{bar(n.get('null_pct') or 0, 100, 'var(--danger)')}</td></tr>"
        for n in nulls
    ) or empty_row(4, "No missing values detected in the tracked columns.")

    num_rows = "".join(
        f"<tr><td><strong>{esc(r['column'])}</strong></td><td>{fmt(r.get('skewness'))}</td>"
        f"<td>{fmt(r.get('outlier_count'))}</td><td>{pct(r.get('outlier_pct'))}</td>"
        f"<td>{fmt(r.get('mean'))}</td><td>{fmt(r.get('std'))}</td></tr>"
        for r in eda.get("numeric_profile", {}).get("columns", [])[:12]
    ) or empty_row(6, "No numeric columns were available for numeric triage.")

    cat_rows = "".join(
        f"<tr><td><strong>{esc(r['column'])}</strong></td><td>{fmt(r.get('unique'))}</td>"
        f"<td>{pct(r.get('freq_pct'))}</td><td>{bar(r.get('freq_pct') or 0, 100, 'var(--teal)')}</td>"
        f"<td>{badge(r.get('strategy'), 'info' if r.get('strategy') != 'high-cardinality' else 'warn')}</td></tr>"
        for r in eda.get("categorical_profile", {}).get("columns", [])[:12]
    ) or empty_row(5, "No categorical columns were available for categorical triage.")

    corr_pairs = []
    corr = eda.get("correlation") or {}
    seen = set()
    for cell in corr.get("matrix", []) or []:
        a, b, value = cell.get("x"), cell.get("y"), cell.get("value")
        if not a or not b or a == b or value is None:
            continue
        key = tuple(sorted([a, b]))
        if key in seen:
            continue
        seen.add(key)
        corr_pairs.append((a, b, value, abs(value)))
    corr_pairs.sort(key=lambda x: x[3], reverse=True)
    corr_rows = "".join(
        f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{fmt(v)}</td>"
        f"<td>{bar(abs_v, 1, 'var(--accent)')}</td>"
        f"<td>{badge('Strong' if abs_v >= 0.7 else 'Moderate' if abs_v >= 0.4 else 'Weak', 'warn' if abs_v >= 0.7 else 'neutral')}</td></tr>"
        for a, b, v, abs_v in corr_pairs[:8]
    ) or empty_row(5, "No usable numeric correlation pairs were found.")

    missing_pairs = (eda.get("missingness") or {}).get("flagged_pairs", []) or []
    missing_pair_rows = "".join(
        f"<tr><td>{esc(r.get('a'))}</td><td>{esc(r.get('b'))}</td><td>{pct(r.get('actual_pct'))}</td>"
        f"<td>{pct(r.get('expected_pct'))}</td><td>{fmt(r.get('lift'))}x</td></tr>"
        for r in missing_pairs[:5]
    ) or empty_row(5, "No unusual missingness co-occurrence patterns were detected.")

    datetime_cols = [c for c in schema if c.get("type") == "datetime"]
    identifier_cols = [
        r for r in eda.get("categorical_profile", {}).get("columns", [])
        if r.get("strategy") == "identifier"
    ][:8]
    segment_cols = [
        r for r in eda.get("categorical_profile", {}).get("columns", [])
        if r.get("strategy") in ("one-hot", "ordinal/frequency") and not r.get("is_imbalanced")
    ][:8]
    dataset_signals = []
    if datetime_cols:
        dataset_signals.append(f"{len(datetime_cols)} datetime column(s): time-series or cohort analysis is likely useful.")
    if identifier_cols:
        dataset_signals.append(f"{len(identifier_cols)} identifier-like column(s): keep for joins/audit, exclude from modelling features.")
    if segment_cols:
        dataset_signals.append(f"{len(segment_cols)} segment-ready categorical column(s): good candidates for grouped KPI cuts.")
    if inferred_target:
        dataset_signals.append(f"Likely target candidate: {inferred_target['name']} ({inferred_target['type']}).")
    signal_items = "".join(f"<li>{esc(s)}</li>" for s in dataset_signals) or "<li>No strong structural signals were detected; start with quality checks and univariate profiling.</li>"

    recommendations = []
    if missing_pct >= 10:
        recommendations.append("Prioritize missing-value strategy before modelling. Separate structural nulls from data-entry gaps.")
    if duplicate_rows:
        recommendations.append("Review duplicate rows. If they are not valid repeated events, deduplicate before KPI reporting.")
    if corr_pairs and corr_pairs[0][3] >= 0.9:
        recommendations.append("At least one pair of numeric columns is highly correlated. For modelling, remove or regularize redundant features.")
    if high_card_cols:
        recommendations.append("High-cardinality categorical features need careful encoding. Prefer frequency, target, or embedding-style encodings over wide one-hot expansion.")
    if skewed_cols:
        recommendations.append("Skewed numeric columns may need log, winsorization, or robust scaling before statistical modelling.")
    if outlier_cols:
        recommendations.append("Investigate outliers as business events first. Treat them only after confirming they are errors or unwanted extremes.")
    if datetime_cols:
        recommendations.append("Use the datetime fields to check seasonality, leakage, train/test split boundaries, and trend drift.")
    if inferred_target and not target:
        recommendations.append(f"Consider using {inferred_target['name']} as the analysis target, then rerun the report with an explicit target when needed.")
    if not recommendations:
        recommendations.append("Dataset looks relatively clean. Move into hypothesis testing, segmentation, and model validation.")
    rec_items = "".join(f"<li>{esc(r)}</li>" for r in recommendations[:8])

    model_rows = ""
    if model and "importance" in model:
        model_rows = "".join(
            f"<tr><td><strong>{esc(r['feature'])}</strong></td><td>{fmt(r['permutation_importance'])}</td>"
            f"<td>{bar(r['permutation_importance'] or 0, max([x.get('permutation_importance') or 0 for x in model['importance'][:15]] + [1]), 'var(--success)')}</td>"
            f"<td>{fmt(r['coefficient_importance'])}</td></tr>"
            for r in model["importance"][:15]
        )
    model_section = ""
    if model_rows:
        model_note = "Inferred target" if not target and model_target else "Selected target"
        model_section = (
            f"<section class='section'><div class='section-head'><div><p class='eyebrow'>Predictive signal</p>"
            f"<h2>Model Importance: {esc(model_target)}</h2></div>{badge(model_note, 'info')}</div>"
            f"<div class='model-summary'>"
            f"<div><span>Task</span><strong>{esc(model.get('task'))}</strong></div>"
            f"<div><span>Metric</span><strong>{esc(model.get('metric'))}: {fmt(model.get('baseline_score'))}</strong></div>"
            f"<div><span>Rows used</span><strong>{fmt(model.get('rows_used'))}</strong></div>"
            f"<div><span>Features used</span><strong>{fmt(model.get('features_used'))}</strong></div>"
            f"</div><table><tr><th>Feature</th><th>Permutation importance</th><th>Signal bar</th><th>Coefficient importance</th></tr>{model_rows}</table>"
            f"<p class='note'>{esc(model.get('note'))}</p></section>"
        )

    comparison_html = ""
    if comparison.get("comparisons"):
        blocks = []
        for comp in comparison["comparisons"]:
            added = ", ".join(esc(c) for c in comp.get("added_columns", [])[:16]) or "None"
            dropped = ", ".join(esc(c) for c in comp.get("dropped_columns", [])[:16]) or "None"
            null_rows_cmp = "".join(
                f"<tr><td><strong>{esc(r['column'])}</strong></td><td>{pct(r['before_null_pct'])}</td>"
                f"<td>{pct(r['after_null_pct'])}</td><td>{pct(r['delta_pct'])}</td></tr>"
                for r in comp.get("null_changes", [])[:10]
            ) or empty_row(4, "No meaningful null-rate changes were detected.")
            blocks.append(
                f"<div class='comparison-block'><h3>{esc(comp['label'])}</h3>"
                f"<div class='metric-grid compact'>"
                f"<div class='metric'><span>Rows changed</span><strong>{fmt(comp['row_delta'])}</strong></div>"
                f"<div class='metric'><span>Columns changed</span><strong>{fmt(comp['column_delta'])}</strong></div>"
                f"<div class='metric'><span>Null % before</span><strong>{pct(comp['before']['null_pct'])}</strong></div>"
                f"<div class='metric'><span>Null % after</span><strong>{pct(comp['after']['null_pct'])}</strong></div>"
                f"</div><div class='change-list'><p><b>Added columns:</b> {added}</p><p><b>Dropped columns:</b> {dropped}</p></div>"
                f"<table><tr><th>Column</th><th>Before null %</th><th>After null %</th><th>Delta</th></tr>{null_rows_cmp}</table>"
                f"</div>"
            )
        comparison_html = (
            "<section class='section'><div class='section-head'><div><p class='eyebrow'>Workflow impact</p>"
            "<h2>Before/After Comparison</h2></div></div>"
            + "".join(blocks)
            + "</section>"
        )

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Dataflow EDA Report</title>
<style>
:root{{--ink:#17202a;--muted:#657080;--line:#dde5ed;--soft:#f6f8fb;--panel:#ffffff;--accent:#4f6df5;--teal:#1fa6a3;--success:#2c9c69;--warning:#cf7b18;--danger:#d44b4b;--shadow:0 18px 45px rgba(31,45,61,.10)}}
*{{box-sizing:border-box}} body{{margin:0;background:linear-gradient(180deg,#eef3f7 0,#fbfcfd 260px);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif;line-height:1.48}}
.page{{max-width:1180px;margin:0 auto;padding:34px 24px 54px}}
.hero{{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:26px;align-items:stretch;margin-bottom:22px}}
.hero-main{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:30px;box-shadow:var(--shadow);position:relative;overflow:hidden}}
.hero-main:before{{content:"";position:absolute;inset:0 0 auto 0;height:5px;background:linear-gradient(90deg,var(--accent),var(--teal),#e6a540)}}
.eyebrow{{margin:0 0 8px;color:var(--teal);font-size:11px;font-weight:800;letter-spacing:0;text-transform:uppercase}}
h1{{font-size:34px;line-height:1.08;margin:0 0 10px;letter-spacing:0}} h2{{font-size:22px;margin:0}} h3{{font-size:16px;margin:18px 0 10px}}
.subtitle{{color:var(--muted);max-width:820px;margin:0;font-size:15px}}
.score-card{{background:#17202a;color:white;border-radius:10px;padding:24px;box-shadow:var(--shadow);display:flex;flex-direction:column;justify-content:space-between}}
.score-ring{{width:126px;height:126px;border-radius:50%;display:grid;place-items:center;margin:auto;background:conic-gradient(var(--score-color) var(--score-angle),rgba(255,255,255,.16) 0);position:relative}}
.score-ring:after{{content:"";position:absolute;inset:12px;border-radius:50%;background:#17202a}} .score-ring strong{{position:relative;z-index:1;font-size:34px}} .score-label{{text-align:center;margin-top:14px;font-weight:800}}
.metric-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}} .metric-grid.compact{{grid-template-columns:repeat(4,1fr);margin:12px 0}}
.metric{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 15px;min-height:86px}} .metric span,.model-summary span{{display:block;color:var(--muted);font-size:12px;font-weight:700;text-transform:uppercase}} .metric strong{{display:block;margin-top:7px;font-size:24px}}
.type-row{{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}} .type-pill{{border:1px solid var(--line);background:#f9fbfd;border-radius:999px;padding:7px 12px;display:flex;gap:8px;align-items:center}} .type-pill span{{color:var(--muted);font-size:12px}} .type-pill strong{{font-size:13px}}
.section{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:24px;margin-top:18px;box-shadow:0 10px 28px rgba(31,45,61,.06)}} .section-head{{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:14px}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:18px}} .insight-list,.recommendations{{margin:0;padding:0;list-style:none}} .insight-list li,.recommendations li{{border-top:1px solid var(--line);padding:12px 0;color:#263443}} .insight-list li:first-child,.recommendations li:first-child{{border-top:0}}
table{{border-collapse:separate;border-spacing:0;width:100%;overflow:hidden;border:1px solid var(--line);border-radius:8px;background:white}} th{{background:#f3f6f9;color:#455363;text-transform:uppercase;font-size:11px;letter-spacing:0}} td,th{{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line);font-size:13px;vertical-align:middle}} tr:last-child td{{border-bottom:0}} .empty{{color:var(--muted);text-align:center;padding:22px}}
.bar{{display:block;height:8px;background:#e9eef4;border-radius:99px;overflow:hidden;min-width:110px}} .bar span{{display:block;height:100%;border-radius:inherit}}
.badge{{display:inline-flex;align-items:center;border-radius:999px;padding:5px 9px;font-size:11px;font-weight:800;background:#edf1f5;color:#455363}} .badge.good{{background:#e7f7ef;color:#197047}} .badge.warn{{background:#fff2df;color:#98530b}} .badge.bad{{background:#ffe8e8;color:#a83131}} .badge.info{{background:#e9f3ff;color:#3156aa}}
.signals{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} .signals ul{{margin:0;padding-left:18px;color:#334252}} .signals li{{margin:8px 0}}
.model-summary{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0}} .model-summary div{{border:1px solid var(--line);background:#fbfcfe;border-radius:8px;padding:12px}} .model-summary strong{{display:block;margin-top:6px;font-size:17px}}
.comparison-block{{border-top:1px solid var(--line);padding-top:14px;margin-top:12px}} .comparison-block:first-of-type{{border-top:0;padding-top:0}} .change-list{{display:grid;grid-template-columns:1fr 1fr;gap:10px;color:#334252}} .change-list p{{background:#f7f9fb;border-radius:8px;padding:10px;margin:0}}
.note{{color:var(--muted);font-size:12px;margin:12px 0 0}} .footer{{color:var(--muted);font-size:12px;text-align:center;margin-top:22px}}
@media(max-width:860px){{.page{{padding:18px}}.hero,.two-col,.signals{{grid-template-columns:1fr}}.metric-grid,.metric-grid.compact,.model-summary{{grid-template-columns:repeat(2,1fr)}}h1{{font-size:28px}}}}
@media print{{body{{background:white}}.page{{max-width:none;padding:0}}.section,.hero-main,.score-card,.metric{{box-shadow:none}}}}
</style></head>
<body>
<main class="page">
<header class="hero">
  <div class="hero-main">
    <p class="eyebrow">Dataflow analyst report</p>
    <h1>{esc(dataset.get('filename', 'Dataset'))}</h1>
    <p class="subtitle">A decision-ready EDA summary focused on data quality, modelling readiness, feature risk, and the next analysis moves a senior analyst would check before presenting or training models.</p>
    <div class="type-row">{type_cards}</div>
  </div>
  <aside class="score-card" style="--score-angle:{health_score * 3.6:.1f}deg;--score-color:var(--{'success' if health_tone == 'good' else 'warning' if health_tone == 'warn' else 'danger'});">
    <div class="score-ring"><strong>{health_score}</strong></div>
    <div class="score-label">{esc(health_label)}</div>
  </aside>
</header>

<section class="metric-grid">
  <div class="metric"><span>Rows</span><strong>{fmt(rows)}</strong></div>
  <div class="metric"><span>Columns</span><strong>{fmt(cols)}</strong></div>
  <div class="metric"><span>Missing cells</span><strong>{pct(missing_pct)}</strong></div>
  <div class="metric"><span>Duplicate rows</span><strong>{fmt(duplicate_rows)}</strong></div>
</section>

<section class="section two-col">
  <div>
    <p class="eyebrow">Executive summary</p>
    <h2>What Stands Out</h2>
    <ul class="insight-list">{obs_cards}</ul>
  </div>
  <div>
    <p class="eyebrow">Analyst actions</p>
    <h2>Recommended Next Steps</h2>
    <ul class="recommendations">{rec_items}</ul>
  </div>
</section>

<section class="section">
  <div class="section-head"><div><p class="eyebrow">Dataset intelligence</p><h2>Dynamic Signals</h2></div>{badge(health_label, health_tone)}</div>
  <div class="signals">
    <ul>{signal_items}</ul>
    <div class="metric-grid compact">
      <div class="metric"><span>Skewed numerics</span><strong>{fmt(skewed_cols)}</strong></div>
      <div class="metric"><span>Outlier columns</span><strong>{fmt(outlier_cols)}</strong></div>
      <div class="metric"><span>High-cardinality</span><strong>{fmt(high_card_cols)}</strong></div>
      <div class="metric"><span>Imbalanced categoricals</span><strong>{fmt(imbalanced_cols)}</strong></div>
    </div>
  </div>
</section>

<section class="section">
  <div class="section-head"><div><p class="eyebrow">Quality profile</p><h2>Missingness</h2></div>{badge('Clean' if not nulls else 'Review', 'good' if not nulls else 'warn')}</div>
  <table><tr><th>Column</th><th>Null %</th><th>Null count</th><th>Scale</th></tr>{null_rows}</table>
  <h3>Missingness Co-occurrence</h3>
  <table><tr><th>Column A</th><th>Column B</th><th>Actual overlap</th><th>Expected overlap</th><th>Lift</th></tr>{missing_pair_rows}</table>
</section>

<section class="section">
  <div class="section-head"><div><p class="eyebrow">Feature triage</p><h2>Numeric Columns</h2></div>{badge(f'{outlier_cols} with outliers', 'warn' if outlier_cols else 'good')}</div>
  <table><tr><th>Column</th><th>Skewness</th><th>Outliers</th><th>Outlier %</th><th>Mean</th><th>Std dev</th></tr>{num_rows}</table>
</section>

<section class="section">
  <div class="section-head"><div><p class="eyebrow">Feature triage</p><h2>Categorical Columns</h2></div>{badge(f'{high_card_cols} high-cardinality', 'warn' if high_card_cols else 'good')}</div>
  <table><tr><th>Column</th><th>Unique</th><th>Top share</th><th>Dominance</th><th>Encoding signal</th></tr>{cat_rows}</table>
</section>

<section class="section">
  <div class="section-head"><div><p class="eyebrow">Relationships</p><h2>Correlation Watchlist</h2></div>{badge(corr.get('method', 'pearson'), 'info') if corr else ''}</div>
  <table><tr><th>Column A</th><th>Column B</th><th>Correlation</th><th>Strength</th><th>Label</th></tr>{corr_rows}</table>
</section>

{comparison_html}
{model_section}
<p class="footer">Generated by Dataflow. Treat this as analyst triage: validate findings against business context before production decisions.</p>
</main>
</body></html>"""
