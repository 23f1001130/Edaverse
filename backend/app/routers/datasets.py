from fastapi import APIRouter, HTTPException
from app.services.store import list_datasets, get_dataset, delete_dataset

router = APIRouter()

@router.get("/datasets")
def get_datasets():
    return list_datasets()

@router.get("/datasets/{dataset_id}")
def get_dataset_by_id(dataset_id: str):
    data = get_dataset(dataset_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return data

@router.delete("/datasets/{dataset_id}")
def remove_dataset(dataset_id: str):
    deleted = delete_dataset(dataset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"deleted": True, "id": dataset_id}
