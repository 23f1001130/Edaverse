from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request
from typing import Optional
from app.services.parser import parse_file
from app.services.store import save_dataset
from app.services.auth import get_request_user_id
from app.services.limiter import limiter

router = APIRouter()

@router.post("/upload")
@limiter.limit("10/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    header_row: Optional[str] = Form(None),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    contents = await file.read()

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    if len(contents) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 100MB)")

    # Coerce header_row to int if provided
    hr = None
    if header_row is not None and str(header_row).strip() != "":
        try:
            hr = int(header_row)
        except (ValueError, TypeError):
            hr = None

    result = parse_file(filename=file.filename, contents=contents, header_row=hr)

    if result.get("success"):
        result = save_dataset(result, owner_id=get_request_user_id(request))

    return result
