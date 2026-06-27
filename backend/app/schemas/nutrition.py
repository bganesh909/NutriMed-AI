from typing import Optional

from pydantic import BaseModel

__all__ = ["NutritionCalculation"]


class MacroBreakdown(BaseModel):
    protein_g: float
    carbs_g: float
    fat_g: float


class NutritionCalculation(BaseModel):
    bmr: float
    tdee: float
    bmi: float
    bmi_category: str
    body_fat_estimate: Optional[float] = None
    target_calories: float
    macros: MacroBreakdown
