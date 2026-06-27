from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class BiomarkerModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
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
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
    }

    def to_dict(self) -> dict:
        return self.model_dump(by_alias=False, exclude={"id"})

    @classmethod
    def from_dict(cls, data: dict) -> "BiomarkerModel":
        doc = dict(data)
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)
