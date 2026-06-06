import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PrizeItem(Base):
    __tablename__ = "prize_items"

    __table_args__ = (
        Index("ix_prize_items_grade_id", "prize_grade_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    prize_grade_id: Mapped[str] = mapped_column(String, ForeignKey("prize_grades.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remaining_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="卡牌")
    cost: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    market_price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_url: Mapped[str] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    prize_grade = relationship("PrizeGrade", back_populates="prize_items")
    tickets = relationship("Ticket", back_populates="prize_item")
