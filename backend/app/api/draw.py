from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.payment import Payment
from app.models.pool import Pool
from app.models.prize_grade import PrizeGrade
from app.models.prize_item import PrizeItem
from app.models.ticket import Ticket
from app.models.warehouse import VirtualWarehouse
from app.schemas.ticket import DrawRequest, DrawResponse, DrawResult, TicketGridResponse
from app.services.events import broadcast

router = APIRouter(prefix="/api/pools", tags=["draw"])


@router.get("/{pool_id}/tickets", response_model=list[TicketGridResponse])
async def get_pool_tickets(pool_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Pool).options(selectinload(Pool.prize_grades)).where(Pool.id == pool_id)
    )
    pool = result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")

    ticket_result = await db.execute(
        select(Ticket).options(
            selectinload(Ticket.prize_grade),
            selectinload(Ticket.prize_item),
        ).where(
            Ticket.pool_id == pool_id
        ).order_by(Ticket.serial_number)
    )
    tickets = ticket_result.scalars().all()

    return [
        TicketGridResponse(
            serial_number=t.serial_number,
            is_drawn=t.is_drawn,
            prize_grade_name=t.prize_grade.grade_name if t.is_drawn and t.prize_grade else None,
            drawn_at=t.drawn_at,
        )
        for t in tickets
    ]


@router.post("/{pool_id}/draw", response_model=DrawResponse)
async def draw_tickets(pool_id: str, body: DrawRequest, db: AsyncSession = Depends(get_db)):
    payment_result = await db.execute(select(Payment).where(Payment.id == body.payment_id).with_for_update())
    payment = payment_result.scalar_one_or_none()
    if not payment or payment.status != "confirmed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment not confirmed")
    if payment.pool_id != pool_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment does not match pool")

    result = await db.execute(
        select(Pool).options(selectinload(Pool.prize_grades)).where(Pool.id == pool_id).with_for_update()
    )
    pool = result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")

    if pool.status != "published":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pool is not available")

    if pool.remaining_tickets < len(body.serial_numbers):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough tickets remaining")

    ticket_result = await db.execute(
        select(Ticket).options(
            selectinload(Ticket.prize_grade),
            selectinload(Ticket.prize_item),
        ).where(
            Ticket.pool_id == pool_id,
            Ticket.serial_number.in_(body.serial_numbers),
            Ticket.is_drawn == False,
        ).with_for_update()
    )
    tickets = ticket_result.scalars().all()

    if len(tickets) != len(body.serial_numbers):
        drawn_numbers = [t.serial_number for t in tickets]
        missing = set(body.serial_numbers) - set(drawn_numbers)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tickets already drawn: {missing}",
        )

    results = []
    now = datetime.now(timezone.utc)

    grade_ids = list({t.prize_grade_id for t in tickets if t.prize_grade_id})
    grades_map = {}
    if grade_ids:
        grade_result = await db.execute(
            select(PrizeGrade).where(PrizeGrade.id.in_(grade_ids)).with_for_update()
        )
        grades_map = {g.id: g for g in grade_result.scalars().all()}

    item_ids = list({t.prize_item_id for t in tickets if t.prize_item_id})
    items_map = {}
    if item_ids:
        item_result = await db.execute(
            select(PrizeItem).where(PrizeItem.id.in_(item_ids)).with_for_update()
        )
        items_map = {i.id: i for i in item_result.scalars().all()}

    for ticket in tickets:
        ticket.is_drawn = True
        ticket.user_id = body.user_id
        ticket.drawn_at = now
        ticket.order_id = payment.id

        prize_item = items_map.get(ticket.prize_item_id) if ticket.prize_item_id else None
        if prize_item:
            prize_item.remaining_stock = max(0, prize_item.remaining_stock - 1)
            grade = grades_map.get(ticket.prize_grade_id) if ticket.prize_grade_id else None
            if grade:
                grade.remaining_stock = max(0, grade.remaining_stock - 1)

        warehouse = VirtualWarehouse(
            ticket_id=ticket.id,
            user_id=body.user_id,
            status="unclaimed",
        )
        db.add(warehouse)

        results.append(DrawResult(
            serial_number=ticket.serial_number,
            prize_grade_name=grade.grade_name if grade else "",
            item_name=prize_item.name if prize_item else "",
            item_type=prize_item.category if prize_item else "",
        ))

    pool.remaining_tickets = max(0, pool.remaining_tickets - len(tickets))

    if pool.remaining_tickets == 0:
        pool.status = "sold_out"

    payment.status = "consumed"
    await db.commit()

    await broadcast("pool_update", {
        "pool_id": pool.id,
        "remaining_tickets": pool.remaining_tickets,
        "status": pool.status,
    })
    await broadcast("draw_result", {
        "pool_id": pool.id,
        "results": [r.model_dump() for r in results],
    })

    return DrawResponse(results=results)
