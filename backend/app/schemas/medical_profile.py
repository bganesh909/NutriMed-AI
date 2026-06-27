from pydantic import BaseModel
from typing import Optional
from datetime import datetime

__all__ = ["MedicalProfileCreate", "MedicalProfileOut"]


class MedicalProfileCreate(BaseModel):
    blood_type: Optional[str] = None
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
    blood_type: Optional[str] = None
    allergies: list[str] = []
    chronic_conditions: list[str] = []
    medications: list[str] = []
    surgeries: list[str] = []
    family_history: list[str] = []
    dietary_restrictions: list[str] = []
    notes: str = ""
    updated_at: Optional[datetime] = None
