from datetime import datetime
from typing import Literal

from pydantic import BaseModel

__all__ = ["MedicalProfileCreate", "MedicalProfileOut"]


# Diet preferences the food catalogue can filter by (app/services/plan_grounding.py).
DietaryPreference = Literal["non_vegetarian", "eggetarian", "vegetarian", "vegan"]


class MedicalProfileCreate(BaseModel):
    blood_type: str | None = None
    dietary_preference: DietaryPreference | None = None
    allergies: list[str] = []
    chronic_conditions: list[str] = []
    medications: list[str] = []
    surgeries: list[str] = []
    family_history: list[str] = []
    dietary_restrictions: list[str] = []
    notes: str = ""


class MedicalProfileOut(BaseModel):
    id: str
    user_id: str
    blood_type: str | None = None
    dietary_preference: str | None = None
    allergies: list[str] = []
    chronic_conditions: list[str] = []
    medications: list[str] = []
    surgeries: list[str] = []
    family_history: list[str] = []
    dietary_restrictions: list[str] = []
    notes: str = ""
    updated_at: datetime | None = None
