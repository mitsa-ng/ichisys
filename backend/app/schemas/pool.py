from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class PrizeGradeCreate(BaseModel):
    grade_name: str
    item_name: str
    item_type: str
    initial_stock: int
    cost: int = 0
    market_price: int = 0
    image_url: Optional[str] = None
    sort_order: int = 0

    @field_validator("grade_name")
    @classmethod
    def grade_name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("獎項等級不得為空")
        return v.strip()

    @field_validator("item_name")
    @classmethod
    def item_name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("獎品名稱不得為空")
        return v.strip()

    @field_validator("initial_stock")
    @classmethod
    def stock_must_be_positive(cls, v):
        if v < 1:
            raise ValueError("獎品庫存必須大於 0")
        return v


class PoolCreate(BaseModel):
    name: str
    banner_image: Optional[str] = None
    single_price: int
    allow_shipping: bool = True
    shipping_fee: int = 0
    free_shipping_threshold: int = 0
    last_one_prize_name: Optional[str] = None
    last_one_prize_image: Optional[str] = None
    payment_methods: str = "onsite,linepay,draw_now"
    prize_grades: list[PrizeGradeCreate]

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("獎池名稱不得為空")
        return v.strip()

    @field_validator("single_price")
    @classmethod
    def price_must_be_positive(cls, v):
        if v < 1:
            raise ValueError("單抽售價必須大於 0")
        return v

    @field_validator("payment_methods")
    @classmethod
    def payment_methods_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("至少需要選擇一種付款方式")
        return v


class PrizeGradeUpdate(BaseModel):
    id: str
    grade_name: Optional[str] = None
    item_name: Optional[str] = None
    item_type: Optional[str] = None
    image_url: Optional[str] = None
    cost: Optional[int] = None
    market_price: Optional[int] = None
    sort_order: Optional[int] = None


class PoolUpdate(BaseModel):
    name: Optional[str] = None
    banner_image: Optional[str] = None
    single_price: Optional[int] = None
    allow_shipping: Optional[bool] = None
    shipping_fee: Optional[int] = None
    free_shipping_threshold: Optional[int] = None
    last_one_prize_name: Optional[str] = None
    last_one_prize_image: Optional[str] = None
    status: Optional[str] = None


class PoolUpdateWithGrades(BaseModel):
    name: Optional[str] = None
    banner_image: Optional[str] = None
    single_price: Optional[int] = None
    allow_shipping: Optional[bool] = None
    shipping_fee: Optional[int] = None
    free_shipping_threshold: Optional[int] = None
    last_one_prize_name: Optional[str] = None
    last_one_prize_image: Optional[str] = None
    payment_methods: Optional[str] = None
    prize_grades: Optional[list[PrizeGradeCreate]] = None


class PrizeGradeResponse(BaseModel):
    id: str
    code: str
    pool_id: str
    grade_name: str
    item_name: str
    item_type: str
    initial_stock: int
    remaining_stock: int
    cost: int
    market_price: int
    image_url: Optional[str] = None
    sort_order: int

    class Config:
        from_attributes = True


class PoolResponse(BaseModel):
    id: str
    code: str
    name: str
    banner_image: Optional[str] = None
    single_price: int
    allow_shipping: bool
    shipping_fee: int
    free_shipping_threshold: int
    last_one_prize_name: Optional[str] = None
    last_one_prize_image: Optional[str] = None
    payment_methods: str = "onsite,linepay,draw_now"
    status: str
    total_tickets: int
    remaining_tickets: int
    prize_grades: list[PrizeGradeResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PoolListResponse(BaseModel):
    id: str
    code: str
    name: str
    banner_image: Optional[str] = None
    single_price: int
    status: str
    total_tickets: int
    remaining_tickets: int
    grade_count: int
    created_at: datetime
