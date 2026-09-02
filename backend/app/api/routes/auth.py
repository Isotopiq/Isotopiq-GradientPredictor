"""Auth routes: register, login, refresh, me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, create_refresh_token, decode_refresh_token
from app.auth.security import hash_password, verify_password
from app.deps import CurrentUser, DBSession
from app.models.user import User
from app.schemas.auth import RefreshRequest, TokenPair, UserLogin, UserOut, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: DBSession) -> TokenPair:
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
    return _make_token_pair(user)


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


@router.get("/me", response_model=UserOut)
async def me(current: CurrentUser) -> User:
    return current


def _make_token_pair(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        user=UserOut(id=user.id, email=user.email, full_name=user.full_name),
    )
