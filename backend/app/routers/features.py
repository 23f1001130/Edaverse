from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from app.services.features import suggest_feature_ops, apply_feature_ops, get_feat_csv, _load_df, promote_engineered
from app.services.store import get_dataset
from app.services.parser import build_column_schema
from app.routers.cleaning import _merge_workflow_ids, _refresh_schema_in_store

router = APIRouter()


class FeatureRequest(BaseModel):
    op_ids: list[str]


class PromoteFeatureRequest(BaseModel):
    op_ids: list[str] = []


@router.get("/datasets/{dataset_id}/feature-suggestions")
def get_feature_suggestions(dataset_id: str, target: str | None = Query(default=None)):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = _load_df(dataset_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset data not found")
    # Always build schema live from df — never trust stale cached metadata
    live_schema = build_column_schema(df)
    ignored = dataset.get("workflow", {}).get("applied_feature_op_ids", [])
    return {"suggestions": suggest_feature_ops(df, live_schema, ignored, target)}


@router.post("/datasets/{dataset_id}/engineer")
def engineer_features(dataset_id: str, req: FeatureRequest):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = _load_df(dataset_id)
    live_schema = build_column_schema(df) if df is not None else dataset.get("schema", [])
    result = apply_feature_ops(dataset_id, req.op_ids, live_schema)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/datasets/{dataset_id}/use-engineered")
def use_engineered(dataset_id: str, req: PromoteFeatureRequest | None = None):
    if not get_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    res = promote_engineered(dataset_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    updated = _refresh_schema_in_store(dataset_id, res["df"])
    if req and req.op_ids:
        updated = _merge_workflow_ids(dataset_id, "applied_feature_op_ids", req.op_ids)
    return {"ok": True, "dataset": updated}


@router.get("/datasets/{dataset_id}/download-engineered")
def download_engineered(dataset_id: str):
    csv_bytes = get_feat_csv(dataset_id)
    if csv_bytes is None:
        raise HTTPException(status_code=404, detail="No engineered file — run feature engineering first")
    dataset = get_dataset(dataset_id)
    fname = (dataset.get("filename", "data") if dataset else "data").rsplit(".", 1)[0]
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}_engineered.csv"'},
    )
