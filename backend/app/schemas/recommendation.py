from datetime import datetime

from pydantic import BaseModel

__all__ = ["RecommendationResponse"]


class RecommendationResponse(BaseModel):
    id: str
    user_id: str
    biomarker_id: str
    deficiencies: list[str] = []
    risk_factors: list[str] = []
    dietary_suggestions: list[str] = []
    supplement_suggestions: list[str] = []
    warnings: list[str] = []
    generated_at: datetime | None = None

    model_config = {"from_attributes": True}
