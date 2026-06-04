from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PaymentCreate(BaseModel):
    pool_id: str
    user_id: str
    serial_numbers: list[int]
    method: str


class PaymentResponse(BaseModel):
    id: str
    pool_id: str
    user_id: str
    amount: int
    method: str
    status: str
    serial_numbers: Optional[str] = None
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaymentConfirm(BaseModel):
    payment_id: str


class PaymentListResponse(BaseModel):
    id: str
    pool_id: str
    pool_name: str
    pool_code: str
    user_id: str
    amount: int
    method: str
    status: str
    serial_numbers: Optional[str] = None
    ticket_count: int = 0
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
