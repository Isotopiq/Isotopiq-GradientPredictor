"""Audit log service — records user actions for admin visibility."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)


async def log_action(
    db: AsyncSession,
    user: User | None = None,
    action: str = "",
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
) -> None:
    """Record an audit log entry. Silently fails to avoid disrupting the request."""
    try:
        entry = AuditLog(
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            detail=detail,
            ip_address=ip_address,
        )
        db.add(entry)
        await db.commit()
    except Exception:
        logger.warning("Failed to write audit log: action=%s", action, exc_info=True)
        await db.rollback()


async def list_audit_logs(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    action: str | None = None,
    user_id: Any | None = None,
) -> tuple[list[AuditLog], int]:
    """List audit logs with optional filtering. Returns (logs, total_count)."""
    stmt = select(AuditLog)
    count_stmt = select(func.count(AuditLog.id))

    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
        count_stmt = count_stmt.where(AuditLog.user_id == user_id)

    stmt = stmt.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
    result = await db.execute(stmt)
    logs = list(result.scalars().all())

    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    return logs, total


def audit_log_to_dict(log: AuditLog) -> dict:
    return {
        "id": str(log.id),
        "user_id": str(log.user_id) if log.user_id else None,
        "user_email": log.user_email,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "detail": log.detail,
        "ip_address": log.ip_address,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }
