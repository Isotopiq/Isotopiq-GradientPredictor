"""API test fixtures: in-memory SQLite DB + TestClient + auth helpers."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
os.environ.setdefault("MODEL_STORAGE_PATH", "./test_models")

from app.models import Base  # noqa: E402


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    sessionmaker = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX AsyncClient with the DB patched to use the test engine."""
    from app import database as db_module
    from app import deps as deps_module

    test_sessionmaker = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def _get_test_db():
        async with test_sessionmaker() as session:
            yield session

    # Patch the dependency
    from app.main import app
    from app.deps import get_db

    app.dependency_overrides[get_db] = _get_test_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


async def register_and_login(client: AsyncClient, email: str = "test@test.com", password: str = "testpass123") -> dict:
    """Register a user and return auth headers."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    tokens = resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
def auth_headers_factory():
    return register_and_login
