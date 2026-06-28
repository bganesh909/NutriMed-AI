from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.models.report import ReportStatus, ReportType

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
    uploaded_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReportAnalysisResponse(BaseModel):
    report_id: str
    status: str
    biomarkers: Optional[Dict[str, Any]] = None
    deficiencies: List[Any] = []
    risk_factors: List[Any] = []
    dietary_suggestions: List[Any] = []
    supplement_suggestions: List[Any] = []
    warnings: List[Any] = []
