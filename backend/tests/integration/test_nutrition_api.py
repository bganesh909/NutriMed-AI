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
    """
    The LLM is stubbed here on purpose: these assert the grounding contract,
    not the model. Calling a real 7B model would make the suite slow,
    non-deterministic and dependent on Ollama being up.
    """

    @staticmethod
    def _stub_llm(response):
        async def _call(self, prompt: str):
            return response
        return _call

    async def test_macros_are_recomputed_from_the_food_database(
        self, client: AsyncClient, auth_headers, monkeypatch
    ):
        from app.data.food_database import FOOD_DATABASE
        from app.services.nutrition_service import NutritionService

        oats = next(f for f in FOOD_DATABASE if f["name"] == "Oats (dry)")
        chicken = next(f for f in FOOD_DATABASE if f["name"] == "Chicken Breast (cooked)")

        # A nutritionally sound day, so the adequacy gate keeps it -- but the
        # model reports a wildly wrong calorie figure that must be discarded.
        monkeypatch.setattr(
            NutritionService, "_call_llm",
            self._stub_llm([
                {"day": "Monday", "meals": [
                    {"name": "Breakfast", "time": "8:00 AM", "foods": [
                        {"name": "Oats (dry)", "quantity_g": 100, "calories": 5},
                        {"name": "Banana", "quantity_g": 150},
                    ]},
                    {"name": "Mid-Morning Snack", "time": "11:00 AM", "foods": [
                        {"name": "Almonds", "quantity_g": 40},
                    ]},
                    {"name": "Lunch", "time": "1:00 PM", "foods": [
                        {"name": "Chicken Breast (cooked)", "quantity_g": 200},
                        {"name": "Brown Rice (cooked)", "quantity_g": 300},
                        {"name": "Broccoli (cooked)", "quantity_g": 150},
                    ]},
                    {"name": "Evening Snack", "time": "5:00 PM", "foods": [
                        {"name": "Paneer", "quantity_g": 100},
                    ]},
                    {"name": "Dinner", "time": "8:00 PM", "foods": [
                        {"name": "Chicken Breast (cooked)", "quantity_g": 200},
                        {"name": "Brown Rice (cooked)", "quantity_g": 200},
                        {"name": "Olive Oil", "quantity_g": 15},
                    ]},
                ]},
            ]),
        )

        resp = await client.post(
            "/api/v1/nutrition/generate-diet",
            headers=auth_headers,
            json={"goal": "maintenance"},
        )
        assert resp.status_code == 201
        body = resp.json()

        meals = body["meal_plan"][0]["meals"]
        breakfast = next(m for m in meals if m["name"] == "Breakfast")
        item = breakfast["foods"][0]
        assert item["calories"] == pytest.approx(oats["calories"], abs=0.2)
        assert item["calories"] != 5

        lunch = next(m for m in meals if m["name"] == "Lunch")
        chicken_item = next(f for f in lunch["foods"] if f["name"] == chicken["name"])
        assert chicken_item["protein_g"] == pytest.approx(chicken["protein_g"] * 2, abs=0.2)

    async def test_hallucinated_food_is_dropped(
        self, client: AsyncClient, auth_headers, monkeypatch
    ):
        from app.services.nutrition_service import NutritionService

        monkeypatch.setattr(
            NutritionService, "_call_llm",
            self._stub_llm([
                {"day": "Monday", "meals": [
                    {"name": "Breakfast", "foods": [
                        {"name": "Oats (dry)", "quantity_g": 100},
                        {"name": "Unicorn Steak", "quantity_g": 200},
                        {"name": "Banana", "quantity_g": 150},
                    ]},
                    {"name": "Lunch", "foods": [
                        {"name": "Chicken Breast (cooked)", "quantity_g": 250},
                        {"name": "Brown Rice (cooked)", "quantity_g": 300},
                        {"name": "Broccoli (cooked)", "quantity_g": 150},
                    ]},
                    {"name": "Dinner", "foods": [
                        {"name": "Paneer", "quantity_g": 120},
                        {"name": "Brown Rice (cooked)", "quantity_g": 250},
                        {"name": "Olive Oil", "quantity_g": 15},
                        {"name": "Almonds", "quantity_g": 40},
                    ]},
                ]},
            ]),
        )

        resp = await client.post(
            "/api/v1/nutrition/generate-diet",
            headers=auth_headers,
            json={"goal": "maintenance"},
        )
        assert resp.status_code == 201
        names = [
            f["name"]
            for day in resp.json()["meal_plan"]
            for meal in day["meals"]
            for f in meal["foods"]
        ]
        assert "Unicorn Steak" not in names

    async def test_unusable_response_falls_back_to_template_plan(
        self, client: AsyncClient, auth_headers, monkeypatch
    ):
        """A failed model must still leave the user with a real plan."""
        from app.services.nutrition_service import NutritionService

        monkeypatch.setattr(
            NutritionService, "_call_llm", self._stub_llm("not json at all")
        )

        resp = await client.post(
            "/api/v1/nutrition/generate-diet",
            headers=auth_headers,
            json={"goal": "maintenance"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["meal_plan"], "fallback must produce a plan"
        assert body["meal_plan"][0]["meals"]

    async def test_generate_diet_without_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/nutrition/generate-diet",
            json={"goal": "maintenance"},
        )
        assert resp.status_code in (401, 403)
