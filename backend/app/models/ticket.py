import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pool_id: Mapped[str] = mapped_column(String, ForeignKey("pools.id"), nullable=False)
    prize_grade_id: Mapped[str] = mapped_column(
        String, ForeignKey("prize_grades.id"), nullable=True
    )
    serial_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_drawn: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[str] = mapped_column(String(100), nullable=True)
    drawn_at: Mapped[datetime] = mapped_column(DateTime(), nullable=True)
    order_id: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), default=lambda: datetime.utcnow()
    )

    pool = relationship("Pool", back_populates="tickets")
    prize_grade = relationship("PrizeGrade", back_populates="tickets")
    warehouse_entry = relationship("VirtualWarehouse", back_populates="ticket", uselist=False, cascade="all, delete-orphan")
