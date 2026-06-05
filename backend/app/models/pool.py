import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Pool(Base):
    __tablename__ = "pools"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    banner_image: Mapped[str] = mapped_column(Text, nullable=True)
    single_price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    allow_shipping: Mapped[bool] = mapped_column(Boolean, default=True)
    shipping_fee: Mapped[int] = mapped_column(Integer, default=0)
    free_shipping_threshold: Mapped[int] = mapped_column(Integer, default=0)
    last_one_prize_name: Mapped[str] = mapped_column(String(200), nullable=True)
    last_one_prize_image: Mapped[str] = mapped_column(Text, nullable=True)
    payment_methods: Mapped[str] = mapped_column(String(100), default="onsite,linepay,draw_now")
    status: Mapped[str] = mapped_column(
        String(20), default="draft"
    )
    total_tickets: Mapped[int] = mapped_column(Integer, default=0)
    remaining_tickets: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    prize_grades = relationship("PrizeGrade", back_populates="pool", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="pool", cascade="all, delete-orphan")
