import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VirtualWarehouse(Base):
    __tablename__ = "virtual_warehouses"

    __table_args__ = (
        Index("ix_virtual_warehouses_user_id", "user_id"),
        Index("ix_virtual_warehouses_status", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id: Mapped[str] = mapped_column(
        String, ForeignKey("tickets.id"), unique=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="unclaimed"
    )
    shipping_name: Mapped[str] = mapped_column(String(200), nullable=True)
    shipping_phone: Mapped[str] = mapped_column(String(20), nullable=True)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=True)
    shipping_tracking: Mapped[str] = mapped_column(String(200), nullable=True)
    qr_code_token: Mapped[str] = mapped_column(String(100), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    ticket = relationship("Ticket", back_populates="warehouse_entry")
