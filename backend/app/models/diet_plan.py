from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DietPlanType(str, Enum):
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    MAINTENANCE = "maintenance"
    THERAPEUTIC = "therapeutic"
    KETO = "keto"
    VEGAN = "vegan"
    BALANCED = "balanced"


class FoodItem(BaseModel):
    name: str
    quantity: str = ""
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None


class Meal(BaseModel):
    name: str
    time: str
    foods: List[FoodItem] = Field(default_factory=list)


class DietPlanModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    plan_type: DietPlanType
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    meals: List[Meal] = Field(default_factory=list)
    duration_weeks: int = 4
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }

    def to_dict(self) -> dict:
        return self.model_dump(by_alias=False, exclude={"id"})

    @classmethod
    def from_dict(cls, data: dict) -> "DietPlanModel":
        doc = dict(data)
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)
