"""API tests for multi-compound method optimization."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestMultiCompound:
    async def test_suggest_multi(self, client):
        resp = await client.post(
            "/api/v1/methods/suggest-multi",
            json={
                "smiles_list": ["CCO", "c1ccccc1", "CC(=O)O"],
                "gradient_time_min": 25.0,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data["per_compound"]) == 3
        assert "gradient" in data
        assert "resolution_matrix" in data
        # 3 compounds -> 3 pairs (C(3,2) = 3)
        assert len(data["resolution_matrix"]) == 3
        # Each resolution entry has the right fields
        for r in data["resolution_matrix"]:
            assert "compound_a" in r
            assert "compound_b" in r
            assert "resolution" in r
            assert "co_elution_risk" in r

    async def test_suggest_multi_single_compound(self, client):
        resp = await client.post(
            "/api/v1/methods/suggest-multi",
            json={"smiles_list": ["CCO"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["per_compound"]) == 1
        assert len(data["resolution_matrix"]) == 0  # no pairs

    async def test_suggest_multi_invalid_smiles(self, client):
        resp = await client.post(
            "/api/v1/methods/suggest-multi",
            json={"smiles_list": ["CCO", "invalid!!!"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["per_compound"][1]["error"] == "invalid SMILES"
