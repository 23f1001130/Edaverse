from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from app.services.cleaning import (
    suggest_fixes, clean_dataset, get_clean_csv, _load_df,
    promote_cleaned, restore_original, has_original_backup,
)
from app.services.store import get_dataset, _meta_path
from app.services.parser import build_column_schema
import json

router = APIRouter()


class CleanRequest(BaseModel):
    fix_ids: list[str]


def _refresh_schema_in_store(dataset_id: str, df):
    """Recompute schema/shape/sample from a dataframe and persist to the metadata json."""
    path = _meta_path(dataset_id)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


@router.get("/datasets/{dataset_id}/suggestions")
def get_suggestions(dataset_id: str):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = _load_df(dataset_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset data not found")
    return {
        "suggestions": suggest_fixes(df, dataset.get("schema", [])),
        "has_backup": has_original_backup(dataset_id),
    }


@router.post("/datasets/{dataset_id}/clean")
def clean(dataset_id: str, req: CleanRequest):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    result = clean_dataset(dataset_id, req.fix_ids, dataset.get("schema", []))
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/datasets/{dataset_id}/use-cleaned")
def use_cleaned(dataset_id: str):
    if not get_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    res = promote_cleaned(dataset_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    updated = _refresh_schema_in_store(dataset_id, res["df"])
    return {"ok": True, "dataset": updated}


@router.post("/datasets/{dataset_id}/restore-original")
def restore(dataset_id: str):
    if not get_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    res = restore_original(dataset_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    updated = _refresh_schema_in_store(dataset_id, res["df"])
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
