from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

__all__ = ["RecommendationResponse"]


class RecommendationResponse(BaseModel):
    id: str
    user_id: str
    biomarker_id: str
    deficiencies: List[str] = []
    risk_factors: List[str] = []
    dietary_suggestions: List[str] = []
    supplement_suggestions: List[str] = []
    warnings: List[str] = []
    generated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
