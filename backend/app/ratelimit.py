"""Shared rate limiter instance (SlowAPI).

Kept in its own module so both ``main.py`` (app wiring) and the route
modules (``@limiter.limit`` decorators) can import it without a circular
import.
"""
from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# RATE_LIMIT_ENABLED=false disables all limits (used by the test suite, where
# every request shares the same client address).
_enabled = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() not in ("false", "0", "no")

limiter = Limiter(key_func=get_remote_address, enabled=_enabled)
