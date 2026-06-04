from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin import Admin
from app.schemas.admin import AdminResponse
from app.schemas.setup import SetupAdminRequest
from app.services.auth import hash_password

router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.get("/status")
async def setup_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Admin).limit(1))
    admin = result.scalar_one_or_none()
    return {"needs_setup": admin is None}


@router.post("/admin", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
async def setup_admin(body: SetupAdminRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Admin).limit(1))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin already exists")

    admin = Admin(
        email=body.email,
        hashed_password=hash_password(body.password),
        display_name=body.display_name,
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return AdminResponse.model_validate(admin)
