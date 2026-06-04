from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ---- Auth Schemas ----

class AdminLogin(BaseModel):
    email: str
    password: str


class AdminOTPSetup(BaseModel):
    otp_code: str


class AdminOTPVerify(BaseModel):
    email: str
    otp_code: str


class AdminResponse(BaseModel):
    id: str
    email: str
    display_name: str
    is_otp_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OTPSetupResponse(BaseModel):
    otp_secret: str
    otp_uri: str
    qr_code: str


class TokenResponse(BaseModel):
    access_token: str
    admin: AdminResponse


# ---- Admin Draw Records ----

class DrawRecordResponse(BaseModel):
    drawn_at: Optional[datetime] = None
    pool_name: str
    pool_code: str
    serial_number: int
    grade_name: Optional[str] = None
    item_name: Optional[str] = None
    single_price: int
    cost: int
    profit: int
    payment_method: Optional[str] = None
    user_id: Optional[str] = None
    order_id: Optional[str] = None
    is_multi_draw: bool = False
    amount: int = 0
