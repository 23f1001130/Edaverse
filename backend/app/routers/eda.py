import json
import logging
import sqlite3
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from app.services.eda import (
    compute_eda, compute_target_analysis, stream_target_analysis,
)
from app.services.progressive_eda import stream_analysis
from app.services.auth import get_request_user_id
from app.services.modeling import build_html_report, compute_before_after_comparison, compute_model_importance
from app.services.store import get_dataset
from app.services.limiter import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/datasets/{dataset_id}/eda")
@limiter.limit("30/minute")
def get_eda(request: Request, dataset_id: str):
    dataset = get_dataset(dataset_id, get_request_user_id(request))
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    try:
        return compute_eda(dataset)
    except (OSError, ValueError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/datasets/{dataset_id}/eda/stream")
@limiter.limit("20/minute")
def stream_eda(request: Request, dataset_id: str):
    dataset = get_dataset(dataset_id, get_request_user_id(request))
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    def generate():
        try:
            for event in stream_analysis(dataset):
                yield f"data: {json.dumps(event, allow_nan=False)}\n\n"
        except (OSError, ValueError, TypeError, KeyError, TimeoutError, sqlite3.Error) as e:
            logger.warning("EDA stream failed for %s: %s: %s", dataset_id, type(e).__name__, e)
            yield f"data: {json.dumps({'stage': 'error', 'label': 'Analysis interrupted', 'progress': 0, 'data': {'error': str(e)}})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/datasets/{dataset_id}/target-analysis")
def get_target_analysis(request: Request, dataset_id: str, target: str = Query(..., min_length=1)):
    dataset = get_dataset(dataset_id, get_request_user_id(request))
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    result = compute_target_analysis(dataset, target)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/datasets/{dataset_id}/target-analysis/stream")
@limiter.limit("20/minute")
def stream_target_analysis_endpoint(request: Request, dataset_id: str, target: str = Query(..., min_length=1)):
    dataset = get_dataset(dataset_id, get_request_user_id(request))
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    def generate():
        try:
            for event in stream_target_analysis(dataset, target):
                yield f"data: {json.dumps(event)}\n\n"
        except (OSError, ValueError, TypeError, KeyError) as e:
            logger.warning("Target analysis stream failed for %s: %s: %s", dataset_id, type(e).__name__, e)
            yield f"data: {json.dumps({'stage': 'error', 'progress': 0.0, 'data': {'error': str(e)}})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/datasets/{dataset_id}/model-importance")
def get_model_importance(request: Request, dataset_id: str, target: str = Query(..., min_length=1)):
    dataset = get_dataset(dataset_id, get_request_user_id(request))
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    result = compute_model_importance(dataset, target)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/datasets/{dataset_id}/report")
def export_report(request: Request, dataset_id: str, target: str | None = None):
    dataset = get_dataset(dataset_id, get_request_user_id(request))
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
def get_before_after_comparison(request: Request, dataset_id: str):
    dataset = get_dataset(dataset_id, get_request_user_id(request))
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    result = compute_before_after_comparison(dataset)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
