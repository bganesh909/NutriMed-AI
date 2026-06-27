from datetime import date as date_type, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

__all__ = ["ProgressLogCreate", "ProgressLogResponse", "ProgressHistoryResponse"]


class ProgressLogCreate(BaseModel):
    date: date_type = Field(default_factory=date_type.today)
    weight: Optional[float] = Field(None, ge=10, le=500)
    body_fat_pct: Optional[float] = Field(None, ge=1, le=70)
    measurements: Dict[str, float] = Field(default_factory=dict)
    biomarker_snapshot: Dict[str, float] = Field(default_factory=dict)
    notes: str = ""


class ProgressLogResponse(BaseModel):
    id: str
    user_id: str
    date: date_type
    weight: Optional[float] = None
    body_fat_pct: Optional[float] = None
    measurements: Dict[str, float] = {}
    biomarker_snapshot: Dict[str, float] = {}
    notes: str = ""
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProgressHistoryResponse(BaseModel):
    entries: List[ProgressLogResponse]
    total: int
    trends: Dict[str, float] = Field(default_factory=dict)
