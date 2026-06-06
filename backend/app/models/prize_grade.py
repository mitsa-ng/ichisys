import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PrizeGrade(Base):
    __tablename__ = "prize_grades"

    __table_args__ = (
        Index("ix_prize_grades_pool_id", "pool_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    pool_id: Mapped[str] = mapped_column(String, ForeignKey("pools.id"), nullable=False)
    grade_name: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    remaining_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    pool = relationship("Pool", back_populates="prize_grades")
    prize_items = relationship("PrizeItem", back_populates="prize_grade", cascade="all, delete-orphan", order_by="PrizeItem.sort_order")
    tickets = relationship("Ticket", back_populates="prize_grade")
