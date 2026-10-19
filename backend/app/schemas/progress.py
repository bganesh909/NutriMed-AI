from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, Field

__all__ = ["ProgressLogCreate", "ProgressLogResponse", "ProgressHistoryResponse"]


class ProgressLogCreate(BaseModel):
    date: date_type = Field(default_factory=date_type.today)
    weight: float | None = Field(None, ge=10, le=500)
    body_fat_pct: float | None = Field(None, ge=1, le=70)
    measurements: dict[str, float] = Field(default_factory=dict)
    biomarker_snapshot: dict[str, float] = Field(default_factory=dict)
    notes: str = ""


class ProgressLogResponse(BaseModel):
    id: str
    user_id: str
    date: date_type
    weight: float | None = None
    body_fat_pct: float | None = None
    measurements: dict[str, float] = {}
    biomarker_snapshot: dict[str, float] = {}
    notes: str = ""
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProgressHistoryResponse(BaseModel):
    entries: list[ProgressLogResponse]
    total: int
    trends: dict[str, float] = Field(default_factory=dict)
