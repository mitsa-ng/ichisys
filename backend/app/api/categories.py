from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryResponse

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.sort_order, Category.name))
    return [CategoryResponse.model_validate(c) for c in result.scalars().all()]


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Category).where(Category.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Category already exists")
    cat = Category(name=body.name, sort_order=body.sort_order)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return CategoryResponse.model_validate(cat)


@router.delete("/{category_id}")
async def delete_category(
    category_id: str,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(cat)
    await db.commit()
    return {"message": "Category deleted"}
