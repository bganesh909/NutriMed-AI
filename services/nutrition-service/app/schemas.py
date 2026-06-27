from pydantic import BaseModel, Field
from typing import Optional


class NutritionCalculateRequest(BaseModel):
    weight_kg: float = Field(..., gt=0, le=500, description="Weight in kilograms")
    height_cm: float = Field(..., gt=0, le=300, description="Height in centimeters")
    age: int = Field(..., ge=1, le=150, description="Age in years")
    gender: str = Field(..., pattern="^(male|female)$")
    activity_level: str = Field(
        default="moderate",
        pattern="^(sedentary|light|moderate|active|very_active)$",
    )
    goal: str = Field(
        default="maintenance",
        pattern="^(fat_loss|muscle_gain|maintenance|recomposition)$",
    )
    waist_cm: Optional[float] = Field(None, gt=0, description="Waist circumference in cm")
    neck_cm: Optional[float] = Field(None, gt=0, description="Neck circumference in cm")
    hip_cm: Optional[float] = Field(None, gt=0, description="Hip circumference in cm (required for females)")


class NutritionCalculateResponse(BaseModel):
    bmr: float
    tdee: float
    bmi: float
    bmi_category: str
    body_fat_percentage: Optional[float] = None
    macros: dict
    hydration_ml: float
    target_calories: float


class DietGenerateRequest(BaseModel):
    weight_kg: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    age: int = Field(..., ge=1, le=150)
    gender: str = Field(..., pattern="^(male|female)$")
    activity_level: str = Field(default="moderate")
    goal: str = Field(default="maintenance")
    dietary_preference: str = Field(
        default="non_vegetarian",
        pattern="^(vegetarian|non_vegetarian|vegan|eggetarian)$",
    )
    cuisine_preference: str = Field(
        default="indian",
        pattern="^(indian|western|mediterranean|mixed)$",
    )
    allergies: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    target_calories: Optional[int] = Field(None, gt=0)
    use_llm: bool = Field(default=True, description="Use LLM for personalized plan")


class MealItem(BaseModel):
    name: str
    quantity: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class Meal(BaseModel):
    meal_type: str
    time: str
    items: list[MealItem]
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float


class DailyDietPlan(BaseModel):
    day: str
    meals: list[Meal]
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    water_ml: float


class DietPlanResponse(BaseModel):
    plan_name: str
    goal: str
    target_calories: int
    target_macros: dict
    dietary_preference: str
    cuisine_preference: str
    daily_plans: list[DailyDietPlan]
    notes: list[str]
    supplements: list[str]


class MealPlanRequest(BaseModel):
    target_calories: int = Field(..., gt=0)
    protein_g: float = Field(..., ge=0)
    carbs_g: float = Field(..., ge=0)
    fat_g: float = Field(..., ge=0)
    dietary_preference: str = Field(default="non_vegetarian")
    cuisine_preference: str = Field(default="indian")
    meal_count: int = Field(default=5, ge=3, le=7)
    allergies: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)


class MealPlanResponse(BaseModel):
    meals: list[Meal]
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    notes: list[str]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
