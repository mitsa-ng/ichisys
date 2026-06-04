from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WarehouseItemResponse(BaseModel):
    id: str
    ticket_id: str
    user_id: str
    status: str
    pool_name: str
    grade_name: str
    item_name: str
    item_type: str
    serial_number: int
    qr_code_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ShippingRequest(BaseModel):
    item_ids: list[str]
    shipping_name: str
    shipping_phone: str
    shipping_address: str


class PickupRequest(BaseModel):
    item_ids: list[str]
