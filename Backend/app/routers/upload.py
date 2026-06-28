from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_role
from ..minio_client import public_url, upload_bytes
from ..models import User
from ..response import ok

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("")
def upload_material_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("owner", "admin", "labeler", "reviewer")),
):
    content = file.file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 400, "message": "empty file", "data": None},
        )
    filename = file.filename or "upload"
    content_type = file.content_type or "application/octet-stream"
    object_name = upload_bytes("annotation", content, filename, content_type)
    return ok(
        {
            "url": public_url("annotation", object_name),
            "object_name": object_name,
            "filename": filename,
            "size": len(content),
        }
    )
