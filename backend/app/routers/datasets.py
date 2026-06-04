from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from app.services.auth import get_request_user_id
from app.services.store import list_datasets, get_dataset, delete_dataset, cleanup_expired_datasets
from app.services.notebook import notebook_bytes

router = APIRouter()

@router.get("/datasets")
def get_datasets(request: Request):
    return list_datasets(get_request_user_id(request))

@router.get("/datasets/{dataset_id}")
def get_dataset_by_id(dataset_id: str, request: Request):
    data = get_dataset(dataset_id, get_request_user_id(request))
    if data is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return data

@router.delete("/datasets/{dataset_id}")
def remove_dataset(dataset_id: str, request: Request):
    deleted = delete_dataset(dataset_id, get_request_user_id(request))
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"deleted": True, "id": dataset_id}


@router.post("/datasets/cleanup-expired")
def cleanup_expired():
    return {"deleted": cleanup_expired_datasets()}


@router.get("/datasets/{dataset_id}/notebook")
def export_notebook(dataset_id: str):
    data = get_dataset(dataset_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    fname = (data.get("filename", "data").rsplit(".", 1)[0] or "data") + "_workflow.ipynb"
    return Response(
        content=notebook_bytes(data),
        media_type="application/x-ipynb+json",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
