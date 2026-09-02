"""API tests for auth endpoints."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestAuth:
    async def test_register(self, client):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "new@test.com", "password": "testpass123"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "new@test.com"

    async def test_register_duplicate(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "dup@test.com", "password": "testpass123"},
        )
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "dup@test.com", "password": "testpass123"},
        )
        assert resp.status_code == 409

    async def test_login(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "login@test.com", "password": "testpass123"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "login@test.com", "password": "testpass123"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_login_wrong_password(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "wrong@test.com", "password": "testpass123"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@test.com", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    async def test_me(self, client):
        headers = await register_and_login(client)
        resp = await client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "test@test.com"

    async def test_me_no_token(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401


async def register_and_login(client, email="test@test.com", password="testpass123"):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    tokens = resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}
