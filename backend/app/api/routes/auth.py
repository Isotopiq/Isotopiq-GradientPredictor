"""Auth routes: register, login, refresh, me, profile, forgot/reset password."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, create_refresh_token, decode_refresh_token
from app.auth.security import hash_password, verify_password
from app.config import settings
from app.deps import CurrentUser, DBSession
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    ProfileUpdate,
    RefreshRequest,
    RememberMeLogin,
    ResetPasswordRequest,
    TokenPair,
    UserLogin,
    UserOut,
    UserRegister,
)
from app.services.audit_service import log_action
from app.services.email_service import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_PROFILE_PIC_SIZE = 10 * 1024 * 1024
ALLOWED_PIC_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: DBSession) -> TokenPair:
    # Check if registration is enabled
    from app.models.app_settings import AppSettings
    settings_result = await db.execute(select(AppSettings).limit(1))
    app_settings = settings_result.scalar_one_or_none()
    if app_settings is not None and not app_settings.registration_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Registration is currently disabled. Contact an administrator.")

    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=data.email, password_hash=hash_password(data.password), full_name=data.full_name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _make_token_pair(user)


@router.post("/login", response_model=TokenPair)
async def login(data: UserLogin, db: DBSession) -> TokenPair:
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account deactivated")
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await log_action(db, user, "login")
    return _make_token_pair(user)


@router.post("/login-remember", response_model=TokenPair)
async def login_with_remember(data: RememberMeLogin, db: DBSession) -> TokenPair:
    """Login with optional remember-me for extended token TTL."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account deactivated")
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await log_action(db, user, "login")
    return _make_token_pair(user, remember_me=data.remember_me)


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshRequest, db: DBSession) -> TokenPair:
    try:
        payload = decode_refresh_token(data.refresh_token)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    import uuid as _uuid

    user = await db.get(User, _uuid.UUID(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return _make_token_pair(user)


def _user_to_out(u: User) -> UserOut:
    """Convert User ORM to UserOut, computing has_profile_picture."""
    return UserOut(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        is_admin=u.is_admin,
        is_active=u.is_active,
        has_profile_picture=u.profile_picture_bytes is not None,
        last_login_at=u.last_login_at,
    )


@router.get("/me", response_model=UserOut)
async def me(current: CurrentUser) -> UserOut:
    return _user_to_out(current)


@router.put("/profile", response_model=UserOut)
async def update_profile(data: ProfileUpdate, db: DBSession, current: CurrentUser) -> UserOut:
    """Update own profile (name, email)."""
    if data.full_name is not None:
        current.full_name = data.full_name
    if data.email is not None and data.email != current.email:
        # Check email not taken
        existing = await db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")
        current.email = data.email
    await db.commit()
    await db.refresh(current)
    await log_action(db, current, "profile_update")
    return _user_to_out(current)


@router.post("/profile/picture", response_model=UserOut)
async def upload_profile_picture(
    db: DBSession,
    current: CurrentUser,
    file: UploadFile = File(...),
) -> UserOut:
    """Upload a profile picture."""
    if file.content_type not in ALLOWED_PIC_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid image type. Allowed: {', '.join(ALLOWED_PIC_TYPES)}",
        )
    contents = await file.read()
    if len(contents) > MAX_PROFILE_PIC_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Image too large (max 10 MB)")
    current.profile_picture_bytes = contents
    current.profile_picture_mime_type = file.content_type
    await db.commit()
    await db.refresh(current)
    await log_action(db, current, "profile_picture_upload")
    return _user_to_out(current)


@router.delete("/profile/picture", response_model=UserOut)
async def delete_profile_picture(db: DBSession, current: CurrentUser) -> UserOut:
    """Remove profile picture."""
    current.profile_picture_bytes = None
    current.profile_picture_mime_type = None
    await db.commit()
    await db.refresh(current)
    return _user_to_out(current)


@router.get("/profile/picture/{user_id}")
async def get_profile_picture(user_id: str, db: DBSession) -> Response:
    """Serve a user's profile picture. Public for display in UI."""
    import uuid as _uuid
    result = await db.execute(select(User).where(User.id == _uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or user.profile_picture_bytes is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No profile picture")
    return Response(content=user.profile_picture_bytes, media_type=user.profile_picture_mime_type or "image/png")


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(data: ForgotPasswordRequest, db: DBSession) -> dict:
    """Request a password reset email. Always returns 202 to avoid user enumeration."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user is not None:
        # Invalidate any existing tokens for this user
        await db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id)
            .values(used=True)
        )

        # Generate a raw token, store its hash
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_token)
        await db.commit()

        # Send email
        reset_link = f"{settings.frontend_url}/reset-password?token={raw_token}"
        await send_password_reset_email(user.email, reset_link)

    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(data: ResetPasswordRequest, db: DBSession) -> dict:
    """Reset password using a valid reset token."""
    token_hash = hashlib.sha256(data.token.encode()).hexdigest()
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    reset_token = result.scalar_one_or_none()

    if reset_token is None or reset_token.used or reset_token.is_expired:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token")

    user = await db.get(User, reset_token.user_id)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User not found")

    user.password_hash = hash_password(data.new_password)
    reset_token.used = True
    await db.commit()

    return {"message": "Password reset successfully. Please log in."}


def _make_token_pair(user: User, remember_me: bool = False) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(str(user.id), remember_me=remember_me),
        refresh_token=create_refresh_token(str(user.id), remember_me=remember_me),
        user=_user_to_out(user),
    )
