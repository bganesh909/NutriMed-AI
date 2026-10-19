from datetime import UTC, datetime

from pydantic import BaseModel, Field


class BiomarkerModel(BaseModel):
    id: str | None = Field(default=None, alias="_id")
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
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

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
