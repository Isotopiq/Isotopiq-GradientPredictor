"""Auth routes: register, login, refresh, me, profile, forgot/reset password."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    refresh_token_ttl,
)
from app.auth.security import hash_password, verify_password
from app.config import settings
from app.core.file_validation import NOSNIFF_HEADERS, read_upload_limited, sniff_image_mime
from app.deps import CurrentUser, DBSession
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.ratelimit import limiter
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

# Fixed bcrypt hash used to equalize login timing for unknown emails
_DUMMY_HASH = hash_password("dummy-password-for-timing")


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, data: UserRegister, db: DBSession) -> TokenPair:
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
    return await _make_token_pair(db, user)


@router.post("/login", response_model=TokenPair)
@limiter.limit("10/minute")
async def login(request: Request, data: UserLogin, db: DBSession) -> TokenPair:
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    # Always run bcrypt to avoid a timing oracle that reveals whether the
    # email is registered (compare against a fixed dummy hash).
    password_hash = user.password_hash if user is not None else _DUMMY_HASH
    if user is None or not verify_password(data.password, password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account deactivated")
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await log_action(db, user, "login")
    return await _make_token_pair(db, user)


@router.post("/login-remember", response_model=TokenPair)
@limiter.limit("10/minute")
async def login_with_remember(request: Request, data: RememberMeLogin, db: DBSession) -> TokenPair:
    """Login with optional remember-me for extended token TTL."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    password_hash = user.password_hash if user is not None else _DUMMY_HASH
    if user is None or not verify_password(data.password, password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account deactivated")
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await log_action(db, user, "login")
    return await _make_token_pair(db, user, remember_me=data.remember_me)


@router.post("/refresh", response_model=TokenPair)
@limiter.limit("30/minute")
async def refresh(request: Request, data: RefreshRequest, db: DBSession) -> TokenPair:
    try:
        payload = decode_refresh_token(data.refresh_token)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token") from None

    sub = payload.get("sub")
    jti = payload.get("jti")
    try:
        user_id = uuid.UUID(sub) if sub else None
    except (ValueError, AttributeError):
        user_id = None
    user = await db.get(User, user_id) if user_id else None
    if user is None or not user.is_active or not jti:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    # The refresh token must map to a live server-side session — this is what
    # makes logout, password-reset revocation and rotation work.
    jti_hash = hashlib.sha256(str(jti).encode()).hexdigest()
    result = await db.execute(
        select(RefreshSession).where(RefreshSession.jti_hash == jti_hash)
    )
    session = result.scalar_one_or_none()
    if session is None or not session.is_active or session.user_id != user.id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    # Rotate: revoke the presented session, issue a fresh pair + session.
    session.revoked_at = datetime.now(timezone.utc)
    return await _make_token_pair(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshRequest, db: DBSession) -> None:
    """Revoke the presented refresh token's session. Idempotent."""
    try:
        payload = decode_refresh_token(data.refresh_token)
    except ValueError:
        return None
    jti = payload.get("jti")
    if jti:
        jti_hash = hashlib.sha256(str(jti).encode()).hexdigest()
        result = await db.execute(
            select(RefreshSession).where(RefreshSession.jti_hash == jti_hash)
        )
        session = result.scalar_one_or_none()
        if session is not None and session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            await db.commit()
    return None


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
    contents = await read_upload_limited(file, MAX_PROFILE_PIC_SIZE)
    # Validate actual content — the client Content-Type header is spoofable
    real_mime = sniff_image_mime(contents)
    if real_mime is None or real_mime not in ALLOWED_PIC_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid image content. Allowed: {', '.join(ALLOWED_PIC_TYPES)}",
        )
    current.profile_picture_bytes = contents
    current.profile_picture_mime_type = real_mime
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
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or user.profile_picture_bytes is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No profile picture")
    return Response(
        content=user.profile_picture_bytes,
        media_type=user.profile_picture_mime_type or "image/png",
        headers=NOSNIFF_HEADERS,
    )


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/minute")
async def forgot_password(request: Request, data: ForgotPasswordRequest, db: DBSession) -> dict:
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
@limiter.limit("5/minute")
async def reset_password(request: Request, data: ResetPasswordRequest, db: DBSession) -> dict:
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
    # Revoke all outstanding refresh sessions for this user
    await db.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()

    return {"message": "Password reset successfully. Please log in."}


async def _make_token_pair(
    db: AsyncSession, user: User, remember_me: bool = False
) -> TokenPair:
    """Issue an access/refresh pair and persist the refresh session.

    The refresh token's ``jti`` is stored (hashed) server-side so sessions can
    be revoked on logout, password reset, or admin deactivation.
    """
    jti = str(uuid.uuid4())
    db.add(
        RefreshSession(
            user_id=user.id,
            jti_hash=hashlib.sha256(jti.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc) + refresh_token_ttl(remember_me),
        )
    )
    await db.commit()
    return TokenPair(
        access_token=create_access_token(str(user.id), remember_me=remember_me),
        refresh_token=create_refresh_token(str(user.id), remember_me=remember_me, jti=jti),
        user=_user_to_out(user),
    )
