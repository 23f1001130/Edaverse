from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from app.services.cleaning import (
    suggest_fixes, clean_dataset, get_clean_csv, _load_df,
    promote_cleaned, restore_original, has_original_backup,
)
from app.services.store import get_dataset, save_dataset_record
from app.services.parser import build_column_schema

router = APIRouter()


class CleanRequest(BaseModel):
    fix_ids: list[str]


class PromoteCleanRequest(BaseModel):
    fix_ids: list[str] = []


def _merge_workflow_ids(dataset_id: str, key: str, ids: list[str]) -> dict | None:
    data = get_dataset(dataset_id)
    if not data:
        return None
    workflow = data.setdefault("workflow", {})
    current = set(workflow.get(key, []))
    current.update(ids or [])
    workflow[key] = sorted(current)
    return save_dataset_record(data)


def _clear_workflow_state(dataset_id: str) -> dict | None:
    data = get_dataset(dataset_id)
    if not data:
        return None
    data.pop("workflow", None)
    return save_dataset_record(data)


def _refresh_schema_in_store(dataset_id: str, df):
    """Recompute schema/shape/sample from a dataframe and persist to the metadata json."""
    data = get_dataset(dataset_id)
    if not data:
        return None

    schema = build_column_schema(df)
    import pandas as pd
    sample = df.head(5).copy()
    for col in sample.columns:
        if pd.api.types.is_datetime64_any_dtype(sample[col]):
            sample[col] = sample[col].astype(str)
        elif pd.api.types.is_float_dtype(sample[col]):
            sample[col] = sample[col].replace([float('inf'), float('-inf')], None)
    rows = sample.where(pd.notna(sample), None).to_dict(orient="records")
    def san(v):
        if isinstance(v, float) and (v != v or v in (float('inf'), float('-inf'))):
            return None
        return v
    rows = [{k: san(v) for k, v in r.items()} for r in rows]

    data["schema"] = schema
    data["shape"] = {"rows": len(df), "columns": len(df.columns)}
    data["sample_rows"] = rows
    return save_dataset_record(data)


@router.get("/datasets/{dataset_id}/suggestions")
def get_suggestions(dataset_id: str):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = _load_df(dataset_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset data not found")
    # Rebuild schema live from the actual df so null_pct reflects the current
    # file, not the cached metadata (which goes stale after promote/restore).
    live_schema = build_column_schema(df)
    ignored = dataset.get("workflow", {}).get("applied_cleaning_fix_ids", [])
    return {
        "suggestions": suggest_fixes(df, live_schema, ignored),
        "has_backup": has_original_backup(dataset_id),
    }


@router.post("/datasets/{dataset_id}/clean")
def clean(dataset_id: str, req: CleanRequest):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = _load_df(dataset_id)
    live_schema = build_column_schema(df) if df is not None else dataset.get("schema", [])
    result = clean_dataset(dataset_id, req.fix_ids, live_schema)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/datasets/{dataset_id}/use-cleaned")
def use_cleaned(dataset_id: str, req: PromoteCleanRequest | None = None):
    if not get_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    res = promote_cleaned(dataset_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    updated = _refresh_schema_in_store(dataset_id, res["df"])
    if req and req.fix_ids:
        updated = _merge_workflow_ids(dataset_id, "applied_cleaning_fix_ids", req.fix_ids)
    return {"ok": True, "dataset": updated}


@router.post("/datasets/{dataset_id}/restore-original")
def restore(dataset_id: str):
    if not get_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    res = restore_original(dataset_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    updated = _refresh_schema_in_store(dataset_id, res["df"])
    updated = _clear_workflow_state(dataset_id) or updated
    return {"ok": True, "dataset": updated}


@router.get("/datasets/{dataset_id}/download")
def download_clean(dataset_id: str):
    csv_bytes = get_clean_csv(dataset_id)
    if csv_bytes is None:
        raise HTTPException(status_code=404, detail="No cleaned file — run cleaning first")
    dataset = get_dataset(dataset_id)
    fname = (dataset.get("filename", "data") if dataset else "data").rsplit(".", 1)[0]
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}_cleaned.csv"'},
    )
