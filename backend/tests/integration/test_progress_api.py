"""
Integration tests for /api/v1/progress endpoints.

Tests: log progress, retrieve history, get single entry.
"""

import pytest
from httpx import AsyncClient
from bson import ObjectId


@pytest.mark.asyncio
class TestProgressLog:
    async def test_create_progress_entry(self, client: AsyncClient, auth_headers, test_user):
        resp = await client.post(
            "/api/v1/progress/",
            headers=auth_headers,
            json={
                "date": "2026-06-15",
                "weight": 74.5,
                "body_fat_pct": 18.0,
                "measurements": {"waist": 82.0, "chest": 100.0},
                "biomarker_snapshot": {"hemoglobin": 14.5},
                "notes": "Post-workout measurement",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["weight"] == 74.5
        assert data["body_fat_pct"] == 18.0
        assert data["measurements"]["waist"] == 82.0
        assert "id" in data

    async def test_create_minimal_progress(self, client: AsyncClient, auth_headers, test_user):
        resp = await client.post(
            "/api/v1/progress/",
            headers=auth_headers,
            json={"weight": 75.0},
        )
        assert resp.status_code == 201
        assert resp.json()["weight"] == 75.0

    async def test_create_without_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/progress/",
            json={"weight": 75.0},
        )
        assert resp.status_code in (401, 403)

    async def test_invalid_weight(self, client: AsyncClient, auth_headers, test_user):
        resp = await client.post(
            "/api/v1/progress/",
            headers=auth_headers,
            json={"weight": 5.0},  # below 10, validation should fail
        )
        assert resp.status_code == 422

    async def test_invalid_body_fat(self, client: AsyncClient, auth_headers, test_user):
        resp = await client.post(
            "/api/v1/progress/",
            headers=auth_headers,
            json={"body_fat_pct": 85.0},  # above 70, validation should fail
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestProgressHistory:
    async def test_empty_history(self, client: AsyncClient, auth_headers, test_user):
        resp = await client.get("/api/v1/progress/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"] == []
        assert data["total"] == 0

    async def test_history_with_entries(self, client: AsyncClient, auth_headers, test_user):
        # Create three entries
        for i, w in enumerate([75.0, 74.5, 74.0]):
            await client.post(
                "/api/v1/progress/",
                headers=auth_headers,
                json={"date": f"2026-06-{15 + i:02d}", "weight": w},
            )

        resp = await client.get("/api/v1/progress/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["entries"]) == 3

    async def test_history_trends(self, client: AsyncClient, auth_headers, test_user):
        await client.post(
            "/api/v1/progress/",
            headers=auth_headers,
            json={"date": "2026-06-01", "weight": 76.0},
        )
        await client.post(
            "/api/v1/progress/",
            headers=auth_headers,
            json={"date": "2026-06-15", "weight": 74.0},
        )

        resp = await client.get("/api/v1/progress/", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 2
        if "weight_change" in data.get("trends", {}):
            assert data["trends"]["weight_change"] == pytest.approx(-2.0, abs=0.01)

    async def test_history_pagination(self, client: AsyncClient, auth_headers, test_user):
        for i in range(5):
            await client.post(
                "/api/v1/progress/",
                headers=auth_headers,
                json={"date": f"2026-06-{10 + i:02d}", "weight": 75.0 - i * 0.5},
            )

        resp = await client.get("/api/v1/progress/?limit=2&skip=0", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) == 2
        assert data["total"] == 5

    async def test_get_single_entry(self, client: AsyncClient, auth_headers, test_user):
        create_resp = await client.post(
            "/api/v1/progress/",
            headers=auth_headers,
            json={"date": "2026-06-20", "weight": 73.5, "notes": "Morning weigh-in"},
        )
        entry_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/progress/{entry_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["weight"] == 73.5
        assert resp.json()["notes"] == "Morning weigh-in"

    async def test_get_nonexistent_entry(self, client: AsyncClient, auth_headers, test_user):
        fake_id = str(ObjectId())
        resp = await client.get(f"/api/v1/progress/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404
