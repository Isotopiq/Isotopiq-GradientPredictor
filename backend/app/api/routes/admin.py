"""Admin routes: app settings, logo upload, user management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import CurrentUser, DBSession
from app.models.app_settings import AppSettings
from app.models.user import User
from app.schemas.auth import AdminUserOut, AdminUserUpdate
from app.services.audit_service import log_action, list_audit_logs, audit_log_to_dict, clear_audit_logs

router = APIRouter(prefix="/admin", tags=["admin"])

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/svg+xml"}
MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2 MB


class AppSettingsOut(BaseModel):
    lab_name: str
    lab_subtitle: str
    lab_address: str | None = None
    lab_website: str | None = None
    has_logo: bool
    logo_mime_type: str | None = None
    report_footer: str
    registration_enabled: bool


class AppSettingsUpdate(BaseModel):
    lab_name: str | None = None
    lab_subtitle: str | None = None
    lab_address: str | None = None
    lab_website: str | None = None
    report_footer: str | None = None
    registration_enabled: bool | None = None


async def _require_admin(user: User) -> None:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")


async def _get_or_create_settings(db: AsyncSession) -> AppSettings:
    result = await db.execute(select(AppSettings).limit(1))
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = AppSettings.default()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.get("/settings", response_model=AppSettingsOut)
async def get_settings(db: DBSession, current: CurrentUser) -> AppSettingsOut:
    """Get app settings. Available to all authenticated users (needed for branding)."""
    settings = await _get_or_create_settings(db)
    return AppSettingsOut(
        lab_name=settings.lab_name,
        lab_subtitle=settings.lab_subtitle,
        lab_address=settings.lab_address,
        lab_website=settings.lab_website,
        has_logo=settings.logo_bytes is not None,
        logo_mime_type=settings.logo_mime_type,
        report_footer=settings.report_footer,
        registration_enabled=settings.registration_enabled,
    )


@router.put("/settings", response_model=AppSettingsOut)
async def update_settings(
    data: AppSettingsUpdate,
    db: DBSession,
    current: CurrentUser,
) -> AppSettingsOut:
    """Update app settings. Admin only."""
    await _require_admin(current)
    settings = await _get_or_create_settings(db)
    if data.lab_name is not None:
        settings.lab_name = data.lab_name
    if data.lab_subtitle is not None:
        settings.lab_subtitle = data.lab_subtitle
    if data.lab_address is not None:
        settings.lab_address = data.lab_address
    if data.lab_website is not None:
        settings.lab_website = data.lab_website
    if data.report_footer is not None:
        settings.report_footer = data.report_footer
    if data.registration_enabled is not None:
        settings.registration_enabled = data.registration_enabled
    await db.commit()
    await db.refresh(settings)
    return AppSettingsOut(
        lab_name=settings.lab_name,
        lab_subtitle=settings.lab_subtitle,
        lab_address=settings.lab_address,
        lab_website=settings.lab_website,
        has_logo=settings.logo_bytes is not None,
        logo_mime_type=settings.logo_mime_type,
        report_footer=settings.report_footer,
        registration_enabled=settings.registration_enabled,
    )


@router.post("/logo", response_model=AppSettingsOut)
async def upload_logo(
    db: DBSession,
    current: CurrentUser,
    file: UploadFile = File(...),
) -> AppSettingsOut:
    """Upload a logo image. Admin only."""
    await _require_admin(current)

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid image type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )

    contents = await file.read()
    if len(contents) > MAX_LOGO_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Logo too large (max 2 MB)")

    settings = await _get_or_create_settings(db)
    settings.logo_bytes = contents
    settings.logo_mime_type = file.content_type
    await db.commit()
    await db.refresh(settings)

    return AppSettingsOut(
        lab_name=settings.lab_name,
        lab_subtitle=settings.lab_subtitle,
        lab_address=settings.lab_address,
        lab_website=settings.lab_website,
        has_logo=True,
        logo_mime_type=settings.logo_mime_type,
        report_footer=settings.report_footer,
        registration_enabled=settings.registration_enabled,
    )


@router.delete("/logo", response_model=AppSettingsOut)
async def delete_logo(db: DBSession, current: CurrentUser) -> AppSettingsOut:
    """Remove the logo. Admin only."""
    await _require_admin(current)
    settings = await _get_or_create_settings(db)
    settings.logo_bytes = None
    settings.logo_mime_type = None
    await db.commit()
    await db.refresh(settings)
    return AppSettingsOut(
        lab_name=settings.lab_name,
        lab_subtitle=settings.lab_subtitle,
        lab_address=settings.lab_address,
        lab_website=settings.lab_website,
        has_logo=False,
        logo_mime_type=None,
        report_footer=settings.report_footer,
        registration_enabled=settings.registration_enabled,
    )


@router.get("/logo")
async def get_logo(db: DBSession) -> Response:
    """Serve the logo image. Public (no auth) for use in reports and UI."""
    settings = await _get_or_create_settings(db)
    if settings.logo_bytes is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No logo set")
    return Response(content=settings.logo_bytes, media_type=settings.logo_mime_type or "image/png")


@router.get("/public-settings")
async def get_public_settings(db: DBSession) -> dict:
    """Public settings (no auth) — used by login/register page to show/hide registration."""
    settings = await _get_or_create_settings(db)
    return {
        "registration_enabled": settings.registration_enabled,
        "lab_name": settings.lab_name,
        "lab_subtitle": settings.lab_subtitle,
    }


# --- User Management ---


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    db: DBSession,
    current: CurrentUser,
    search: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[AdminUserOut]:
    """List all users. Admin only."""
    await _require_admin(current)
    stmt = select(User).order_by(User.created_at.desc())
    if search:
        stmt = stmt.where(User.email.ilike(f"%{search}%"))
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return [
        AdminUserOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            is_admin=u.is_admin,
            is_active=u.is_active,
            has_profile_picture=u.profile_picture_bytes is not None,
            last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
            created_at=u.created_at.isoformat() if u.created_at else None,
        )
        for u in users
    ]


@router.get("/users/count")
async def count_users(db: DBSession, current: CurrentUser) -> dict:
    """Get user count stats. Admin only."""
    await _require_admin(current)
    total = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar() or 0
    admins = (await db.execute(select(func.count(User.id)).where(User.is_admin == True))).scalar() or 0
    return {"total": total, "active": active, "admins": admins}


@router.put("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: str,
    data: AdminUserUpdate,
    db: DBSession,
    current: CurrentUser,
) -> AdminUserOut:
    """Update a user (toggle admin, activate/deactivate). Admin only."""
    await _require_admin(current)
    import uuid as _uuid
    result = await db.execute(select(User).where(User.id == _uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if data.is_admin is not None:
        user.is_admin = data.is_admin
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.full_name is not None:
        user.full_name = data.full_name
    await db.commit()
    await db.refresh(user)
    await log_action(db, current, "user_update", "user", user_id, f"Updated {user.email}")
    return AdminUserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        is_active=user.is_active,
        has_profile_picture=user.profile_picture_bytes is not None,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: DBSession,
    current: CurrentUser,
) -> None:
    """Delete a user. Admin only. Cannot delete yourself."""
    await _require_admin(current)
    import uuid as _uuid
    if str(current.id) == user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete your own account")
    result = await db.execute(select(User).where(User.id == _uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    email = user.email
    await db.delete(user)
    await db.commit()
    await log_action(db, current, "user_delete", "user", user_id, f"Deleted {email}")


# --- Audit Log ---


@router.get("/audit-logs")
async def get_audit_logs(
    db: DBSession,
    current: CurrentUser,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: str | None = Query(None),
) -> dict:
    """View audit logs. Admin only."""
    await _require_admin(current)
    logs, total = await list_audit_logs(db, limit=limit, offset=offset, action=action)
    return {
        "logs": [audit_log_to_dict(l) for l in logs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/audit-logs")
async def delete_audit_logs(db: DBSession, current: CurrentUser) -> dict:
    """Clear all audit logs. Admin only."""
    await _require_admin(current)
    deleted = await clear_audit_logs(db)
    # Log the clear action itself (after the delete so it's the only entry)
    await log_action(db, current, "audit_logs_clear", "audit_log", None, f"Cleared {deleted} audit log entries")
    return {"deleted": deleted}


@router.get("/stats")
async def get_admin_stats(db: DBSession, current: CurrentUser) -> dict:
    """Get admin dashboard stats. Admin only."""
    await _require_admin(current)
    from sqlalchemy import select as sa_select, func as sa_func
    from app.models.compound import Compound
    from app.models.method import Method
    from app.models.run import Run
    from app.models.audit_log import AuditLog

    total_users = (await db.execute(sa_select(sa_func.count(User.id)))).scalar() or 0
    active_users = (await db.execute(sa_select(sa_func.count(User.id)).where(User.is_active == True))).scalar() or 0
    total_compounds = (await db.execute(sa_select(sa_func.count(Compound.id)))).scalar() or 0
    total_methods = (await db.execute(sa_select(sa_func.count(Method.id)))).scalar() or 0
    total_runs = (await db.execute(sa_select(sa_func.count(Run.id)))).scalar() or 0
    total_logs = (await db.execute(sa_select(sa_func.count(AuditLog.id)))).scalar() or 0

    return {
        "users": {"total": total_users, "active": active_users},
        "compounds": total_compounds,
        "methods": total_methods,
        "runs": total_runs,
        "audit_logs": total_logs,
    }
