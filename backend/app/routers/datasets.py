from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import Response
from app.services.auth import get_request_user_id
from app.services.store import list_datasets, get_dataset, delete_dataset, cleanup_expired_datasets
from app.services.notebook import notebook_bytes

router = APIRouter()

@router.get("/datasets")
def get_datasets(
    request: Request,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return list_datasets(get_request_user_id(request), limit=limit, offset=offset)

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


@router.post("/datasets/cleanup-demo-duplicates")
def cleanup_demo_duplicates():
    """Remove all anonymous demo datasets (no owner_id) that were created before
    per-user scoping was enforced. Safe to call multiple times."""
    from app.services.store import list_datasets, delete_dataset
    anonymous = list_datasets(None)
    deleted = 0
    for ds in anonymous:
        if ds.get("filename") == "customer_churn_demo.csv" and not ds.get("owner_id"):
            if delete_dataset(ds["id"], None):
                deleted += 1
    return {"deleted": deleted}


@router.get("/datasets/{dataset_id}/notebook")
def export_notebook(dataset_id: str, request: Request):
    data = get_dataset(dataset_id, get_request_user_id(request))
    if data is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    fname = (data.get("filename", "data").rsplit(".", 1)[0] or "data") + "_workflow.ipynb"
    return Response(
        content=notebook_bytes(data),
        media_type="application/x-ipynb+json",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
