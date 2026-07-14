import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Body
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.database import get_db
from backend.auth.models import User, RefreshToken, UserRole
from backend.auth.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, UserResponse,
    RefreshRequest, PasswordChangeRequest, PasswordResetRequest,
    PasswordResetConfirmRequest, ProfileUpdateRequest,
)
from backend.auth.utils import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, hash_token,
    generate_email_token, generate_password_reset_token,
)
from backend.auth.dependencies import get_current_user, get_optional_user
from backend.config import settings

logger = logging.getLogger("gigacorp.auth.router")

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        role=user.role.value if user.role else "customer",
        is_verified=user.is_verified,
        avatar_url=user.avatar_url,
        company=user.company,
        phone=user.phone,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


async def _create_tokens(user: User, request: Request, db: AsyncSession) -> TokenResponse:
    access_token = create_access_token(str(user.id), user.role.value)
    refresh_token_str = create_refresh_token(str(user.id))
    refresh_token_hash = hash_token(refresh_token_str)

    expires_at = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)

    db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=refresh_token_hash,
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent", "")[:500],
        ip_address=request.client.host if request.client else "unknown",
    )
    db.add(db_refresh)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=_user_to_response(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(User).where(or_(User.email == body.email, User.username == body.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email or username already registered")

    user = User(
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
        display_name=body.display_name or body.username,
        company=body.company,
        role=UserRole.CUSTOMER,
        email_verification_token=generate_email_token(),
    )
    db.add(user)
    await db.flush()

    logger.info("User registered: %s (%s)", user.email, user.id)
    return await _create_tokens(user, request, db)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(or_(
            User.email == body.email.strip().lower(),
            User.username == body.email.strip(),
        ))
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email/username or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    user.last_login_at = datetime.utcnow()
    db.add(user)
    await db.flush()

    logger.info("User logged in: %s", user.email)
    return await _create_tokens(user, request, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hash_token(body.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow(),
        )
    )
    db_token = result.scalar_one_or_none()

    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_result = await db.execute(select(User).where(User.id == db_token.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    db_token.revoked = True
    db.add(db_token)
    await db.flush()

    logger.debug("Token refreshed for user: %s", user.email)
    return await _create_tokens(user, request, db)


@router.post("/logout", status_code=204)
async def logout(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hash_token(body.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    db_token = result.scalar_one_or_none()
    if db_token:
        db_token.revoked = True
        db.add(db_token)
    return None


@router.post("/logout-all", status_code=204)
async def logout_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked == False,
        )
    )
    for token in result.scalars().all():
        token.revoked = True
        db.add(token)
    logger.info("All sessions revoked for user: %s", current_user.email)
    return None


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return _user_to_response(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.display_name is not None:
        current_user.display_name = body.display_name
    if body.company is not None:
        current_user.company = body.company
    if body.phone is not None:
        current_user.phone = body.phone
    if body.avatar_url is not None:
        current_user.avatar_url = body.avatar_url
    current_user.updated_at = datetime.utcnow()
    db.add(current_user)
    logger.info("Profile updated for user: %s", current_user.email)
    return _user_to_response(current_user)


@router.post("/change-password", status_code=200)
async def change_password(
    body: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.hashed_password = hash_password(body.new_password)
    current_user.updated_at = datetime.utcnow()
    db.add(current_user)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked == False,
        )
    )
    for token in result.scalars().all():
        token.revoked = True
        db.add(token)

    logger.info("Password changed for user: %s", current_user.email)
    return {"detail": "Password changed successfully. All other sessions have been logged out."}


@router.post("/request-password-reset", status_code=200)
async def request_password_reset(
    body: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == body.email.strip().lower()))
    user = result.scalar_one_or_none()

    if user:
        token = generate_password_reset_token()
        user.password_reset_token = hash_token(token)
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        db.add(user)
        logger.info("Password reset requested for: %s", user.email)

    return {"detail": "If the email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=200)
async def reset_password(
    body: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.password_reset_token.isnot(None),
            User.password_reset_expires > datetime.utcnow(),
        )
    )
    user = None
    for row in result.scalars().all():
        if row.password_reset_token == hash_token(body.token):
            user = row
            break

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.hashed_password = hash_password(body.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.updated_at = datetime.utcnow()
    db.add(user)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked == False,
        )
    )
    for token in result.scalars().all():
        token.revoked = True
        db.add(token)

    logger.info("Password reset completed for: %s", user.email)
    return {"detail": "Password has been reset successfully."}


@router.post("/verify-email", status_code=200)
async def verify_email(
    token: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_verified:
        return {"detail": "Email already verified"}

    stored_hash = hash_token(token)
    if current_user.email_verification_token != stored_hash:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    current_user.is_verified = True
    current_user.verified_at = datetime.utcnow()
    current_user.email_verification_token = None
    db.add(current_user)

    logger.info("Email verified for user: %s", current_user.email)
    return {"detail": "Email verified successfully"}


@router.post("/resend-verification", status_code=200)
async def resend_verification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_verified:
        return {"detail": "Email already verified"}

    current_user.email_verification_token = generate_email_token()
    db.add(current_user)
    logger.info("Verification email resent for: %s", current_user.email)
    return {"detail": "Verification email sent"}
