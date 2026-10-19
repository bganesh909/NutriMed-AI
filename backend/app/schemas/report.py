from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.report import ReportType

__all__ = ["ReportCreate", "ReportResponse", "ReportAnalysisResponse"]


class ReportCreate(BaseModel):
    report_type: ReportType
    original_filename: str


class ReportResponse(BaseModel):
    id: str
    user_id: str
    report_type: str
    original_filename: str
    status: str
    uploaded_at: datetime | None = None
    processed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReportAnalysisResponse(BaseModel):
    report_id: str
    status: str
    biomarkers: dict[str, Any] | None = None
    deficiencies: list[Any] = []
    risk_factors: list[Any] = []
    dietary_suggestions: list[Any] = []
    supplement_suggestions: list[Any] = []
    warnings: list[Any] = []
