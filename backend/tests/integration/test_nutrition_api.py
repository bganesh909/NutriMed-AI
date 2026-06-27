"""
Integration tests for /api/v1/nutrition endpoints.

Tests: calculate nutrition, generate diet plan.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestNutritionCalculate:
    async def test_calculate_with_body_params(self, client: AsyncClient, auth_headers, test_user):
        resp = await client.post(
            "/api/v1/nutrition/calculate",
            headers=auth_headers,
            json={
                "weight_kg": 75,
                "height_cm": 175,
                "age": 30,
                "gender": "male",
                "activity_level": "moderate",
                "goal": "maintenance",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "bmr" in data
        assert "tdee" in data
        assert "bmi" in data
        assert "bmi_category" in data
        assert "target_calories" in data
        assert "macros" in data
        assert data["macros"]["protein_g"] > 0
        assert data["macros"]["carbs_g"] > 0
        assert data["macros"]["fat_g"] > 0

    async def test_calculate_uses_profile_defaults(self, client: AsyncClient, auth_headers, test_user):
        """When no body params provided, uses profile values."""
        resp = await client.post(
            "/api/v1/nutrition/calculate",
            headers=auth_headers,
            json={"goal": "maintenance"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["bmi"] > 0

    async def test_calculate_get_endpoint(self, client: AsyncClient, auth_headers, test_user):
        resp = await client.get(
            "/api/v1/nutrition/calculate",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "bmr" in data
        assert "macros" in data

    async def test_calculate_weight_loss_goal(self, client: AsyncClient, auth_headers, test_user):
        maint_resp = await client.post(
            "/api/v1/nutrition/calculate",
            headers=auth_headers,
            json={"weight_kg": 80, "height_cm": 175, "age": 30, "gender": "male", "goal": "maintenance"},
        )
        loss_resp = await client.post(
            "/api/v1/nutrition/calculate",
            headers=auth_headers,
            json={"weight_kg": 80, "height_cm": 175, "age": 30, "gender": "male", "goal": "weight_loss"},
        )
        assert loss_resp.json()["target_calories"] < maint_resp.json()["target_calories"]

    async def test_calculate_without_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/nutrition/calculate",
            json={"goal": "maintenance"},
        )
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
class TestDietPlanGeneration:
    async def test_generate_diet_plan(self, client: AsyncClient, auth_headers, test_user):
        """
        Calls the diet plan generation endpoint.
        This will fail with 503 if Ollama is not running, which is expected.
        """
        resp = await client.post(
            "/api/v1/nutrition/generate-diet",
            headers=auth_headers,
            json={
                "goal": "maintenance",
                "dietary_restrictions": ["vegetarian"],
                "allergies": ["peanuts"],
            },
        )
        # 201 if Ollama is available, 503 if not
        assert resp.status_code in (201, 503)

    async def test_generate_diet_without_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/nutrition/generate-diet",
            json={"goal": "maintenance"},
        )
        assert resp.status_code in (401, 403)
