"""SMTP email service for password reset and notifications."""
from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email via SMTP. Returns True on success, False on failure."""
    if not settings.smtp_host:
        logger.warning("SMTP not configured — email not sent to %s", to)
        return False

    msg = EmailMessage()
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_use_tls,
        )
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False


async def send_password_reset_email(to: str, reset_link: str) -> bool:
    """Send a password reset email with a reset link."""
    subject = "IsotopiQ — Password Reset"
    body = f"""You requested a password reset for your IsotopiQ account.

Click the link below to reset your password (valid for 1 hour):
{reset_link}

If you didn't request this, you can safely ignore this email.

— IsotopiQ LC-MS Suite
"""
    return await send_email(to, subject, body)
