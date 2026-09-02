"""API tests for ML endpoints."""
from __future__ import annotations

import pytest

from tests.fixtures import get_fixture_csv_bytes


async def _auth(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "ml@test.com", "password": "testpass123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
class TestMLTrain:
    async def test_train_from_csv(self, client):
        headers = await _auth(client)
        csv_bytes = get_fixture_csv_bytes()
        resp = await client.post(
            "/api/v1/ml/train/csv",
            params={"column_type": "C18", "model_type": "sklearn"},
            files={"file": ("compounds.csv", csv_bytes, "text/csv")},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["column_type"] == "C18"
        assert data["model_type"] == "sklearn"
        assert data["n_samples"] > 0
        assert "metrics" in data

    async def test_train_xgboost(self, client):
        headers = await _auth(client)
        csv_bytes = get_fixture_csv_bytes()
        resp = await client.post(
            "/api/v1/ml/train/csv",
            params={"column_type": "C18", "model_type": "xgboost"},
            files={"file": ("compounds.csv", csv_bytes, "text/csv")},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text

    async def test_list_models(self, client):
        headers = await _auth(client)
        csv_bytes = get_fixture_csv_bytes()
        await client.post(
            "/api/v1/ml/train/csv",
            params={"column_type": "C18", "model_type": "sklearn"},
            files={"file": ("compounds.csv", csv_bytes, "text/csv")},
            headers=headers,
        )
        resp = await client.get("/api/v1/ml/models", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_get_model(self, client):
        headers = await _auth(client)
        csv_bytes = get_fixture_csv_bytes()
        train_resp = await client.post(
            "/api/v1/ml/train/csv",
            params={"column_type": "C18", "model_type": "sklearn"},
            files={"file": ("compounds.csv", csv_bytes, "text/csv")},
            headers=headers,
        )
        artifact_id = train_resp.json()["artifact_id"]
        resp = await client.get(f"/api/v1/ml/models/{artifact_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == artifact_id

    async def test_train_no_stored_runs(self, client):
        headers = await _auth(client)
        resp = await client.post(
            "/api/v1/ml/train",
            json={
                "column_type": "C18",
                "model_type": "sklearn",
                "use_stored_runs": True,
            },
            headers=headers,
        )
        assert resp.status_code == 400
