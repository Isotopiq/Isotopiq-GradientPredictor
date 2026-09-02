"""API tests for compound endpoints."""
from __future__ import annotations

import pytest


async def _auth(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "comp@test.com", "password": "testpass123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
class TestCompounds:
    async def test_create_compound_from_smiles(self, client):
        headers = await _auth(client)
        resp = await client.post(
            "/api/v1/compounds",
            json={"smiles": "CCO", "name": "ethanol"},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["smiles"] == "CCO"
        assert data["mw"] is not None
        assert 45 < data["mw"] < 47
        assert data["logp"] is not None

    async def test_create_compound_invalid_smiles(self, client):
        headers = await _auth(client)
        resp = await client.post(
            "/api/v1/compounds",
            json={"smiles": "not-valid!!!"},
            headers=headers,
        )
        assert resp.status_code == 400

    async def test_create_compound_no_input(self, client):
        headers = await _auth(client)
        resp = await client.post("/api/v1/compounds", json={}, headers=headers)
        assert resp.status_code == 400

    async def test_list_compounds(self, client):
        headers = await _auth(client)
        await client.post(
            "/api/v1/compounds", json={"smiles": "CCO"}, headers=headers
        )
        await client.post(
            "/api/v1/compounds", json={"smiles": "c1ccccc1"}, headers=headers
        )
        resp = await client.get("/api/v1/compounds", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    async def test_get_compound(self, client):
        headers = await _auth(client)
        create = await client.post(
            "/api/v1/compounds", json={"smiles": "CCO"}, headers=headers
        )
        cid = create.json()["id"]
        resp = await client.get(f"/api/v1/compounds/{cid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == cid

    async def test_get_compound_not_found(self, client):
        headers = await _auth(client)
        resp = await client.get(
            "/api/v1/compounds/00000000-0000-0000-0000-000000000000", headers=headers
        )
        assert resp.status_code == 404

    async def test_delete_compound(self, client):
        headers = await _auth(client)
        create = await client.post(
            "/api/v1/compounds", json={"smiles": "CCO"}, headers=headers
        )
        cid = create.json()["id"]
        resp = await client.delete(f"/api/v1/compounds/{cid}", headers=headers)
        assert resp.status_code == 204

    async def test_compounds_require_auth(self, client):
        resp = await client.get("/api/v1/compounds")
        assert resp.status_code == 401
