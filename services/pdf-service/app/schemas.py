from pydantic import BaseModel, Field
from typing import Optional


class PatientInfo(BaseModel):
    name: str
    age: int
    gender: str
    weight_kg: float
    height_cm: float
    blood_group: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    report_date: Optional[str] = None


class BiomarkerEntry(BaseModel):
    name: str
    value: float
    unit: str
    reference_low: float
    reference_high: float
    status: str = Field(default="normal", pattern="^(low|normal|high|critical)$")


class RiskFactor(BaseModel):
    name: str
    severity: str = Field(default="moderate", pattern="^(low|moderate|high|critical)$")
    description: str


class MealItem(BaseModel):
    name: str
    quantity: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class MealEntry(BaseModel):
    meal_type: str
    time: str
    items: list[MealItem]


class DailyDietEntry(BaseModel):
    day: str
    meals: list[MealEntry]
    total_calories: float


class ExerciseEntry(BaseModel):
    name: str
    sets: int
    reps: str
    rest_seconds: int
    notes: Optional[str] = None


class WorkoutSessionEntry(BaseModel):
    day: str
    focus: str
    exercises: list[ExerciseEntry]


class SupplementRecommendation(BaseModel):
    name: str
    dosage: str
    timing: str
    reason: str


class BiomarkerHistory(BaseModel):
    name: str
    dates: list[str]
    values: list[float]
    unit: str


class HealthReportRequest(BaseModel):
    patient: PatientInfo
    biomarkers: list[BiomarkerEntry] = Field(default_factory=list)
    risk_factors: list[RiskFactor] = Field(default_factory=list)
    deficiencies: list[str] = Field(default_factory=list)
    diet_plan: Optional[list[DailyDietEntry]] = None
    workout_plan: Optional[list[WorkoutSessionEntry]] = None
    supplements: list[SupplementRecommendation] = Field(default_factory=list)
    biomarker_history: Optional[list[BiomarkerHistory]] = None
    macros: Optional[dict] = None
    bmi: Optional[float] = None
    bmi_category: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class DietPlanPDFRequest(BaseModel):
    patient: PatientInfo
    diet_plan: list[DailyDietEntry]
    target_calories: int
    macros: dict
    dietary_preference: str = "non_vegetarian"
    notes: list[str] = Field(default_factory=list)


class WorkoutPlanPDFRequest(BaseModel):
    patient: PatientInfo
    workout_plan: list[WorkoutSessionEntry]
    fitness_level: str
    goal: str
    days_per_week: int
    notes: list[str] = Field(default_factory=list)


class PDFResponse(BaseModel):
    filename: str
    file_path: str
    file_size_bytes: int
    message: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
