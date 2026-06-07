from datetime import datetime

from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    sort_order: int = 0


class CategoryResponse(BaseModel):
    id: str
    name: str
    sort_order: int
    created_at: datetime

    class Config:
        from_attributes = True
