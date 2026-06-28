"""
Fitness / workout plan generation service.

Generates plans by calling the local LLM (Ollama) and adapts based on
biomarker data (e.g., lower intensity if anemic, joint-friendly if high uric acid).
"""

import json
from typing import Optional

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.repositories.workout_plan_repository import WorkoutPlanRepository


# Biomarker-based adaptations: marker -> condition -> adaptation advice
_BIOMARKER_ADAPTATIONS: dict[str, list[dict]] = {
    "hemoglobin": [
        {
            "condition": lambda v, g: v < (12.0 if g == "female" else 13.0),
            "adaptation": "Reduce high-intensity exercises. Focus on low-to-moderate intensity until hemoglobin normalises.",
        },
    ],
    "tsh": [
        {
            "condition": lambda v, _: v > 4.5,
            "adaptation": "Include moderate exercise; avoid extreme endurance training. Prioritise recovery.",
        },
    ],
    "uric_acid": [
        {
            "condition": lambda v, g: v > (6.0 if g == "female" else 7.0),
            "adaptation": "Avoid high-impact exercises on joints. Prefer swimming, cycling, yoga.",
        },
    ],
    "creatinine": [
        {
            "condition": lambda v, g: v > (1.1 if g == "female" else 1.3),
            "adaptation": "Avoid excessive protein loading post-workout. Keep hydration high.",
        },
    ],
    "fasting_sugar": [
        {
            "condition": lambda v, _: v > 125,
            "adaptation": "Include regular aerobic exercise (walking, cycling). Monitor blood sugar before/after exercise.",
        },
    ],
    "hba1c": [
        {
            "condition": lambda v, _: v >= 5.7,
            "adaptation": "Prioritise resistance training and moderate cardio for glucose management.",
        },
    ],
}


class FitnessService:
    def __init__(self, workout_plan_repo: WorkoutPlanRepository) -> None:
        self.workout_plan_repo = workout_plan_repo

    def get_biomarker_adaptations(
        self,
        markers: dict[str, float],
        gender: str = "male",
    ) -> list[str]:
        """Return adaptation notes based on biomarker values."""
        adaptations: list[str] = []
        for marker_name, rules in _BIOMARKER_ADAPTATIONS.items():
            value = markers.get(marker_name)
            if value is None:
                continue
            for rule in rules:
                if rule["condition"](value, gender.lower()):
                    adaptations.append(rule["adaptation"])
        return adaptations

    async def generate_workout_plan(
        self,
        user_id: str,
        user_profile: dict,
        goal: str = "general_fitness",
        difficulty: str = "intermediate",
        days_per_week: int = 4,
        conditions: list[str] | None = None,
        biomarkers: Optional[dict[str, float]] = None,
    ) -> dict:
        gender = (user_profile.get("gender") or "male").lower()
        age = user_profile.get("age") or 30
        weight = user_profile.get("weight") or user_profile.get("weight_kg") or 70

        adaptations: list[str] = list(conditions or [])
        if biomarkers:
            adaptations.extend(self.get_biomarker_adaptations(biomarkers, gender))

        adaptations_str = "; ".join(adaptations) if adaptations else "none"

        prompt = (
            f"Create a {days_per_week}-day weekly workout plan for a {age}-year-old {gender} "
            f"weighing {weight}kg.\n"
            f"Goal: {goal}. Difficulty: {difficulty}.\n"
            f"Health conditions / adaptations: {adaptations_str}.\n\n"
            "For each day, provide the workout name and a list of exercises with sets, reps, "
            "and rest time. Return valid JSON with this structure:\n"
            '[{"day_name": "Day 1 - Push", "exercises": [{"name": "Bench Press", '
            '"sets": 4, "reps": "8-10", "rest": "90s"}]}]'
        )

        plan_data = await self._call_llm(prompt)

        plan_doc = {
            "user_id": user_id,
            "goal": goal,
            "difficulty": difficulty,
            "days_per_week": days_per_week,
            "plan": plan_data if isinstance(plan_data, list) else [{"raw": plan_data}],
            "adaptations": adaptations,
            "notes": f"Generated for {goal} / {difficulty}. Adaptations: {adaptations_str}.",
        }
        from datetime import datetime, timezone

        plan_doc["created_at"] = datetime.now(timezone.utc)
        saved = await self.workout_plan_repo.create(plan_doc)
        return saved

    async def _call_llm(self, prompt: str) -> list | str:
        url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = data.get("response", "")
                try:
                    start = text.index("[")
                    end = text.rindex("]") + 1
                    return json.loads(text[start:end])
                except (ValueError, json.JSONDecodeError):
                    return text
        except httpx.HTTPError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM service (Ollama) is not available. Please ensure it is running.",
            )
