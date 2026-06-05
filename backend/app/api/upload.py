import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from app.config import settings
from app.dependencies import get_current_admin
from app.models.admin import Admin

router = APIRouter(prefix="/api/upload", tags=["upload"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_SIZE = 10 * 1024 * 1024


@router.post("")
async def upload_image(
    file: UploadFile = File(...),
    admin: Admin = Depends(get_current_admin),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支援的檔案格式：{file.content_type}，僅支援 JPEG、PNG、GIF、WebP",
        )

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="檔案過大，最大 10MB",
        )

    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp"}.get(file.content_type, ".bin")
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(settings.upload_dir, filename)
    os.makedirs(settings.upload_dir, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(contents)

    return {"url": f"/api/files/{filename}"}
