from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DietPlanType(StrEnum):
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
    calories: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None


class Meal(BaseModel):
    name: str
    time: str
    foods: list[FoodItem] = Field(default_factory=list)


class DietPlanModel(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    user_id: str
    plan_type: DietPlanType
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    meals: list[Meal] = Field(default_factory=list)
    duration_weeks: int = 4
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

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
