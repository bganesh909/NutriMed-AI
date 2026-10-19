"""
When the model times out or is down, plan generation falls back to the
deterministic templates (as the report workers do) instead of failing with 503,
and records the fallback so it is visible in generation metrics.
"""

import httpx
import pytest
from httpx import AsyncClient

NON_VEGETARIAN = ("chicken", "fish", "egg", "mutton", "prawn", "meat", "salmon", "tuna", "beef", "pork")


@pytest.fixture()
def llm_times_out(monkeypatch):
    """Make every Ollama call time out; other requests (the test client's) pass through."""
    original_post = httpx.AsyncClient.post

    async def _post(self, url, *args, **kwargs):
        if "/api/generate" in str(url):
            raise httpx.ReadTimeout("model took too long")
        return await original_post(self, url, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "post", _post)


@pytest.mark.asyncio
async def test_diet_falls_back_and_respects_vegetarian(client: AsyncClient, test_db, auth_headers, llm_times_out):
    resp = await client.post(
        "/api/v1/nutrition/generate-diet",
        json={"goal": "fat_loss", "dietary_restrictions": ["vegetarian"], "allergies": []},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    plan = resp.json()
    foods = [
        food["name"].lower()
        for day in plan["meal_plan"]
        for meal in day.get("meals", [])
        for food in meal.get("foods", [])
    ]
    assert foods, "fallback plan should contain meals"
    assert not [f for f in foods if any(word in f for word in NON_VEGETARIAN)]

    metric = await test_db["generation_metrics"].find_one({"kind": "diet"})
    assert metric["outcome"] == "template_fallback"


@pytest.mark.asyncio
async def test_workout_falls_back_instead_of_saving_empty_plan(
    client: AsyncClient, test_db, auth_headers, llm_times_out
):
    resp = await client.post(
        "/api/v1/fitness/generate-workout",
        json={"goal": "fat_loss", "difficulty": "beginner", "conditions": [], "use_biomarkers": False},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    days = resp.json()["days"]
    assert days and any(day.get("exercises") for day in days)

    metric = await test_db["generation_metrics"].find_one({"kind": "workout"})
    assert metric["outcome"] == "template_fallback"
