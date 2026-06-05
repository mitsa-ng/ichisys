import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PrizeGrade(Base):
    __tablename__ = "prize_grades"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    pool_id: Mapped[str] = mapped_column(String, ForeignKey("pools.id"), nullable=False)
    grade_name: Mapped[str] = mapped_column(String(50), nullable=False)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)
    item_type: Mapped[str] = mapped_column(String(100), nullable=False)
    initial_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remaining_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    market_price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_url: Mapped[str] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), default=lambda: datetime.utcnow()
    )

    pool = relationship("Pool", back_populates="prize_grades")
    tickets = relationship("Ticket", back_populates="prize_grade")
