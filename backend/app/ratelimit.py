"""Shared rate limiter instance (SlowAPI).

Kept in its own module so both ``main.py`` (app wiring) and the route
modules (``@limiter.limit`` decorators) can import it without a circular
import.
"""
from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _client_key(request: Request) -> str:
    """Rate-limit key — prefers X-Forwarded-For set by the nginx/Traefik proxy.

    Behind a reverse proxy every request's client.host is the proxy IP, so
    get_remote_address would pool ALL users into one bucket. We trust the
    first XFF entry because our own nginx always sets it (and the app is only
    reachable through it in deployment).
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


# RATE_LIMIT_ENABLED=false disables all limits (used by the test suite, where
# every request shares the same client address).
_enabled = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() not in ("false", "0", "no")

limiter = Limiter(key_func=_client_key, enabled=_enabled)
