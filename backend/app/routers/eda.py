import json
import os
import time
import logging
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from app.services.eda import (
    compute_eda, compute_target_analysis,
    _load_df, compute_distributions, compute_correlation, compute_outliers,
    compute_scatter_pairs, compute_missingness_cooccurrence, compute_missingness_matrix,
    compute_numeric_profile, compute_categorical_profile,
    compute_pca_projection, compute_pivot_heatmap, compute_observations, compute_nulls,
)
from app.services.modeling import build_html_report, compute_before_after_comparison, compute_model_importance
from app.services.store import get_dataset
from app.services.limiter import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/datasets/{dataset_id}/eda")
@limiter.limit("30/minute")
def get_eda(request: Request, dataset_id: str):
    dataset = get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    result = compute_eda(dataset)
    return result


@router.get("/datasets/{dataset_id}/eda/stream")
@limiter.limit("20/minute")
def stream_eda(request: Request, dataset_id: str):
    dataset = get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    STAGE_LABELS = {
        "loading": "Loading dataset…",
        "distributions": "Computing distributions…",
        "correlations": "Computing correlations…",
        "outliers": "Detecting outliers…",
        "advanced": "Building advanced metrics…",
        "complete": "Done",
        "error": "Error",
    }

    _STREAM_TIMEOUT = int(os.getenv("EDA_STREAM_TIMEOUT_SECS", "300"))

    def generate():
        def sse(stage: str, progress: float, data=None) -> str:
            payload = {"stage": stage, "label": STAGE_LABELS.get(stage, stage), "progress": round(progress, 2)}
            if data is not None:
                payload["data"] = data
            return f"data: {json.dumps(payload)}\n\n"

        deadline = time.monotonic() + _STREAM_TIMEOUT

        def check_deadline(next_stage: str) -> None:
            if time.monotonic() > deadline:
                raise TimeoutError(f"EDA timed out before {next_stage} (limit: {_STREAM_TIMEOUT}s)")

        try:
            import pandas as pd
            yield sse("loading", 0.05)
            df = _load_df(dataset)
            if df is None:
                rows = dataset.get("sample_rows", [])
                if not rows:
                    yield sse("error", 0.0, {"error": "No data available for EDA"})
                    return
                df = pd.DataFrame(rows)

            schema = dataset.get("schema", [])

            check_deadline("distributions")
            yield sse("distributions", 0.20)
            distributions = compute_distributions(df, schema)

            check_deadline("correlations")
            yield sse("correlations", 0.42)
            correlation = compute_correlation(df, schema, "pearson")
            spearman = compute_correlation(df, schema, "spearman")
            scatter_pairs = compute_scatter_pairs(df, schema, correlation)

            check_deadline("outliers")
            yield sse("outliers", 0.60)
            outliers = compute_outliers(df, schema)

            check_deadline("advanced")
            yield sse("advanced", 0.76)
            nulls = compute_nulls(df, schema)
            observations = compute_observations(df, schema, correlation, outliers)
            missingness = compute_missingness_cooccurrence(df, schema)
            missingness_matrix = compute_missingness_matrix(df, schema)
            numeric_profile = compute_numeric_profile(df, schema, outliers)
            categorical_profile = compute_categorical_profile(df, schema)
            pca = compute_pca_projection(df, schema)
            pivot_heatmap = compute_pivot_heatmap(df, schema)

            result = {
                "dataset_id": dataset["id"],
                "filename": dataset.get("filename"),
                "observations": observations,
                "distributions": distributions,
                "correlation": correlation,
                "correlation_spearman": spearman,
                "scatter_pairs": scatter_pairs,
                "outliers": outliers,
                "nulls": nulls,
                "missingness": missingness,
                "missingness_matrix": missingness_matrix,
                "numeric_profile": numeric_profile,
                "categorical_profile": categorical_profile,
                "pca": pca,
                "pivot_heatmap": pivot_heatmap,
            }
            yield sse("complete", 1.0, result)
        except TimeoutError as e:
            logger.warning("EDA stream timed out for %s: %s", dataset_id, e)
            yield sse("error", 0.0, {"error": str(e)})
        except (OSError, ValueError, TypeError, KeyError) as e:
            logger.warning("EDA stream failed for %s: %s: %s", dataset_id, type(e).__name__, e)
            yield sse("error", 0.0, {"error": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/datasets/{dataset_id}/target-analysis")
def get_target_analysis(dataset_id: str, target: str = Query(..., min_length=1)):
    dataset = get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    result = compute_target_analysis(dataset, target)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/datasets/{dataset_id}/model-importance")
def get_model_importance(dataset_id: str, target: str = Query(..., min_length=1)):
    dataset = get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    result = compute_model_importance(dataset, target)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/datasets/{dataset_id}/report")
def export_report(dataset_id: str, target: str | None = None):
    dataset = get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    html = build_html_report(dataset, target)
    fname = (dataset.get("filename", "dataset").rsplit(".", 1)[0]) + "_eda_report.html"
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/datasets/{dataset_id}/comparison")
def get_before_after_comparison(dataset_id: str):
    dataset = get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    result = compute_before_after_comparison(dataset)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
