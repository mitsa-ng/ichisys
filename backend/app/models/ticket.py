import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    __table_args__ = (
        Index("ix_tickets_pool_id", "pool_id"),
        Index("ix_tickets_pool_id_is_drawn", "pool_id", "is_drawn"),
        Index("ix_tickets_pool_id_serial_number", "pool_id", "serial_number"),
        Index("ix_tickets_user_id", "user_id"),
        Index("ix_tickets_is_drawn", "is_drawn"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pool_id: Mapped[str] = mapped_column(String, ForeignKey("pools.id"), nullable=False)
    prize_grade_id: Mapped[str] = mapped_column(
        String, ForeignKey("prize_grades.id"), nullable=True
    )
    prize_item_id: Mapped[str] = mapped_column(
        String, ForeignKey("prize_items.id"), nullable=True
    )
    serial_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_drawn: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[str] = mapped_column(String(100), nullable=True)
    drawn_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    order_id: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    pool = relationship("Pool", back_populates="tickets")
    prize_grade = relationship("PrizeGrade", back_populates="tickets")
    prize_item = relationship("PrizeItem", back_populates="tickets")
    warehouse_entry = relationship("VirtualWarehouse", back_populates="ticket", uselist=False, cascade="all, delete-orphan")
