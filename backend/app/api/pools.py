from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete as sa_delete, select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.pool import Pool
from app.models.prize_grade import PrizeGrade
from app.models.prize_item import PrizeItem
from app.models.ticket import Ticket
from app.models.warehouse import VirtualWarehouse
from app.schemas.pool import (
    PoolCreate,
    PoolListResponse,
    PoolResponse,
    PoolUpdate,
    PoolUpdateWithGrades,
    PrizeGradeResponse,
    PrizeGradeUpdate,
)
from app.services.auth import generate_grade_code, generate_pool_code
from app.services.events import broadcast
from app.services.shuffle import build_ticket_plan

router = APIRouter(prefix="/api/pools", tags=["pools"])


@router.get("", response_model=list[PoolListResponse])
async def list_pools(
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    grade_count_subq = (
        select(PrizeGrade.pool_id, func.count().label("cnt"))
        .group_by(PrizeGrade.pool_id)
        .subquery()
    )
    query = (
        select(Pool, grade_count_subq.c.cnt)
        .outerjoin(grade_count_subq, Pool.id == grade_count_subq.c.pool_id)
        .order_by(Pool.created_at.desc())
    )
    if status_filter:
        query = query.where(Pool.status == status_filter)
    result = await db.execute(query)
    rows = result.all()

    return [
        PoolListResponse(
            id=p.id,
            code=p.code,
            name=p.name,
            banner_image=p.banner_image,
            single_price=p.single_price,
            status=p.status,
            total_tickets=p.total_tickets,
            remaining_tickets=p.remaining_tickets,
            grade_count=cnt or 0,
            created_at=p.created_at,
        )
        for p, cnt in rows
    ]


@router.post("", response_model=PoolResponse, status_code=status.HTTP_201_CREATED)
async def create_pool(
    body: PoolCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if len(body.prize_grades) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 prize grades are required",
        )

    try:
        pool_code = generate_pool_code()
        stock_total = sum(item.stock for g in body.prize_grades for item in g.prize_items)
        total = body.total_tickets if body.total_tickets is not None else stock_total

        pool = Pool(
            code=pool_code,
            name=body.name,
            banner_image=body.banner_image,
            single_price=body.single_price,
            payment_methods=body.payment_methods,
            allow_shipping=body.allow_shipping,
            shipping_fee=body.shipping_fee,
            free_shipping_threshold=body.free_shipping_threshold,
            status="draft",
            total_tickets=total,
            remaining_tickets=total,
        )
        db.add(pool)
        await db.flush()

        for i, g in enumerate(body.prize_grades):
            grade_stock = sum(item.stock for item in g.prize_items)
            grade = PrizeGrade(
                code=generate_grade_code(),
                pool_id=pool.id,
                grade_name=g.grade_name,
                sort_order=g.sort_order or i,
                remaining_stock=grade_stock,
            )
            db.add(grade)
            await db.flush()

            for item in g.prize_items:
                pi = PrizeItem(
                    prize_grade_id=grade.id,
                    name=item.name,
                    stock=item.stock,
                    remaining_stock=item.stock,
                    category=item.category,
                    cost=item.cost,
                    market_price=item.market_price,
                    image_url=item.image_url,
                    sort_order=item.sort_order,
                )
                db.add(pi)

        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="獎池代碼重複，請重新試一次",
        )

    result = await db.execute(
        select(Pool)
        .options(
            selectinload(Pool.prize_grades).selectinload(PrizeGrade.prize_items)
        )
        .where(Pool.id == pool.id)
    )
    pool = result.scalar_one()
    await broadcast("pool_update", {"pool_id": pool.id, "status": "draft", "name": pool.name})
    return PoolResponse.model_validate(pool)


@router.get("/{pool_id}", response_model=PoolResponse)
async def get_pool(pool_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Pool)
        .options(
            selectinload(Pool.prize_grades).selectinload(PrizeGrade.prize_items)
        )
        .where(Pool.id == pool_id)
    )
    pool = result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    return PoolResponse.model_validate(pool)


@router.patch("/{pool_id}", response_model=PoolResponse)
async def update_pool(
    pool_id: str,
    body: PoolUpdateWithGrades,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Pool)
        .options(
            selectinload(Pool.prize_grades).selectinload(PrizeGrade.prize_items)
        )
        .where(Pool.id == pool_id)
    )
    pool = result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")

    update_data = body.model_dump(exclude_unset=True)
    prize_grades_data = update_data.pop("prize_grades", None)
    explicit_total = update_data.pop("total_tickets", None)

    if prize_grades_data is not None and pool.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only edit prize grades on draft pools",
        )

    for key, value in update_data.items():
        setattr(pool, key, value)

    if prize_grades_data is not None:
        total = 0
        new_grades = []
        for i, g in enumerate(prize_grades_data):
            items_data = g.get("prize_items", [])
            grade = PrizeGrade(
                code=generate_grade_code(),
                pool_id=pool.id,
                grade_name=g["grade_name"],
                sort_order=g.get("sort_order") if g.get("sort_order") is not None else i,
            )
            for item in items_data:
                pi = PrizeItem(
                    name=item["name"],
                    stock=item["stock"],
                    remaining_stock=item["stock"],
                    category=item.get("category", "卡牌"),
                    cost=item.get("cost", 0),
                    market_price=item.get("market_price", 0),
                    image_url=item.get("image_url"),
                    sort_order=item.get("sort_order", 0),
                )
                grade.prize_items.append(pi)
                total += item["stock"]
            grade.remaining_stock = sum(item["stock"] for item in items_data)
            new_grades.append(grade)

        pool.prize_grades = new_grades
        new_total = explicit_total if explicit_total is not None else total
        delta = new_total - pool.total_tickets
        pool.total_tickets = new_total
        if pool.status == "draft":
            pool.remaining_tickets = new_total
        else:
            pool.remaining_tickets = max(0, pool.remaining_tickets + delta)
    elif explicit_total is not None:
        delta = explicit_total - pool.total_tickets
        pool.total_tickets = explicit_total
        if pool.status == "draft":
            pool.remaining_tickets = explicit_total
        else:
            pool.remaining_tickets = max(0, pool.remaining_tickets + delta)

    await db.commit()
    await db.refresh(pool)
    await broadcast("pool_update", {"pool_id": pool.id, "status": pool.status, "remaining_tickets": pool.remaining_tickets})
    return PoolResponse.model_validate(pool)


@router.patch("/{pool_id}/grades", response_model=PoolResponse)
async def update_pool_grades(
    pool_id: str,
    body: list[PrizeGradeUpdate],
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Pool)
        .options(
            selectinload(Pool.prize_grades).selectinload(PrizeGrade.prize_items)
        )
        .where(Pool.id == pool_id)
    )
    pool = result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")

    existing_map = {g.id: g for g in pool.prize_grades}

    for update in body:
        grade = existing_map.get(update.id)
        if not grade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prize grade {update.id} not found",
            )
        if update.grade_name is not None:
            grade.grade_name = update.grade_name
        if update.sort_order is not None:
            grade.sort_order = update.sort_order

    await db.commit()
    await db.refresh(pool)
    await broadcast("pool_update", {"pool_id": pool.id, "status": pool.status, "remaining_tickets": pool.remaining_tickets})
    return PoolResponse.model_validate(pool)


@router.delete("/{pool_id}")
async def delete_pool(
    pool_id: str,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Pool).where(Pool.id == pool_id))
    pool = result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")

    await db.delete(pool)
    await db.commit()
    await broadcast("pool_deleted", {"pool_id": pool_id})
    return {"message": "Pool deleted"}


@router.post("/{pool_id}/shuffle")
async def shuffle_pool(
    pool_id: str,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Pool)
        .options(
            selectinload(Pool.prize_grades).selectinload(PrizeGrade.prize_items)
        )
        .where(Pool.id == pool_id)
    )
    pool = result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")

    await db.execute(
        sa_delete(VirtualWarehouse).where(
            VirtualWarehouse.ticket_id.in_(
                select(Ticket.id).where(Ticket.pool_id == pool_id)
            )
        )
    )
    await db.execute(
        sa_delete(Ticket).where(Ticket.pool_id == pool_id)
    )

    grades = pool.prize_grades
    total = pool.total_tickets
    ticket_plan = build_ticket_plan(pool, grades, total)

    new_tickets = [Ticket(**t) for t in ticket_plan]
    for t in new_tickets:
        db.add(t)

    pool.total_tickets = total
    pool.remaining_tickets = total
    pool.status = "published"

    await db.commit()
    await broadcast("pool_update", {"pool_id": pool.id, "status": "published", "total_tickets": total, "remaining_tickets": total})
    return {"message": "Pool shuffled and published", "total_tickets": total}


@router.post("/{pool_id}/publish")
async def publish_pool(
    pool_id: str,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Pool)
        .options(
            selectinload(Pool.prize_grades).selectinload(PrizeGrade.prize_items)
        )
        .where(Pool.id == pool_id)
    )
    pool = result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")

    if pool.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pool is not in draft status")

    grades = pool.prize_grades
    total = pool.total_tickets
    ticket_plan = build_ticket_plan(pool, grades, total)

    new_tickets = [Ticket(**t) for t in ticket_plan]
    for t in new_tickets:
        db.add(t)

    pool.total_tickets = total
    pool.remaining_tickets = total
    pool.status = "published"

    await db.commit()
    await broadcast("pool_update", {"pool_id": pool.id, "status": "published", "total_tickets": total, "remaining_tickets": total})
    return {"message": "Pool published", "total_tickets": total}
