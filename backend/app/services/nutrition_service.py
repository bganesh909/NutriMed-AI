"""
Nutrition calculation and diet plan generation service.

Calculations:
- BMR via Mifflin-St Jeor equation
- TDEE from BMR * activity multiplier
- BMI from weight/height
- Body fat estimate via U.S. Navy method
- Macro split based on goal
"""

import math
from typing import Optional

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.repositories.diet_plan_repository import DietPlanRepository


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
    def calculate_bmr(
        weight_kg: float, height_cm: float, age: int, gender: str
    ) -> float:
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
        bmi = round(weight_kg / (height_m ** 2), 1)
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
        hip_cm: Optional[float] = None,
    ) -> float:
        """U.S. Navy body fat estimation method."""
        if gender.lower() == "female":
            if hip_cm is None:
                raise ValueError("Hip measurement required for female body fat estimate")
            bf = (
                495
                / (
                    1.29579
                    - 0.35004 * math.log10(waist_cm + hip_cm - neck_cm)
                    + 0.22100 * math.log10(height_cm)
                )
                - 450
            )
        else:
            bf = (
                495
                / (
                    1.0324
                    - 0.19077 * math.log10(waist_cm - neck_cm)
                    + 0.15456 * math.log10(height_cm)
                )
                - 450
            )
        return round(max(bf, 2.0), 1)

    @staticmethod
    def macro_split(
        target_calories: float, goal: str
    ) -> dict[str, float]:
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
        waist_cm: Optional[float] = None,
        hip_cm: Optional[float] = None,
        neck_cm: Optional[float] = None,
    ) -> dict:
        bmr = self.calculate_bmr(weight_kg, height_cm, age, gender)
        tdee = self.calculate_tdee(bmr, activity_level)
        bmi, bmi_category = self.calculate_bmi(weight_kg, height_cm)

        body_fat: Optional[float] = None
        if waist_cm and neck_cm:
            try:
                body_fat = self.estimate_body_fat(
                    gender, waist_cm, neck_cm, height_cm, hip_cm
                )
            except ValueError:
                pass

        calorie_adjustments = {
            "weight_loss": -500,
            "muscle_gain": 300,
            "maintenance": 0,
        }
        target_calories = round(
            tdee + calorie_adjustments.get(goal.lower(), 0), 1
        )
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

        prompt = (
            f"Create a detailed 7-day meal plan for a {age}-year-old {gender} "
            f"weighing {weight}kg, {height}cm tall, activity level: {activity}.\n"
            f"Goal: {goal}. Daily calories: {calc['target_calories']} kcal.\n"
            f"Macros: protein {calc['macros']['protein_g']}g, "
            f"carbs {calc['macros']['carbs_g']}g, fat {calc['macros']['fat_g']}g.\n"
            f"Dietary restrictions: {restrictions_str}.\n"
            f"Allergies: {allergies_str}.\n\n"
            "For each day provide breakfast, mid-morning snack, lunch, evening snack, "
            "and dinner with specific food items, quantities, and approximate calories. "
            "Return the result as valid JSON with this structure:\n"
            '[{"day": "Monday", "meals": [{"name": "Breakfast", "time": "8:00 AM", '
            '"foods": [{"name": "Oatmeal", "quantity": "1 cup", "calories": 150, '
            '"protein_g": 5, "carbs_g": 27, "fat_g": 3}]}]}]'
        )

        meal_plan = await self._call_llm(prompt)

        plan_doc = {
            "user_id": user_id,
            "goal": goal,
            "calories": calc["target_calories"],
            "macros": calc["macros"],
            "meal_plan": meal_plan if isinstance(meal_plan, list) else [{"raw": meal_plan}],
            "notes": f"Generated for {goal} goal. Restrictions: {restrictions_str}.",
        }
        from datetime import datetime, timezone

        plan_doc["created_at"] = datetime.now(timezone.utc)
        saved = await self.diet_plan_repo.create(plan_doc)
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
            async with httpx.AsyncClient(timeout=120) as client:
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
        except httpx.HTTPError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM service (Ollama) is not available. Please ensure it is running.",
            )
