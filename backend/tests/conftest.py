"""Pytest fixtures.

For unit tests we don't need a DB. For API tests we use a SQLite-in-memory
engine via aiosqlite so tests run without a Postgres dependency.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Force test config: use SQLite for tests unless DATABASE_URL is explicitly set
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",
)
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:18717")
os.environ.setdefault("MODEL_STORAGE_PATH", "./test_models")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
