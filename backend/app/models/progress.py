from datetime import UTC, datetime
from datetime import date as date_type

from pydantic import BaseModel, Field


class ProgressModel(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    user_id: str
    date: date_type = Field(default_factory=lambda: date_type.today())
    weight: float | None = None
    body_fat_pct: float | None = None
    measurements: dict[str, float] = Field(default_factory=dict)
    biomarker_snapshot: dict[str, float] = Field(default_factory=dict)
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {
        "populate_by_name": True,
    }

    def to_dict(self) -> dict:
        data = self.model_dump(by_alias=False, exclude={"id"})
        data["date"] = data["date"].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ProgressModel":
        doc = dict(data)
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)
