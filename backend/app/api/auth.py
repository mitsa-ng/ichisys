from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin
from app.limiter import limiter
from app.models.admin import Admin
from app.schemas.admin import (
    AdminLogin,
    AdminOTPSetup,
    AdminOTPVerify,
    AdminResponse,
    OTPSetupResponse,
    TokenResponse,
)
from app.services.auth import (
    create_access_token,
    generate_otp_secret,
    generate_qr_code_base64,
    get_otp_uri,
    hash_password,
    verify_otp,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: AdminLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Admin).where(Admin.email == body.email))
    admin = result.scalar_one_or_none()
    if not admin or not verify_password(body.password, admin.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if admin.is_otp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP required",
        )
    token = create_access_token(admin.id)
    return TokenResponse(access_token=token, admin=AdminResponse.model_validate(admin))


@router.post("/verify-otp", response_model=TokenResponse)
@limiter.limit("10/minute")
async def verify_otp_login(request: Request, body: AdminOTPVerify, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Admin).where(Admin.email == body.email))
    admin = result.scalar_one_or_none()
    if not admin or not admin.otp_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid request")
    if not verify_otp(admin.otp_secret, body.otp_code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP code")
    token = create_access_token(admin.id)
    return TokenResponse(access_token=token, admin=AdminResponse.model_validate(admin))


@router.post("/setup-otp", response_model=OTPSetupResponse)
async def setup_otp(admin: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    secret = generate_otp_secret()
    uri = get_otp_uri(secret, admin.email)
    qr_svg = generate_qr_code_base64(uri)
    admin.otp_secret = secret
    await db.commit()
    return OTPSetupResponse(otp_secret=secret, otp_uri=uri, qr_code=qr_svg)


@router.post("/confirm-otp", response_model=AdminResponse)
async def confirm_otp(
    body: AdminOTPSetup,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if not admin.otp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP not setup yet")
    if not verify_otp(admin.otp_secret, body.otp_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP code")
    admin.is_otp_enabled = True
    await db.commit()
    await db.refresh(admin)
    return AdminResponse.model_validate(admin)


@router.post("/disable-otp", response_model=AdminResponse)
async def disable_otp(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    admin.otp_secret = None
    admin.is_otp_enabled = False
    await db.commit()
    await db.refresh(admin)
    return AdminResponse.model_validate(admin)


@router.get("/me", response_model=AdminResponse)
async def get_me(admin: Admin = Depends(get_current_admin)):
    return AdminResponse.model_validate(admin)
