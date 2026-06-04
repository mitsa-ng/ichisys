from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TicketGridResponse(BaseModel):
    serial_number: int
    is_drawn: bool
    prize_grade_name: Optional[str] = None
    drawn_at: Optional[datetime] = None


class DrawResult(BaseModel):
    serial_number: int
    prize_grade_name: str
    item_name: str
    item_type: str


class DrawRequest(BaseModel):
    user_id: str
    serial_numbers: list[int]
    payment_id: str


class DrawResponse(BaseModel):
    results: list[DrawResult]
