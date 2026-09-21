"""Security regression tests: auth coverage, owner scoping, token lifecycle."""
from __future__ import annotations

import pytest
from sqlalchemy import update

from tests.api.conftest import register_and_login
from tests.fixtures import get_fixture_csv_bytes

# ---------------------------------------------------------------------------
# Unauthenticated requests must be rejected on compute/lookup endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAuthRequired:
    @pytest.mark.parametrize("path", [
        "/api/v1/methods/van-deemter",
        "/api/v1/methods/suggest",
        "/api/v1/methods/gradient/simulate",
        "/api/v1/methods/chromatogram",
        "/api/v1/methods/optimize-gradient",
        "/api/v1/methods/resolution-map/1d",
        "/api/v1/methods/resolution-map/2d",
        "/api/v1/methods/ternary-optimize",
        "/api/v1/methods/method-transfer",
    ])
    async def test_post_compute_endpoints_require_auth(self, client, path):
        resp = await client.post(path, json={})
        assert resp.status_code == 401

    @pytest.mark.parametrize("path", [
        "/api/v1/methods/retention-models",
        "/api/v1/methods/buffers/list",
        "/api/v1/compounds/pubchem/lookup?name=aspirin",
        "/api/v1/compounds/search/multi?name=test",
        "/api/v1/compounds/depiction?smiles=CCO",
        "/api/v1/compounds/pka-plot?smiles=CCO",
    ])
    async def test_get_lookup_endpoints_require_auth(self, client, path):
        resp = await client.get(path)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Refresh-token lifecycle: rotation, revocation, legacy rejection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestRefreshTokenLifecycle:
    async def test_refresh_rotates_and_old_token_fails(self, client):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "rot@test.com", "password": "testpass123"},
        )
        assert resp.status_code == 201
        refresh_token = resp.json()["refresh_token"]

        # First refresh succeeds and rotates the session
        r1 = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert r1.status_code == 200
        new_refresh = r1.json()["refresh_token"]
        assert new_refresh != refresh_token

        # Reuse of the rotated (now revoked) token must fail
        r2 = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert r2.status_code == 401

        # The new token works
        r3 = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": new_refresh}
        )
        assert r3.status_code == 200

    async def test_logout_revokes_refresh(self, client):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "logout@test.com", "password": "testpass123"},
        )
        refresh_token = resp.json()["refresh_token"]

        out = await client.post(
            "/api/v1/auth/logout", json={"refresh_token": refresh_token}
        )
        assert out.status_code == 204

        r = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert r.status_code == 401

    async def test_logout_is_idempotent_for_bad_token(self, client):
        r = await client.post(
            "/api/v1/auth/logout", json={"refresh_token": "garbage"}
        )
        assert r.status_code == 204

    async def test_legacy_refresh_token_without_jti_rejected(self, client):
        """Refresh tokens minted before session tracking carry no jti."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "legacy@test.com", "password": "testpass123"},
        )
        user_id = resp.json()["user"]["id"]

        from app.auth.jwt import create_refresh_token
        legacy = create_refresh_token(str(user_id))  # no jti
        r = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": legacy}
        )
        assert r.status_code == 401

    async def test_malformed_refresh_payload_rejected(self, client):
        r = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "not-a-jwt"}
        )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Deactivated users lose access (access + refresh)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestDeactivatedUser:
    async def test_inactive_user_blocked(self, client, db_engine):
        tokens_resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "gone@test.com", "password": "testpass123"},
        )
        data = tokens_resp.json()
        access = data["access_token"]
        refresh_token = data["refresh_token"]
        user_id = data["user"]["id"]

        # Works while active
        ok = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"}
        )
        assert ok.status_code == 200

        # Deactivate directly in the DB
        import uuid as _uuid

        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        from app.models.user import User
        sm = async_sessionmaker(bind=db_engine, class_=AsyncSession)
        async with sm() as s:
            await s.execute(
                update(User)
                .where(User.id == _uuid.UUID(user_id))
                .values(is_active=False)
            )
            await s.commit()

        # Access token now rejected (403 — authenticated but deactivated)
        r1 = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"}
        )
        assert r1.status_code == 403

        # Refresh also rejected
        r2 = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert r2.status_code == 401

        # Login rejected
        r3 = await client.post(
            "/api/v1/auth/login",
            json={"email": "gone@test.com", "password": "testpass123"},
        )
        assert r3.status_code == 403


# ---------------------------------------------------------------------------
# Last-admin protection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestLastAdmin:
    async def test_cannot_demote_last_admin(self, client, db_engine):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "admin@test.com", "password": "testpass123"},
        )
        data = resp.json()
        user_id = data["user"]["id"]
        headers = {"Authorization": f"Bearer {data['access_token']}"}

        # Promote to admin directly in DB
        import uuid as _uuid

        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        from app.models.user import User
        sm = async_sessionmaker(bind=db_engine, class_=AsyncSession)
        async with sm() as s:
            await s.execute(
                update(User)
                .where(User.id == _uuid.UUID(user_id))
                .values(is_admin=True)
            )
            await s.commit()

        # Demoting the only admin must fail
        r = await client.put(
            f"/api/v1/admin/users/{user_id}",
            json={"is_admin": False},
            headers=headers,
        )
        assert r.status_code == 400

    async def test_non_admin_cannot_touch_admin_routes(self, client):
        headers = await register_and_login(client, "plain@test.com")
        r = await client.get("/api/v1/admin/users", headers=headers)
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Cross-user scoping: models must not be visible to other users
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestOwnerScoping:
    async def _train_model(self, client, headers) -> str:
        resp = await client.post(
            "/api/v1/ml/train/csv",
            params={"column_type": "C18", "model_type": "sklearn"},
            files={"file": ("compounds.csv", get_fixture_csv_bytes(), "text/csv")},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()["artifact_id"]

    async def test_cross_user_model_get_and_delete(self, client):
        headers_a = await register_and_login(client, "owner@test.com")
        artifact_id = await self._train_model(client, headers_a)

        headers_b = await register_and_login(client, "other@test.com")

        # Other user's model is invisible in their list
        listed = await client.get("/api/v1/ml/models", headers=headers_b)
        assert listed.status_code == 200
        assert all(m["id"] != artifact_id for m in listed.json())

        # Direct access denied (404 — no enumeration)
        got = await client.get(
            f"/api/v1/ml/models/{artifact_id}", headers=headers_b
        )
        assert got.status_code == 404

        # Direct delete denied
        deleted = await client.delete(
            f"/api/v1/ml/models/{artifact_id}", headers=headers_b
        )
        assert deleted.status_code == 404

        # Owner still sees it
        still = await client.get(
            f"/api/v1/ml/models/{artifact_id}", headers=headers_a
        )
        assert still.status_code == 200


# ---------------------------------------------------------------------------
# SVG upload rejection (stored-XSS defence)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestUploadValidation:
    async def test_svg_logo_rejected(self, client, db_engine):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "svgadmin@test.com", "password": "testpass123"},
        )
        data = resp.json()
        user_id = data["user"]["id"]
        headers = {"Authorization": f"Bearer {data['access_token']}"}

        import uuid as _uuid

        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        from app.models.user import User
        sm = async_sessionmaker(bind=db_engine, class_=AsyncSession)
        async with sm() as s:
            await s.execute(
                update(User)
                .where(User.id == _uuid.UUID(user_id))
                .values(is_admin=True)
            )
            await s.commit()

        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        r = await client.post(
            "/api/v1/admin/logo",
            files={"file": ("logo.svg", svg, "image/svg+xml")},
            headers=headers,
        )
        assert r.status_code == 400

    async def test_spoofed_mime_rejected(self, client, db_engine):
        """A non-image body with an image Content-Type must be rejected."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "spoof@test.com", "password": "testpass123"},
        )
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        r = await client.post(
            "/api/v1/auth/profile/picture",
            files={"file": ("pic.png", b"not an image at all", "image/png")},
            headers=headers,
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Van Deemter analyte-size modes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestVanDeemterAnalytes:
    _BASE = {
        "length_mm": 100.0,
        "inner_diameter_mm": 2.1,
        "particle_size_um": 1.7,
        "particle_type": "fully_porous",
        "solvent_b": "acetonitrile",
        "fraction_b": 0.5,
        "temperature_c": 40.0,
        # High limit so small-MW optima aren't pressure-capped (which would
        # legitimately raise H above the unconstrained h_min).
        "max_pressure_bar": 2000.0,
    }

    async def test_typical_default_no_mw_needed(self, client):
        headers = await register_and_login(client, "vd1@test.com")
        r = await client.post(
            "/api/v1/methods/van-deemter", json=self._BASE, headers=headers
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["analytes"]["source"] == "typical"
        assert data["analytes"]["mw_used"] == pytest.approx(300.0)
        assert data["flow_window"] is None
        assert data["optimum_efficiency"]["flow_ml_min"] > 0

    async def test_mz_mode_converts_to_mw(self, client):
        headers = await register_and_login(client, "vd2@test.com")
        r = await client.post(
            "/api/v1/methods/van-deemter",
            json={**self._BASE, "analyte_mode": "mz", "mz": 610.28, "charge": 2},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        mw = r.json()["analytes"]["mw_used"]
        assert mw == pytest.approx(2 * 610.28 - 2 * 1.007276, abs=0.1)

    async def test_mw_range_gives_window_and_band(self, client):
        headers = await register_and_login(client, "vd3@test.com")
        r = await client.post(
            "/api/v1/methods/van-deemter",
            json={**self._BASE, "analyte_mode": "mw_range",
                  "mw_min": 150.0, "mw_max": 800.0},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["flow_window"] is not None
        fw = data["flow_window"]
        assert fw["low_flow_ml_min"] < fw["high_flow_ml_min"]
        # Curve points carry the band
        assert all("h_low_um" in p and "h_high_um" in p for p in data["curve"])
        assert all(p["h_low_um"] <= p["h_um"] <= p["h_high_um"] for p in data["curve"])

    async def test_hmin_is_mw_independent(self, client):
        """h_min / N at optimum must not depend on analyte MW."""
        headers = await register_and_login(client, "vd4@test.com")
        h_mins = []
        for mw in (150.0, 300.0, 1200.0):
            r = await client.post(
                "/api/v1/methods/van-deemter",
                json={**self._BASE, "analyte_mode": "mw", "analyte_mw": mw},
                headers=headers,
            )
            assert r.status_code == 200
            h_mins.append(r.json()["optimum_efficiency"]["h_um"])
        assert h_mins[0] == pytest.approx(h_mins[1])
        assert h_mins[1] == pytest.approx(h_mins[2])

    async def test_dm_override_ignores_mw(self, client):
        headers = await register_and_login(client, "vd5@test.com")
        r = await client.post(
            "/api/v1/methods/van-deemter",
            json={**self._BASE, "analyte_mode": "mw",
                  "analyte_mw": 5000.0, "dm_m2_s": 1e-9},
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["analytes"]["source"] == "dm_override"
        assert data["dm_m2_s"] == pytest.approx(1e-9)


# ---------------------------------------------------------------------------
# Method compound append — POST /methods/{id}/compounds
# ---------------------------------------------------------------------------

_METHOD_PAYLOAD = {
    "name": "Add-Compound Test Method",
    "column_type": "C18",
    "ph": 2.7,
    "flow_rate_ml_min": 0.4,
    "temperature_c": 30.0,
    "compounds_smiles": ["CN1C=NC2=C1C(=O)N(C(=O)N2C)C"],
    "compound_names": ["Caffeine"],
}


class TestMethodCompounds:
    async def _make_method(self, client, headers) -> str:
        r = await client.post("/api/v1/methods", json=_METHOD_PAYLOAD, headers=headers)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    async def test_owner_can_add_compound(self, client):
        headers = await register_and_login(client, "mc1@test.com")
        mid = await self._make_method(client, headers)
        r = await client.post(
            f"/api/v1/methods/{mid}/compounds",
            json={"smiles": "Nc1ncnc2[nH]cnc12", "name": "Adenine"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["compounds_smiles"]) == 2
        assert data["compound_names"][-1] == "Adenine"
        assert len(data["compound_ids"]) == 2
        assert data["compound_ids"][-1] is None

    async def test_non_owner_forbidden(self, client):
        owner = await register_and_login(client, "mc2@test.com")
        mid = await self._make_method(client, owner)
        other = await register_and_login(client, "mc3@test.com")
        r = await client.post(
            f"/api/v1/methods/{mid}/compounds",
            json={"smiles": "Nc1ncnc2[nH]cnc12"},
            headers=other,
        )
        assert r.status_code == 403

    async def test_duplicate_is_idempotent(self, client):
        headers = await register_and_login(client, "mc4@test.com")
        mid = await self._make_method(client, headers)
        smiles = _METHOD_PAYLOAD["compounds_smiles"][0]
        r = await client.post(
            f"/api/v1/methods/{mid}/compounds",
            json={"smiles": smiles},
            headers=headers,
        )
        assert r.status_code == 200
        assert len(r.json()["compounds_smiles"]) == 1

    async def test_invalid_smiles_400(self, client):
        headers = await register_and_login(client, "mc5@test.com")
        mid = await self._make_method(client, headers)
        r = await client.post(
            f"/api/v1/methods/{mid}/compounds",
            json={"smiles": "not-a-smiles!!!"},
            headers=headers,
        )
        assert r.status_code == 400

    async def test_requires_auth(self, client):
        r = await client.post(
            "/api/v1/methods/00000000-0000-0000-0000-000000000000/compounds",
            json={"smiles": "CCO"},
        )
        assert r.status_code == 401

    async def test_compound_id_smiles_mismatch_400(self, client):
        headers = await register_and_login(client, "mc6@test.com")
        mid = await self._make_method(client, headers)
        cr = await client.post(
            "/api/v1/compounds",
            json={"smiles": "CCO", "name": "ethanol"},
            headers=headers,
        )
        assert cr.status_code in (200, 201), cr.text
        cid = cr.json()["id"]
        r = await client.post(
            f"/api/v1/methods/{mid}/compounds",
            json={"smiles": "Nc1ncnc2[nH]cnc12", "compound_id": cid},
            headers=headers,
        )
        assert r.status_code == 400

    async def test_compound_id_links_library_entry(self, client):
        headers = await register_and_login(client, "mc7@test.com")
        mid = await self._make_method(client, headers)
        cr = await client.post(
            "/api/v1/compounds",
            json={"smiles": "Nc1ncnc2[nH]cnc12", "name": "Adenine"},
            headers=headers,
        )
        cid = cr.json()["id"]
        r = await client.post(
            f"/api/v1/methods/{mid}/compounds",
            json={"smiles": "Nc1ncnc2[nH]cnc12", "name": "Adenine", "compound_id": cid},
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["compound_ids"][-1] == cid


# ---------------------------------------------------------------------------
# Method visibility (is_public) + PATCH + fork completeness
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMethodVisibility:
    async def _make_method(self, client, headers, public=False):
        r = await client.post(
            "/api/v1/methods",
            json={"name": "vis test", "column_type": "C18", "is_public": public},
            headers=headers,
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    async def test_private_method_hidden_from_other_users(self, client):
        owner = await register_and_login(client, "vis-owner@test.com")
        other = await register_and_login(client, "vis-other@test.com")
        mid = await self._make_method(client, owner, public=False)
        # Detail: 403
        r = await client.get(f"/api/v1/methods/{mid}", headers=other)
        assert r.status_code == 403
        # List: absent
        r = await client.get("/api/v1/methods?limit=200", headers=other)
        assert mid not in [m["id"] for m in r.json()]

    async def test_public_method_visible_to_other_users(self, client):
        owner = await register_and_login(client, "vis-owner2@test.com")
        other = await register_and_login(client, "vis-other2@test.com")
        mid = await self._make_method(client, owner, public=True)
        r = await client.get(f"/api/v1/methods/{mid}", headers=other)
        assert r.status_code == 200
        assert r.json()["is_public"] is True
        r = await client.get("/api/v1/methods?limit=200", headers=other)
        assert mid in [m["id"] for m in r.json()]

    async def test_patch_toggles_visibility(self, client):
        owner = await register_and_login(client, "vis-owner3@test.com")
        other = await register_and_login(client, "vis-other3@test.com")
        mid = await self._make_method(client, owner, public=False)
        # Owner flips to public via PATCH
        r = await client.patch(
            f"/api/v1/methods/{mid}", json={"is_public": True}, headers=owner
        )
        assert r.status_code == 200
        assert r.json()["is_public"] is True
        # Other user can now read it
        r = await client.get(f"/api/v1/methods/{mid}", headers=other)
        assert r.status_code == 200
        # Toggle back off
        r = await client.patch(
            f"/api/v1/methods/{mid}", json={"is_public": False}, headers=owner
        )
        assert r.status_code == 200
        r = await client.get(f"/api/v1/methods/{mid}", headers=other)
        assert r.status_code == 403

    async def test_patch_non_owner_forbidden(self, client):
        owner = await register_and_login(client, "vis-owner4@test.com")
        other = await register_and_login(client, "vis-other4@test.com")
        mid = await self._make_method(client, owner, public=True)
        r = await client.patch(
            f"/api/v1/methods/{mid}", json={"name": "hijack"}, headers=other
        )
        assert r.status_code == 403

    async def test_patch_updates_fields_in_place(self, client):
        headers = await register_and_login(client, "vis-owner5@test.com")
        mid = await self._make_method(client, headers)
        r = await client.patch(
            f"/api/v1/methods/{mid}",
            json={"name": "renamed", "ph": 7.4, "flow_rate_ml_min": 0.8},
            headers=headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == mid  # same method, not a copy
        assert body["name"] == "renamed"
        assert body["ph"] == 7.4
        assert body["flow_rate_ml_min"] == 0.8

    async def test_fork_preserves_compounds_and_metadata(self, client):
        owner = await register_and_login(client, "vis-owner6@test.com")
        forker = await register_and_login(client, "vis-forker@test.com")
        r = await client.post(
            "/api/v1/methods",
            json={
                "name": "rich method",
                "column_type": "C18",
                "is_public": True,
                "compounds_smiles": ["CCO"],
                "compound_names": ["ethanol"],
                "dwell_volume_ml": 1.1,
                "dead_volume_ml": 0.2,
                "retention_model": "lss",
                "retention_model_label": "LSS",
            },
            headers=owner,
        )
        assert r.status_code == 201, r.text
        mid = r.json()["id"]
        r = await client.post(f"/api/v1/methods/{mid}/fork", headers=forker)
        assert r.status_code == 201, r.text
        forked = r.json()
        assert forked["compounds_smiles"] == ["CCO"]
        assert forked["compound_names"] == ["ethanol"]
        assert forked["dwell_volume_ml"] == 1.1
        assert forked["dead_volume_ml"] == 0.2
        assert forked["retention_model"] == "lss"
        assert forked["is_public"] is False  # fork is a private copy
