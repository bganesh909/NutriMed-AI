from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.workout_plan import Difficulty

__all__ = ["WorkoutPlanRequest", "WorkoutPlanResponse", "ExerciseSchema"]


class ExerciseSchema(BaseModel):
    name: str
    sets: int = 3
    reps: str = "10-12"
    rest: str = "60s"

    # LLM-generated plans return reps/rest as either numbers or strings.
    @field_validator("reps", "rest", mode="before")
    @classmethod
    def _coerce_to_str(cls, v):
        return str(v) if v is not None else v


class WorkoutDaySchema(BaseModel):
    day_name: str = "Workout"
    exercises: list[ExerciseSchema] = Field(default_factory=list)

    # Some models label the day "day" or "name" instead of "day_name".
    @model_validator(mode="before")
    @classmethod
    def _normalise_day_name(cls, data):
        if isinstance(data, dict) and not data.get("day_name"):
            alias = data.get("day") or data.get("name")
            if alias:
                data = {**data, "day_name": str(alias)}
        return data


class WorkoutPlanRequest(BaseModel):
    goal: str = "general_fitness"
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    injuries: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)

    model_config = {"use_enum_values": True}


class WorkoutPlanResponse(BaseModel):
    id: str
    user_id: str
    # Tolerant defaults: report-derived plans (from the recommendation worker)
    # don't carry these fields, while directly-generated plans do.
    plan_type: str = "custom"
    difficulty: str = "intermediate"
    goal: str = "general_fitness"
    days: list[WorkoutDaySchema] = []
    adaptations: list[str] = []
    duration_weeks: int = 4
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
