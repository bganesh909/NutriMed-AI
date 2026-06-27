from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.workout_plan import Difficulty

__all__ = ["WorkoutPlanRequest", "WorkoutPlanResponse", "ExerciseSchema"]


class ExerciseSchema(BaseModel):
    name: str
    sets: int
    reps: str
    rest: str = "60s"


class WorkoutDaySchema(BaseModel):
    day_name: str
    exercises: List[ExerciseSchema] = Field(default_factory=list)


class WorkoutPlanRequest(BaseModel):
    goal: str = "general_fitness"
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    injuries: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)

    model_config = {"use_enum_values": True}


class WorkoutPlanResponse(BaseModel):
    id: str
    user_id: str
    plan_type: str
    difficulty: str
    goal: str
    days: List[WorkoutDaySchema] = []
    adaptations: List[str] = []
    duration_weeks: int = 4
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
