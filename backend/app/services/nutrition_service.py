"""
Nutrition calculation and diet plan generation service.

Calculations:
- BMR via Mifflin-St Jeor equation
- TDEE from BMR * activity multiplier
- BMI from weight/height
- Body fat estimate via U.S. Navy method
- Macro split based on goal
"""

import contextlib
import logging
import math
from datetime import UTC

import httpx

from app.core.config import settings
from app.repositories.diet_plan_repository import DietPlanRepository
from app.services.diet_templates import build_fallback_meal_plan
from app.services.generation_metrics import (
    OUTCOME_FALLBACK,
    OUTCOME_LLM_REPAIRED,
    OUTCOME_LLM_VERIFIED,
    record_generation_async,
)
from app.services.plan_grounding import (
    clinical_priority_names,
    format_food_catalogue,
    plan_is_nutritionally_adequate,
    select_foods,
    verify_diet_plan,
)

logger = logging.getLogger("nutrimed.nutrition")


ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
    # aliases accepted from the UserModel enum
    "lightly_active": 1.375,
    "moderately_active": 1.55,
    "extra_active": 1.9,
}


class NutritionService:
    def __init__(self, diet_plan_repo: DietPlanRepository) -> None:
        self.diet_plan_repo = diet_plan_repo

    # ------------------------------------------------------------------
    # Pure calculation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
        """Mifflin-St Jeor equation."""
        if gender.lower() == "female":
            return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5

    @staticmethod
    def calculate_tdee(bmr: float, activity_level: str) -> float:
        multiplier = ACTIVITY_MULTIPLIERS.get(activity_level.lower(), 1.55)
        return round(bmr * multiplier, 1)

    @staticmethod
    def calculate_bmi(weight_kg: float, height_cm: float) -> tuple[float, str]:
        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m**2), 1)
        if bmi < 18.5:
            category = "underweight"
        elif bmi < 25:
            category = "normal"
        elif bmi < 30:
            category = "overweight"
        else:
            category = "obese"
        return bmi, category

    @staticmethod
    def estimate_body_fat(
        gender: str,
        waist_cm: float,
        neck_cm: float,
        height_cm: float,
        hip_cm: float | None = None,
    ) -> float:
        """U.S. Navy body fat estimation method."""
        if gender.lower() == "female":
            if hip_cm is None:
                raise ValueError("Hip measurement required for female body fat estimate")
            bf = (
                495 / (1.29579 - 0.35004 * math.log10(waist_cm + hip_cm - neck_cm) + 0.22100 * math.log10(height_cm))
                - 450
            )
        else:
            bf = 495 / (1.0324 - 0.19077 * math.log10(waist_cm - neck_cm) + 0.15456 * math.log10(height_cm)) - 450
        return round(max(bf, 2.0), 1)

    @staticmethod
    def macro_split(target_calories: float, goal: str) -> dict[str, float]:
        """
        Return macro grams based on goal.
        Ratios (protein/carbs/fat as % of calories):
          - weight_loss:  40/30/30
          - muscle_gain:  35/40/25
          - maintenance:  30/40/30
        """
        ratios = {
            "weight_loss": (0.40, 0.30, 0.30),
            "muscle_gain": (0.35, 0.40, 0.25),
            "maintenance": (0.30, 0.40, 0.30),
        }
        p_ratio, c_ratio, f_ratio = ratios.get(goal.lower(), ratios["maintenance"])
        return {
            "protein_g": round(target_calories * p_ratio / 4, 1),
            "carbs_g": round(target_calories * c_ratio / 4, 1),
            "fat_g": round(target_calories * f_ratio / 9, 1),
        }

    def calculate_all(
        self,
        weight_kg: float,
        height_cm: float,
        age: int,
        gender: str,
        activity_level: str = "moderate",
        goal: str = "maintenance",
        waist_cm: float | None = None,
        hip_cm: float | None = None,
        neck_cm: float | None = None,
    ) -> dict:
        bmr = self.calculate_bmr(weight_kg, height_cm, age, gender)
        tdee = self.calculate_tdee(bmr, activity_level)
        bmi, bmi_category = self.calculate_bmi(weight_kg, height_cm)

        body_fat: float | None = None
        if waist_cm and neck_cm:
            with contextlib.suppress(ValueError):
                body_fat = self.estimate_body_fat(gender, waist_cm, neck_cm, height_cm, hip_cm)

        calorie_adjustments = {
            "weight_loss": -500,
            "muscle_gain": 300,
            "maintenance": 0,
        }
        target_calories = round(tdee + calorie_adjustments.get(goal.lower(), 0), 1)
        macros = self.macro_split(target_calories, goal)

        return {
            "bmr": round(bmr, 1),
            "tdee": tdee,
            "bmi": bmi,
            "bmi_category": bmi_category,
            "body_fat_estimate": body_fat,
            "target_calories": target_calories,
            "macros": macros,
        }

    # ------------------------------------------------------------------
    # Diet plan generation (calls local LLM via Ollama)
    # ------------------------------------------------------------------

    async def generate_diet_plan(
        self,
        user_id: str,
        user_profile: dict,
        goal: str = "maintenance",
        dietary_restrictions: list[str] | None = None,
        allergies: list[str] | None = None,
    ) -> dict:
        weight = user_profile.get("weight") or user_profile.get("weight_kg") or 70
        height = user_profile.get("height") or user_profile.get("height_cm") or 170
        age = user_profile.get("age") or 30
        gender = user_profile.get("gender") or "male"
        activity = user_profile.get("activity_level") or "moderate"

        calc = self.calculate_all(
            weight_kg=weight,
            height_cm=height,
            age=age,
            gender=gender,
            activity_level=activity,
            goal=goal,
        )

        restrictions_str = ", ".join(dietary_restrictions or []) or "none"
        allergies_str = ", ".join(allergies or []) or "none"

        # Ground the model in the real food database: it chooses names and gram
        # portions, and every macro is recomputed from the catalogue afterwards.
        preference = "non_vegetarian"
        for restriction in dietary_restrictions or []:
            token = str(restriction).strip().lower().replace("-", "_")
            if token in ("vegan", "vegetarian", "eggetarian", "non_vegetarian"):
                preference = token
                break

        _foods = select_foods(preference=preference, allergies=allergies or [])
        catalogue = format_food_catalogue(_foods, clinical_priority_names(_foods, None))

        prompt = (
            f"Create a 3-day meal plan for a {age}-year-old {gender} "
            f"weighing {weight}kg, {height}cm tall, activity level: {activity}.\n"
            f"Goal: {goal}. Daily target: {calc['target_calories']} kcal, "
            f"protein {calc['macros']['protein_g']}g, "
            f"carbs {calc['macros']['carbs_g']}g, fat {calc['macros']['fat_g']}g.\n"
            f"Dietary restrictions: {restrictions_str}.\n"
            f"Allergies: {allergies_str}.\n\n"
            f"You may ONLY use foods from this catalogue, by exact name. It is "
            f"already filtered for this person's preference and allergies:\n"
            f"{catalogue}\n\n"
            "RULES:\n"
            "- Use exact names from the catalogue. Never invent a food.\n"
            '- Give each portion as a number of grams in "quantity_g".\n'
            "- Do NOT output calories or macros; they are computed from the "
            "catalogue and anything you write is discarded.\n"
            "- Aim the day's totals at the target above.\n"
            "- Give each day breakfast, mid-morning snack, lunch, evening snack "
            "and dinner.\n\n"
            "Return valid JSON with this structure:\n"
            '[{"day": "Monday", "meals": [{"name": "Breakfast", "time": "8:00 AM", '
            '"foods": [{"name": "Oats (dry)", "quantity_g": 60}]}]}]'
        )

        meal_plan = await self._call_llm(prompt)

        raw_days = meal_plan if isinstance(meal_plan, list) else []
        verified, warnings = verify_diet_plan({"meal_plan": raw_days})
        if warnings:
            logger.warning("Diet plan verification for user %s: %s", user_id, warnings[:10])
        verified_days = verified.get("meal_plan") or []

        # Deterministic fallback when the response is unusable or the plan is
        # nutritionally unsound, so the user always gets something sensible.
        adequate, reasons = plan_is_nutritionally_adequate({"meal_plan": verified_days}, int(calc["target_calories"]))
        if not adequate:
            logger.info("Diet plan rejected for user %s: %s", user_id, reasons[:5])
        outcome = (
            OUTCOME_LLM_REPAIRED if (adequate and warnings) else OUTCOME_LLM_VERIFIED if adequate else OUTCOME_FALLBACK
        )
        if not verified_days or not adequate:
            logger.info("Falling back to the template diet generator for user %s", user_id)
            fallback = build_fallback_meal_plan(
                weight_kg=weight,
                height_cm=height,
                age=age,
                gender=gender,
                activity_level=activity,
                goal=goal,
                dietary_preference=preference,
                conditions=dietary_restrictions or [],
            )
            verified_days = fallback.get("meal_plan") or []
            verified["calories"] = fallback.get("calories")
            verified["macros"] = fallback.get("macros")

        plan_doc = {
            "user_id": user_id,
            "goal": goal,
            # Targets from the deterministic calculator; achieved values are
            # summed from the verified plan.
            "calories": calc["target_calories"],
            "macros": calc["macros"],
            "achieved_calories": verified.get("calories"),
            "achieved_macros": verified.get("macros"),
            "meal_plan": verified_days,
            "verified": True,
            "notes": f"Generated for {goal} goal. Restrictions: {restrictions_str}.",
        }
        from datetime import datetime

        plan_doc["created_at"] = datetime.now(UTC)
        saved = await self.diet_plan_repo.create(plan_doc)
        await record_generation_async(
            self.diet_plan_repo.db,
            kind="diet",
            outcome=outcome,
            user_id=user_id,
            dropped=warnings,
            reasons=reasons,
            model=settings.OLLAMA_MODEL,
        )
        saved["nutrition_calc"] = calc
        return saved

    async def _call_llm(self, prompt: str) -> list | str:
        """Call Ollama local LLM and attempt to parse JSON response."""
        url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = data.get("response", "")
                # Try to extract JSON
                import json

                try:
                    # Find JSON array in response
                    start = text.index("[")
                    end = text.rindex("]") + 1
                    return json.loads(text[start:end])
                except (ValueError, json.JSONDecodeError):
                    return text
        except httpx.HTTPError as exc:
            # Treated like an unusable answer: the caller serves the template
            # plan and records the fallback, as the report workers do, rather
            # than failing the request because the model is slow or down.
            logger.warning("LLM call failed (%s): %s", type(exc).__name__, exc)
            return ""
