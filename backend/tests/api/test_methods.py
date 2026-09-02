"""API tests for method endpoints."""
from __future__ import annotations

import pytest


async def _auth(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "meth@test.com", "password": "testpass123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
class TestMethodSuggestion:
    async def test_suggest_from_smiles(self, client):
        resp = await client.post(
            "/api/v1/methods/suggest",
            json={"smiles": "CC(=O)O", "ionization_mode": "ESI+"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "column" in data
        assert "ph" in data
        assert "additive" in data
        assert "gradient" in data
        assert "descriptors" in data
        assert data["column"]["column_type"] in ("C18", "HILIC", "ion_pair", "phenyl")

    async def test_suggest_no_input(self, client):
        resp = await client.post("/api/v1/methods/suggest", json={})
        assert resp.status_code == 400

    async def test_suggest_invalid_smiles(self, client):
        resp = await client.post(
            "/api/v1/methods/suggest", json={"smiles": "invalid!!!"}
        )
        assert resp.status_code == 400

    async def test_suggest_gradient_has_table(self, client):
        resp = await client.post(
            "/api/v1/methods/suggest", json={"smiles": "CCO"}
        )
        data = resp.json()
        assert len(data["gradient"]["gradient_table"]) >= 3


@pytest.mark.asyncio
class TestGradientSimulation:
    async def test_simulate_gradient(self, client):
        resp = await client.post(
            "/api/v1/methods/gradient/simulate",
            json={
                "gradient_table": [
                    {"time_s": 0, "percent_b": 5},
                    {"time_s": 60, "percent_b": 5},
                    {"time_s": 1200, "percent_b": 95},
                    {"time_s": 1320, "percent_b": 95},
                ],
                "flow_rate_ml_min": 0.4,
                "logp": 2.0,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["predicted_rt_s"] > 0
        assert data["method"] == "heuristic"


@pytest.mark.asyncio
class TestChromatogram:
    async def test_simulate_chromatogram(self, client):
        resp = await client.post(
            "/api/v1/methods/chromatogram",
            json={
                "peaks": [{"rt_s": 300, "width_s": 10, "height": 1.0, "label": "A"}],
                "total_time_s": 600,
                "n_points": 100,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data["times"]) == 100
        assert max(data["intensities"]) > 0.5


@pytest.mark.asyncio
class TestMethodCRUD:
    async def test_create_and_get_method(self, client):
        headers = await _auth(client)
        create = await client.post(
            "/api/v1/methods",
            json={
                "name": "Test C18 method",
                "column_type": "C18",
                "ph": 2.7,
                "mobile_phase_a": "water + 0.1% formic acid",
                "mobile_phase_b": "acetonitrile",
                "gradient_table": [
                    {"time_s": 0, "percent_b": 5},
                    {"time_s": 1200, "percent_b": 95},
                ],
                "flow_rate_ml_min": 0.4,
            },
            headers=headers,
        )
        assert create.status_code == 201, create.text
        mid = create.json()["id"]
        resp = await client.get(f"/api/v1/methods/{mid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["column_type"] == "C18"

    async def test_list_methods(self, client):
        headers = await _auth(client)
        await client.post(
            "/api/v1/methods",
            json={"column_type": "C18"},
            headers=headers,
        )
        resp = await client.get("/api/v1/methods", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_delete_method(self, client):
        headers = await _auth(client)
        create = await client.post(
            "/api/v1/methods",
            json={"column_type": "C18"},
            headers=headers,
        )
        mid = create.json()["id"]
        resp = await client.delete(f"/api/v1/methods/{mid}", headers=headers)
        assert resp.status_code == 204
