import io
import uuid

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from app.config import settings
from app.dependencies import get_current_admin
from app.models.admin import Admin

router = APIRouter(prefix="/api/upload", tags=["upload"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_SIZE = 10 * 1024 * 1024

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
)


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

    public_id = f"ichisys/{uuid.uuid4().hex}"

    try:
        result = cloudinary.uploader.upload(
            io.BytesIO(contents),
            public_id=public_id,
            overwrite=True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上傳失敗：{str(e)}",
        )

    return {"url": result["secure_url"]}
