from fastapi import APIRouter, HTTPException
from app.services.eda import compute_eda
from app.services.store import get_dataset

router = APIRouter()

@router.get("/datasets/{dataset_id}/eda")
def get_eda(dataset_id: str):
    dataset = get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    result = compute_eda(dataset)
    return result
