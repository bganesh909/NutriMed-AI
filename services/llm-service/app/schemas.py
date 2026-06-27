from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="The prompt to send to the LLM")
    model: Optional[str] = Field(None, description="Model name; uses default if not set")
    system_prompt: Optional[str] = Field(None, description="System prompt for context")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=32768)


class GenerateResponse(BaseModel):
    text: str
    model: str
    tokens_used: int
    duration_ms: float


class LabAnalysisRequest(BaseModel):
    age: int = Field(..., ge=0, le=150)
    gender: str = Field(..., pattern="^(male|female|other)$")
    weight: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    activity_level: str = Field(
        ..., pattern="^(sedentary|lightly_active|moderately_active|very_active|extremely_active)$"
    )
    conditions: list[str] = Field(default_factory=list)
    biomarkers: dict = Field(..., description="Biomarker name to value mapping")
    reference_ranges: Optional[dict] = Field(
        None, description="Optional custom reference ranges"
    )
    model: Optional[str] = None


class LabAnalysisResponse(BaseModel):
    analysis: dict
    model: str
    tokens_used: int
    duration_ms: float


class DietPlanRequest(BaseModel):
    age: int = Field(..., ge=0, le=150)
    gender: str = Field(..., pattern="^(male|female|other)$")
    weight: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    activity_level: str
    goal: str = Field(..., description="e.g. weight_loss, muscle_gain, maintenance")
    dietary_preference: str = Field(
        default="omnivore",
        description="e.g. omnivore, vegetarian, vegan, keto, paleo",
    )
    allergies: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    calories: Optional[int] = Field(None, gt=0)
    protein_g: Optional[float] = Field(None, ge=0)
    carbs_g: Optional[float] = Field(None, ge=0)
    fat_g: Optional[float] = Field(None, ge=0)
    biomarker_considerations: Optional[str] = Field(None)
    model: Optional[str] = None


class DietPlanResponse(BaseModel):
    plan: dict
    model: str
    tokens_used: int
    duration_ms: float


class WorkoutPlanRequest(BaseModel):
    age: int = Field(..., ge=0, le=150)
    gender: str = Field(..., pattern="^(male|female|other)$")
    weight: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    activity_level: str
    goal: str = Field(..., description="e.g. strength, hypertrophy, endurance, flexibility")
    fitness_level: str = Field(
        default="beginner", pattern="^(beginner|intermediate|advanced)$"
    )
    conditions: list[str] = Field(default_factory=list)
    injuries: list[str] = Field(default_factory=list)
    available_equipment: list[str] = Field(default_factory=lambda: ["bodyweight"])
    days_per_week: int = Field(default=4, ge=1, le=7)
    session_duration_minutes: int = Field(default=60, ge=15, le=180)
    biomarker_considerations: Optional[str] = Field(None)
    model: Optional[str] = None


class WorkoutPlanResponse(BaseModel):
    plan: dict
    model: str
    tokens_used: int
    duration_ms: float


class SupplementRequest(BaseModel):
    age: int = Field(..., ge=0, le=150)
    gender: str = Field(..., pattern="^(male|female|other)$")
    weight: float = Field(..., gt=0)
    conditions: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    current_supplements: list[str] = Field(default_factory=list)
    biomarkers: dict = Field(default_factory=dict)
    goal: str = Field(default="general_health")
    dietary_preference: str = Field(default="omnivore")
    model: Optional[str] = None


class SupplementResponse(BaseModel):
    recommendations: dict
    model: str
    tokens_used: int
    duration_ms: float


class ModelInfo(BaseModel):
    name: str
    size: Optional[str] = None
    modified_at: Optional[str] = None
    digest: Optional[str] = None


class ModelsResponse(BaseModel):
    models: list[ModelInfo]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    ollama_connected: bool
