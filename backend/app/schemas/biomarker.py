from datetime import datetime

from pydantic import BaseModel

__all__ = ["BiomarkerCreate", "BiomarkerResponse", "BiomarkerWithInterpretation"]


class BiomarkerCreate(BaseModel):
    report_id: str
    hemoglobin: float | None = None
    vitamin_d: float | None = None
    vitamin_b12: float | None = None
    ldl: float | None = None
    hdl: float | None = None
    triglycerides: float | None = None
    fasting_sugar: float | None = None
    hba1c: float | None = None
    creatinine: float | None = None
    tsh: float | None = None
    sgpt: float | None = None
    sgot: float | None = None
    iron: float | None = None
    calcium: float | None = None
    urea: float | None = None
    uric_acid: float | None = None


class BiomarkerResponse(BaseModel):
    id: str
    user_id: str
    report_id: str
    hemoglobin: float | None = None
    vitamin_d: float | None = None
    vitamin_b12: float | None = None
    ldl: float | None = None
    hdl: float | None = None
    triglycerides: float | None = None
    fasting_sugar: float | None = None
    hba1c: float | None = None
    creatinine: float | None = None
    tsh: float | None = None
    sgpt: float | None = None
    sgot: float | None = None
    iron: float | None = None
    calcium: float | None = None
    urea: float | None = None
    uric_acid: float | None = None
    extracted_at: datetime | None = None

    model_config = {"from_attributes": True}


class BiomarkerInterpretation(BaseModel):
    name: str
    value: float | None = None
    unit: str = ""
    normal_range: str = ""
    status: str = "normal"
    remark: str = ""


class BiomarkerWithInterpretation(BiomarkerResponse):
    interpretations: list[BiomarkerInterpretation] = []
