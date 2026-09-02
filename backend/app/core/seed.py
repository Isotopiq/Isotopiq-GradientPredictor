"""Seed a default admin user on first startup.

Controlled by env vars:
  ADMIN_EMAIL (default: admin@lcms.local)
  ADMIN_PASSWORD (default: changeme-admin-2024!)

If the user already exists, this is a no-op.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


async def seed_admin(db: AsyncSession) -> None:
    """Create the default admin user if it doesn't already exist."""
    email = settings.admin_email
    password = settings.admin_password

    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing is not None:
        logger.info("Admin user '%s' already exists — skipping seed.", email)
        return

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name="System Administrator",
        is_admin=True,
    )
    db.add(user)
    await db.commit()
    logger.info("Seeded admin user '%s'.", email)
