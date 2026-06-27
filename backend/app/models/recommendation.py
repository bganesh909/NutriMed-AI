from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class RecommendationModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    biomarker_id: str
    deficiencies: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    dietary_suggestions: List[str] = Field(default_factory=list)
    supplement_suggestions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
    }

    def to_dict(self) -> dict:
        return self.model_dump(by_alias=False, exclude={"id"})

    @classmethod
    def from_dict(cls, data: dict) -> "RecommendationModel":
        doc = dict(data)
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)
