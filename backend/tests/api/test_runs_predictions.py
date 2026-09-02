"""API tests for health + runs + predictions."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestHealth:
    async def test_health(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


async def _auth(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "run@test.com", "password": "testpass123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_compound_and_method(client, headers):
    comp = await client.post(
        "/api/v1/compounds", json={"smiles": "CCO"}, headers=headers
    )
    cid = comp.json()["id"]
    meth = await client.post(
        "/api/v1/methods",
        json={
            "column_type": "C18",
            "gradient_table": [{"time_s": 0, "percent_b": 5}, {"time_s": 1200, "percent_b": 95}],
        },
        headers=headers,
    )
    mid = meth.json()["id"]
    return cid, mid


@pytest.mark.asyncio
class TestRuns:
    async def test_create_run(self, client):
        headers = await _auth(client)
        cid, mid = await _create_compound_and_method(client, headers)
        resp = await client.post(
            "/api/v1/runs",
            json={"compound_id": cid, "method_id": mid, "observed_rt_s": 180.5},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["observed_rt_s"] == 180.5

    async def test_list_runs(self, client):
        headers = await _auth(client)
        cid, mid = await _create_compound_and_method(client, headers)
        await client.post(
            "/api/v1/runs",
            json={"compound_id": cid, "method_id": mid, "observed_rt_s": 180.5},
            headers=headers,
        )
        resp = await client.get("/api/v1/runs", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


@pytest.mark.asyncio
class TestPredictions:
    async def test_create_prediction(self, client):
        headers = await _auth(client)
        cid, mid = await _create_compound_and_method(client, headers)
        resp = await client.post(
            "/api/v1/predictions",
            json={"compound_id": cid, "method_id": mid},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["predicted_rt_s"] is not None
        assert data["model_version"] == "rules-v1"
        assert data["confidence"] < 0.5  # rules-based = low confidence

    async def test_prediction_not_found(self, client):
        headers = await _auth(client)
        resp = await client.post(
            "/api/v1/predictions",
            json={
                "compound_id": "00000000-0000-0000-0000-000000000000",
                "method_id": "00000000-0000-0000-0000-000000000000",
            },
            headers=headers,
        )
        assert resp.status_code == 404
