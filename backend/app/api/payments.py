import io
from datetime import datetime, timezone

import qrcode
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.admin import Admin
from app.models.payment import Payment
from app.models.pool import Pool
from app.schemas.payment import PaymentCreate, PaymentListResponse, PaymentResponse
from app.services.auth import decode_access_token
from app.services.events import broadcast

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    body: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None),
):
    if body.method == "linepay":
        if not authorization:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        token = authorization.replace("Bearer ", "")
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        admin_result = await db.execute(select(Admin).where(Admin.id == payload.get("sub")))
        admin = admin_result.scalar_one_or_none()
        if not admin or not admin.is_otp_enabled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin 2FA authentication required")

    result = await db.execute(select(Pool).where(Pool.id == body.pool_id))
    pool = result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")

    if body.method not in pool.payment_methods.split(","):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment method")

    amount = pool.single_price * len(body.serial_numbers)
    serial_str = ",".join(str(n) for n in body.serial_numbers)

    payment = Payment(
        pool_id=body.pool_id,
        user_id=body.user_id,
        amount=amount,
        method=body.method,
        status="pending",
        serial_numbers=serial_str,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    if body.method == "draw_now":
        payment.status = "confirmed"
        payment.confirmed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(payment)
        await broadcast("payment_confirmed", {
            "payment_id": payment.id,
            "pool_id": payment.pool_id,
            "user_id": payment.user_id,
        })
    else:
        await broadcast("payment_created", {
            "payment_id": payment.id,
            "pool_id": payment.pool_id,
            "user_id": payment.user_id,
        })

    return PaymentResponse.model_validate(payment)


@router.post("/{payment_id}/confirm", response_model=PaymentResponse)
async def confirm_payment(payment_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    if payment.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment already processed")

    payment.status = "confirmed"
    payment.confirmed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(payment)

    await broadcast("payment_confirmed", {
        "payment_id": payment.id,
        "pool_id": payment.pool_id,
        "user_id": payment.user_id,
    })

    return PaymentResponse.model_validate(payment)


@router.post("/{payment_id}/cancel", response_model=PaymentResponse)
async def cancel_payment(payment_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    if payment.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment already processed")

    payment.status = "cancelled"
    payment.cancelled_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(payment)

    await broadcast("payment_cancelled", {
        "payment_id": payment.id,
        "pool_id": payment.pool_id,
        "user_id": payment.user_id,
    })

    return PaymentResponse.model_validate(payment)


@router.get("/list", response_model=list[PaymentListResponse])
async def list_payments(
    status: str = Query("pending", description="Filter by status"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Payment).where(Payment.status == status).order_by(Payment.created_at.desc())
    )
    payments = result.scalars().all()

    pool_ids = list(set(p.pool_id for p in payments))
    pools_map = {}
    if pool_ids:
        pool_result = await db.execute(
            select(Pool).options(selectinload(Pool.prize_grades)).where(Pool.id.in_(pool_ids))
        )
        for p in pool_result.scalars().all():
            pools_map[p.id] = p

    response = []
    for p in payments:
        pool = pools_map.get(p.pool_id)
        serial_list = [int(s) for s in p.serial_numbers.split(",") if s.strip()] if p.serial_numbers else []
        ticket_count = len(serial_list)
        response.append(PaymentListResponse(
            id=p.id,
            pool_id=p.pool_id,
            pool_name=pool.name if pool else "",
            pool_code=pool.code if pool else "",
            user_id=p.user_id,
            amount=p.amount,
            method=p.method,
            status=p.status,
            serial_numbers=p.serial_numbers,
            ticket_count=ticket_count,
            created_at=p.created_at,
            confirmed_at=p.confirmed_at,
        ))
    return response


@router.get("/qrcode/{payment_id}")
async def payment_qrcode(payment_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    img = qrcode.make(payment_id)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return PaymentResponse.model_validate(payment)
