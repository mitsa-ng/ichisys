import csv
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.payment import Payment
from app.models.pool import Pool
from app.models.ticket import Ticket
from app.models.prize_grade import PrizeGrade
from app.models.prize_item import PrizeItem
from app.schemas.admin import AdminCreate, AdminListResponse, AdminUpdate, DrawRecordResponse
from app.services.auth import hash_password

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/accounts", response_model=list[AdminListResponse])
async def list_admins(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Admin).order_by(Admin.created_at.desc()))
    admins = result.scalars().all()
    return [AdminListResponse.model_validate(a) for a in admins]


@router.post("/accounts", response_model=AdminListResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    body: AdminCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(Admin).where(Admin.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already exists")
    new_admin = Admin(
        email=body.email,
        hashed_password=hash_password(body.password),
        display_name=body.display_name,
    )
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)
    return AdminListResponse.model_validate(new_admin)


@router.patch("/accounts/{admin_id}", response_model=AdminListResponse)
async def update_admin(
    admin_id: str,
    body: AdminUpdate,
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Admin not found")
    if body.email is not None:
        existing = await db.execute(select(Admin).where(Admin.email == body.email, Admin.id != admin_id))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already exists")
        target.email = body.email
    if body.display_name is not None:
        target.display_name = body.display_name
    if body.password is not None:
        target.hashed_password = hash_password(body.password)
    await db.commit()
    await db.refresh(target)
    return AdminListResponse.model_validate(target)


@router.delete("/accounts/{admin_id}")
async def delete_admin(
    admin_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if current_admin.id == admin_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Admin not found")
    await db.delete(target)
    await db.commit()
    return {"message": "Admin deleted"}


async def _fetch_draws(
    pool_id: Optional[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    db: AsyncSession,
) -> list[DrawRecordResponse]:
    query = (
        select(Ticket)
        .options(
            selectinload(Ticket.prize_grade),
            selectinload(Ticket.prize_item),
        )
        .where(Ticket.is_drawn == True)
        .order_by(Ticket.drawn_at.desc())
    )

    if pool_id:
        query = query.where(Ticket.pool_id == pool_id)
    if date_from:
        query = query.where(Ticket.drawn_at >= date_from)
    if date_to:
        query = query.where(Ticket.drawn_at <= date_to)

    ticket_result = await db.execute(query)
    tickets = ticket_result.scalars().all()

    pool_ids = list(set(t.pool_id for t in tickets))
    pools_map = {}
    if pool_ids:
        pool_result = await db.execute(
            select(Pool).where(Pool.id.in_(pool_ids))
        )
        for p in pool_result.scalars().all():
            pools_map[p.id] = p

    order_ids = [t.order_id for t in tickets if t.order_id]
    order_counts = {}
    if order_ids:
        count_result = await db.execute(
            select(Ticket.order_id, func.count(Ticket.id).label("cnt"))
            .where(Ticket.order_id.in_(order_ids))
            .group_by(Ticket.order_id)
        )
        for row in count_result:
            order_counts[row.order_id] = row.cnt

    payment_map = {}
    if order_ids:
        pay_result = await db.execute(
            select(Payment).where(Payment.id.in_(order_ids))
        )
        for p in pay_result.scalars().all():
            payment_map[p.id] = p

    records = []
    for t in tickets:
        pool = pools_map.get(t.pool_id)
        payment = payment_map.get(t.order_id) if t.order_id else None
        grade = t.prize_grade
        prize_item = t.prize_item
        cost = prize_item.cost if prize_item else 0
        single_price = pool.single_price if pool else 0
        order_count = order_counts.get(t.order_id, 1) if t.order_id else 1
        is_multi = order_count > 1

        records.append(DrawRecordResponse(
            drawn_at=t.drawn_at,
            pool_name=pool.name if pool else "",
            pool_code=pool.code if pool else "",
            serial_number=t.serial_number,
            grade_name=grade.grade_name if grade else None,
            item_name=prize_item.name if prize_item else None,
            single_price=single_price,
            cost=cost,
            profit=single_price - cost,
            payment_method=payment.method if payment else None,
            user_id=t.user_id,
            order_id=t.order_id,
            is_multi_draw=is_multi,
            amount=payment.amount if payment else single_price,
        ))

    return records


@router.get("/draws", response_model=list[DrawRecordResponse])
async def get_draw_records(
    pool_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await _fetch_draws(pool_id, date_from, date_to, db)


@router.get("/draws/export")
async def export_draws_csv(
    pool_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    records = await _fetch_draws(pool_id, date_from, date_to, db)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "抽獎時間", "獎池代碼", "獎池名稱", "序號", "獎項等級",
        "獎品名稱", "售價", "成本", "利潤", "付款方式",
        "同筆訂單金額", "多抽訂單",
    ])
    for r in records:
        def fmt(d):
            return d.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S") if d else ""
        writer.writerow([
            fmt(r.drawn_at),
            r.pool_code,
            r.pool_name,
            r.serial_number,
            r.grade_name or "",
            r.item_name or "",
            r.single_price,
            r.cost,
            r.profit,
            {"onsite": "現場", "linepay": "LinePay"}.get(r.payment_method, r.payment_method or ""),
            r.amount,
            "是" if r.is_multi_draw else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=draw_records.csv"},
    )
