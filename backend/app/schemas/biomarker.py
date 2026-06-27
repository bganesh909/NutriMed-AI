from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel

__all__ = ["BiomarkerCreate", "BiomarkerResponse", "BiomarkerWithInterpretation"]


class BiomarkerCreate(BaseModel):
    report_id: str
    hemoglobin: Optional[float] = None
    vitamin_d: Optional[float] = None
    vitamin_b12: Optional[float] = None
    ldl: Optional[float] = None
    hdl: Optional[float] = None
    triglycerides: Optional[float] = None
    fasting_sugar: Optional[float] = None
    hba1c: Optional[float] = None
    creatinine: Optional[float] = None
    tsh: Optional[float] = None
    sgpt: Optional[float] = None
    sgot: Optional[float] = None
    iron: Optional[float] = None
    calcium: Optional[float] = None
    urea: Optional[float] = None
    uric_acid: Optional[float] = None


class BiomarkerResponse(BaseModel):
    id: str
    user_id: str
    report_id: str
    hemoglobin: Optional[float] = None
    vitamin_d: Optional[float] = None
    vitamin_b12: Optional[float] = None
    ldl: Optional[float] = None
    hdl: Optional[float] = None
    triglycerides: Optional[float] = None
    fasting_sugar: Optional[float] = None
    hba1c: Optional[float] = None
    creatinine: Optional[float] = None
    tsh: Optional[float] = None
    sgpt: Optional[float] = None
    sgot: Optional[float] = None
    iron: Optional[float] = None
    calcium: Optional[float] = None
    urea: Optional[float] = None
    uric_acid: Optional[float] = None
    extracted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BiomarkerInterpretation(BaseModel):
    name: str
    value: Optional[float] = None
    unit: str = ""
    normal_range: str = ""
    status: str = "normal"
    remark: str = ""


class BiomarkerWithInterpretation(BiomarkerResponse):
    interpretations: list[BiomarkerInterpretation] = []
