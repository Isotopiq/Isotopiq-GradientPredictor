"""Password hashing using bcrypt directly (avoids passlib compat issues)."""
from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    """Hash a password with bcrypt. Truncates to 72 bytes (bcrypt limit)."""
    pw_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    pw_bytes = password.encode("utf-8")[:72]
    hash_bytes = password_hash.encode("utf-8")
    try:
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except (ValueError, TypeError):
        return False
