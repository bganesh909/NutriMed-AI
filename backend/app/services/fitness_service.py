"""
Fitness / workout plan generation service.

Generates plans by calling the local LLM (Ollama) and adapts based on
biomarker data (e.g., lower intensity if anemic, joint-friendly if high uric acid).
"""

import json
import logging
from datetime import UTC

from app.repositories.workout_plan_repository import WorkoutPlanRepository
from app.services import llm_client
from app.services.generation_metrics import (
    OUTCOME_FALLBACK,
    OUTCOME_LLM_REPAIRED,
    OUTCOME_LLM_VERIFIED,
    record_generation_async,
)
from app.services.lab_interpretation_service import LabInterpretationService
from app.services.plan_grounding import (
    format_exercise_catalogue,
    select_exercises,
    verify_workout_plan,
)
from app.services.workout_templates import build_fallback_days

logger = logging.getLogger("nutrimed.fitness")


# Biomarker-based adaptations: marker -> condition -> adaptation advice
_BIOMARKER_ADAPTATIONS: dict[str, list[dict]] = {
    "hemoglobin": [
        {
            "condition": lambda v, g: v < (12.0 if g == "female" else 13.0),
            "adaptation": (
                "Reduce high-intensity exercises. Focus on low-to-moderate intensity until hemoglobin normalises."
            ),
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
            "adaptation": (
                "Include regular aerobic exercise (walking, cycling). Monitor blood sugar before/after exercise."
            ),
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
        biomarkers: dict[str, float] | None = None,
    ) -> dict:
        gender = (user_profile.get("gender") or "male").lower()
        age = user_profile.get("age") or 30
        weight = user_profile.get("weight") or user_profile.get("weight_kg") or 70

        adaptations: list[str] = list(conditions or [])
        if biomarkers:
            adaptations.extend(self.get_biomarker_adaptations(biomarkers, gender))

        adaptations_str = "; ".join(adaptations) if adaptations else "none"

        # Derive the rule-engine view of the biomarkers so exercise selection can
        # cap intensity clinically (e.g. anemia limits difficulty) rather than
        # relying on the model to respect a sentence in the prompt.
        rule_engine = None
        if biomarkers:
            try:
                rule_engine = LabInterpretationService().interpret(dict(biomarkers), gender)
            except Exception:
                logger.warning("Rule engine failed during workout grounding", exc_info=True)

        catalogue = format_exercise_catalogue(select_exercises(difficulty=difficulty, rule_engine=rule_engine))

        prompt = (
            f"Create a {days_per_week}-day weekly workout plan for a {age}-year-old {gender} "
            f"weighing {weight}kg.\n"
            f"Goal: {goal}. Difficulty: {difficulty}.\n"
            f"Health conditions / adaptations: {adaptations_str}.\n\n"
            f"You may ONLY use exercises from this catalogue, by exact name. It "
            f"is already filtered for this person's level and lab findings:\n"
            f"{catalogue}\n\n"
            "RULES:\n"
            "- Use exact names from the catalogue. Never invent an exercise.\n"
            "- Do NOT write form or technique instructions; they come from the "
            "catalogue and anything you write is discarded.\n"
            "- Give sets, reps and rest for each exercise, plus a warm-up and "
            "cool-down per day.\n\n"
            "Return valid JSON with this structure:\n"
            '[{"day_name": "Day 1 - Push", "warm_up": "...", "cool_down": "...", '
            '"exercises": [{"name": "Push-ups", '
            '"sets": 4, "reps": "8-10", "rest": "90s"}]}]'
        )

        plan_data = await self._call_llm(prompt)

        raw_days = plan_data if isinstance(plan_data, list) else []
        verified_days, warnings = verify_workout_plan(raw_days)
        if warnings:
            logger.warning("Workout plan verification for user %s: %s", user_id, warnings[:10])
        outcome = (
            OUTCOME_LLM_REPAIRED
            if (verified_days and warnings)
            else OUTCOME_LLM_VERIFIED
            if verified_days
            else OUTCOME_FALLBACK
        )
        if not verified_days:
            # Unusable or no answer from the model: serve the deterministic
            # template, as the report workers do, rather than an empty plan.
            logger.info("Workout plan fell back to templates for user %s", user_id)
            verified_days, _ = verify_workout_plan(
                build_fallback_days(
                    age=age,
                    gender=gender,
                    weight_kg=weight,
                    height_cm=user_profile.get("height") or user_profile.get("height_cm") or 170,
                    fitness_level=difficulty,
                    goal=goal,
                    days_per_week=days_per_week,
                    conditions=conditions or [],
                )
            )

        plan_doc = {
            "user_id": user_id,
            "goal": goal,
            "difficulty": difficulty,
            "days_per_week": days_per_week,
            "days": verified_days,
            "plan": verified_days,
            "verified": True,
            "adaptations": adaptations,
            "notes": f"Generated for {goal} / {difficulty}. Adaptations: {adaptations_str}.",
        }
        from datetime import datetime

        plan_doc["created_at"] = datetime.now(UTC)
        saved = await self.workout_plan_repo.create(plan_doc)
        await record_generation_async(
            self.workout_plan_repo.db,
            kind="workout",
            outcome=outcome,
            user_id=user_id,
            dropped=warnings,
            model=llm_client.model_name(),
        )
        return saved

    async def _call_llm(self, prompt: str) -> list | str:
        """Ask the configured model and parse the JSON array in its answer."""
        try:
            text = await llm_client.complete(prompt)
        except llm_client.LLMError as exc:
            # Treated like an unusable answer: the caller serves the template
            # plan and records the fallback, as the report workers do, rather
            # than failing the request because the model is slow or down.
            logger.warning("LLM call failed: %s", exc)
            return ""
        try:
            start = text.index("[")
            end = text.rindex("]") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return text
