from pydantic import BaseModel, Field
from typing import Optional


class WorkoutGenerateRequest(BaseModel):
    age: int = Field(..., ge=1, le=150)
    gender: str = Field(..., pattern="^(male|female)$")
    weight_kg: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    fitness_level: str = Field(
        default="beginner",
        pattern="^(beginner|intermediate|advanced)$",
    )
    goal: str = Field(
        default="general_fitness",
        pattern="^(fat_loss|muscle_gain|strength|endurance|general_fitness|flexibility)$",
    )
    days_per_week: int = Field(default=4, ge=2, le=7)
    session_duration_minutes: int = Field(default=60, ge=20, le=180)
    available_equipment: list[str] = Field(
        default_factory=lambda: ["bodyweight"],
        description="e.g. bodyweight, dumbbells, barbell, machines, cables, resistance_bands",
    )
    conditions: list[str] = Field(default_factory=list)
    injuries: list[str] = Field(default_factory=list)


class ExerciseDetail(BaseModel):
    name: str
    sets: int
    reps: str
    rest_seconds: int
    notes: Optional[str] = None
    alternatives: list[str] = Field(default_factory=list)


class WorkoutSession(BaseModel):
    day: str
    focus: str
    warmup: list[str]
    exercises: list[ExerciseDetail]
    cooldown: list[str]
    estimated_duration_minutes: int
    notes: list[str] = Field(default_factory=list)


class WorkoutPlanResponse(BaseModel):
    plan_name: str
    fitness_level: str
    goal: str
    days_per_week: int
    split_type: str
    sessions: list[WorkoutSession]
    progressive_overload: list[str]
    general_notes: list[str]


class AdaptWorkoutRequest(BaseModel):
    workout_plan: dict = Field(..., description="Existing workout plan to adapt")
    biomarkers: dict = Field(default_factory=dict, description="Biomarker name to value mapping")
    conditions: list[str] = Field(default_factory=list)
    injuries: list[str] = Field(default_factory=list)


class AdaptWorkoutResponse(BaseModel):
    adapted_plan: dict
    adaptations_made: list[str]
    warnings: list[str]


class ExerciseInfo(BaseModel):
    name: str
    muscle_group: str
    equipment: str
    difficulty: str
    instructions: str
    alternatives: list[str]


class ExerciseListResponse(BaseModel):
    exercises: list[ExerciseInfo]
    total_count: int


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
