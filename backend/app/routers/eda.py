from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from app.services.eda import compute_eda, compute_target_analysis
from app.services.modeling import build_html_report, compute_before_after_comparison, compute_model_importance
from app.services.store import get_dataset

router = APIRouter()

@router.get("/datasets/{dataset_id}/eda")
def get_eda(dataset_id: str):
    dataset = get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    result = compute_eda(dataset)
    return result


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
