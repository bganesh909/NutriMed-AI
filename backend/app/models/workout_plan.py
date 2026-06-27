from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Difficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Exercise(BaseModel):
    name: str
    sets: int
    reps: str
    rest: str = "60s"


class WorkoutDay(BaseModel):
    day_name: str
    exercises: List[Exercise] = Field(default_factory=list)


class WorkoutPlanModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    plan_type: str = "general_fitness"
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    goal: str
    days: List[WorkoutDay] = Field(default_factory=list)
    adaptations: List[str] = Field(default_factory=list)
    duration_weeks: int = 4
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }

    def to_dict(self) -> dict:
        return self.model_dump(by_alias=False, exclude={"id"})

    @classmethod
    def from_dict(cls, data: dict) -> "WorkoutPlanModel":
        doc = dict(data)
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)
