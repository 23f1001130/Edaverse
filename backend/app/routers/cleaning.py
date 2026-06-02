from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from app.services.cleaning import suggest_fixes, clean_dataset, get_clean_csv, _load_df
from app.services.store import get_dataset

router = APIRouter()


class CleanRequest(BaseModel):
    fix_ids: list[str]


@router.get("/datasets/{dataset_id}/suggestions")
def get_suggestions(dataset_id: str):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = _load_df(dataset_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset data not found")
    return {"suggestions": suggest_fixes(df, dataset.get("schema", []))}


@router.post("/datasets/{dataset_id}/clean")
def clean(dataset_id: str, req: CleanRequest):
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    result = clean_dataset(dataset_id, req.fix_ids, dataset.get("schema", []))
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


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
