import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request
from typing import Optional
from app.services.parser import parse_upload
import pandas as pd
import threading
from zipfile import BadZipFile
from app.services.store import save_dataset
from app.services.auth import get_request_user_id
from app.services.limiter import limiter

router = APIRouter()
_upload_lock = threading.Lock()


def _max_upload_bytes() -> int:
    try:
        return max(int(os.getenv("MAX_UPLOAD_MB", "100")), 1) * 1024 * 1024
    except (TypeError, ValueError):
        return 100 * 1024 * 1024

@router.post("/upload")
@limiter.limit("10/minute")
def upload_file(
    request: Request,
    file: UploadFile = File(...),
    header_row: Optional[str] = Form(None),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    max_bytes = _max_upload_bytes()
    if size > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large (max {max_bytes // (1024 * 1024)}MB)")

    # Coerce header_row to int if provided
    hr = None
    if header_row is not None and str(header_row).strip() != "":
        try:
            hr = int(header_row)
        except (ValueError, TypeError):
            hr = None

    # One memory-intensive ingestion at a time, without blocking health/config
    # requests on the event loop or queuing unbounded worker jobs.
    if not _upload_lock.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="Another dataset is processing. Please retry shortly.")
    result = None
    temp_path = None
    try:
        result = parse_upload(file.filename, file.file, size, hr)
        temp_path = result.get("_data_path")
        if result.get("success"):
            result = save_dataset(result, owner_id=get_request_user_id(request))
        return result
    except (pd.errors.ParserError, ValueError, UnicodeDecodeError, BadZipFile) as exc:
        raise HTTPException(status_code=400, detail=f"Could not read this dataset: {exc}") from exc
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)
        _upload_lock.release()
