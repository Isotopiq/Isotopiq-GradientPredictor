"""Seed a default admin user on first startup.

Controlled by env vars:
  ADMIN_EMAIL (default: admin@lcms.local)
  ADMIN_PASSWORD (default: changeme-admin-2024!)

If the user already exists, this is a no-op.
"""
from __future__ import annotations

import logging

import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password, verify_password
from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


async def seed_admin(db: AsyncSession) -> None:
    """Create or update the default admin user from env vars.

    On first startup, creates the admin user.
    On subsequent startups, updates the password (and email if changed) so
    that changing ADMIN_EMAIL/ADMIN_PASSWORD in the env file takes effect
    without needing to wipe the database.
    """
    email = settings.admin_email
    password = settings.admin_password

    # In production, config.py replaces an unset/default ADMIN_PASSWORD with an
    # ephemeral random value — surface it once here so the deployer can log in
    # (visible only in container logs).
    # NB: compose injects the default string when ADMIN_PASSWORD is unset, so
    # treat "unset OR still-default" as ephemeral.
    env_pw = os.environ.get("ADMIN_PASSWORD")
    prod_ephemeral = (
        settings.app_env.lower() in ("production", "prod")
        and (not env_pw or env_pw == "changeme-admin-2024!")
    )
    if prod_ephemeral:
        logger.warning(
            ">>> EPHEMERAL ADMIN PASSWORD for '%s': %s  — set ADMIN_PASSWORD "
            "in the environment for a persistent password (this value "
            "regenerates on every restart).",
            email,
            password,
        )
    elif password == "changeme-admin-2024!":
        logger.warning(
            "ADMIN_PASSWORD is unset/default — the seeded admin uses a "
            "publicly known password. Set ADMIN_PASSWORD in the environment."
        )

    # Look up by email first
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()

    if existing is not None:
        # User exists — update password in case it changed in env
        if not verify_password(password, existing.password_hash):
            existing.password_hash = hash_password(password)
            await db.commit()
            logger.info("Admin user '%s' password updated from env.", email)
        else:
            logger.info("Admin user '%s' already exists — no changes.", email)
        return

    # No user with this email — maybe the email was changed in env.
    # Look for any existing admin user and update it. Use first() not
    # scalar_one_or_none(): multiple admins may exist and would raise
    # MultipleResultsFound, crash-looping startup.
    result = await db.execute(select(User).where(User.is_admin == True))
    any_admin = result.scalars().first()
    if any_admin is not None:
        any_admin.email = email
        any_admin.password_hash = hash_password(password)
        await db.commit()
        logger.info("Admin user updated to '%s' from env.", email)
        return

    # No admin user at all — create one
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name="System Administrator",
        is_admin=True,
    )
    db.add(user)
    await db.commit()
    logger.info("Seeded admin user '%s'.", email)
