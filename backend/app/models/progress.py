from datetime import date, datetime, timezone
from typing import Dict, Optional

from pydantic import BaseModel, Field


class ProgressModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    date: date = Field(default_factory=lambda: date.today())
    weight: Optional[float] = None
    body_fat_pct: Optional[float] = None
    measurements: Dict[str, float] = Field(default_factory=dict)
    biomarker_snapshot: Dict[str, float] = Field(default_factory=dict)
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
