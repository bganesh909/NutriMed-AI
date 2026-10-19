from datetime import datetime

from pydantic import BaseModel, Field

from app.models.diet_plan import DietPlanType

__all__ = ["DietPlanRequest", "DietPlanResponse", "MealSchema", "FoodItemSchema"]


class FoodItemSchema(BaseModel):
    name: str
    quantity: str = ""
    calories: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None


class MealSchema(BaseModel):
    name: str
    time: str
    foods: list[FoodItemSchema] = Field(default_factory=list)


class DietPlanRequest(BaseModel):
    plan_type: DietPlanType = DietPlanType.BALANCED
    dietary_preference: str = "none"
    goal: str = "maintenance"

    model_config = {"use_enum_values": True}


class DietPlanResponse(BaseModel):
    id: str
    user_id: str
    plan_type: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    meals: list[MealSchema] = []
    duration_weeks: int = 4
    notes: str = ""
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
