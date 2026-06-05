import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.ticket import Ticket
from app.models.warehouse import VirtualWarehouse
from app.schemas.warehouse import WarehouseItemResponse, ShippingRequest

router = APIRouter(prefix="/api/warehouse", tags=["warehouse"])


@router.get("/{user_id}", response_model=list[WarehouseItemResponse])
async def get_user_warehouse(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VirtualWarehouse)
        .options(
            selectinload(VirtualWarehouse.ticket).selectinload(Ticket.prize_grade),
            selectinload(VirtualWarehouse.ticket).selectinload(Ticket.pool),
        )
        .where(
            VirtualWarehouse.user_id == user_id,
            VirtualWarehouse.status.in_(["unclaimed", "shipping_requested"]),
        )
        .order_by(VirtualWarehouse.created_at.desc())
    )
    items = result.scalars().all()

    return [
        WarehouseItemResponse(
            id=item.id,
            ticket_id=item.ticket_id,
            user_id=item.user_id,
            status=item.status,
            pool_name=item.ticket.pool.name if item.ticket.pool else "",
            grade_name=item.ticket.prize_grade.grade_name if item.ticket.prize_grade else "",
            item_name=item.ticket.prize_grade.item_name if item.ticket.prize_grade else "",
            item_type=item.ticket.prize_grade.item_type if item.ticket.prize_grade else "",
            serial_number=item.ticket.serial_number,
            qr_code_token=item.qr_code_token,
            expires_at=item.expires_at,
            created_at=item.created_at,
        )
        for item in items
    ]


@router.post("/request-shipping")
async def request_shipping(body: ShippingRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VirtualWarehouse).where(
            VirtualWarehouse.id.in_(body.item_ids),
            VirtualWarehouse.status == "unclaimed",
        )
    )
    items = result.scalars().all()

    if len(items) != len(body.item_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some items are not available for shipping",
        )

    for item in items:
        item.status = "shipping_requested"
        item.shipping_name = body.shipping_name
        item.shipping_phone = body.shipping_phone
        item.shipping_address = body.shipping_address

    await db.commit()
    return {"message": "Shipping requested", "count": len(items)}


@router.post("/request-pickup/{user_id}")
async def request_pickup(user_id: str, item_ids: list[str], db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VirtualWarehouse).where(
            VirtualWarehouse.id.in_(item_ids),
            VirtualWarehouse.user_id == user_id,
            VirtualWarehouse.status == "unclaimed",
        )
    )
    items = result.scalars().all()

    if len(items) != len(item_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some items are not available for pickup",
        )

    token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=7)

    for item in items:
        item.qr_code_token = token
        item.status = "unclaimed"

    await db.commit()
    return {
        "message": "Pickup requested",
        "qr_code_token": token,
        "expires_at": expires_at.isoformat(),
    }


@router.post("/verify-qr")
async def verify_qr(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VirtualWarehouse)
        .options(
            selectinload(VirtualWarehouse.ticket).selectinload(Ticket.prize_grade),
        )
        .where(
            VirtualWarehouse.qr_code_token == token,
            VirtualWarehouse.status.in_(["unclaimed", "shipping_requested"]),
        )
    )
    items = result.scalars().all()

    if not items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired QR code")

    return [
        {
            "warehouse_id": item.id,
            "grade_name": item.ticket.prize_grade.grade_name if item.ticket.prize_grade else "",
            "item_name": item.ticket.prize_grade.item_name if item.ticket.prize_grade else "",
            "status": item.status,
        }
        for item in items
    ]


@router.post("/confirm-pickup/{warehouse_id}")
async def confirm_pickup(warehouse_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VirtualWarehouse).where(
            VirtualWarehouse.id == warehouse_id,
            VirtualWarehouse.status == "unclaimed",
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found or already claimed")

    item.status = "picked_up"
    item.claimed_at = datetime.utcnow()
    await db.commit()
    return {"message": "Pickup confirmed"}
