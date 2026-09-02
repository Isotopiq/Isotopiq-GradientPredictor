"""Auth schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    is_admin: bool = False
    is_active: bool = True
    has_profile_picture: bool = False
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None


class AdminUserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    is_admin: bool = False
    is_active: bool = True
    has_profile_picture: bool = False
    last_login_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class AdminUserUpdate(BaseModel):
    is_admin: bool | None = None
    is_active: bool | None = None
    full_name: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class RememberMeLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False
