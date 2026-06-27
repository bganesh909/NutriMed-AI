"""Pydantic schemas for OCR service request/response models."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ReportType(str, Enum):
    CBC = "cbc"
    LIPID_PROFILE = "lipid_profile"
    LFT = "lft"
    KFT = "kft"
    THYROID = "thyroid"
    VITAMIN = "vitamin"
    DIABETES = "diabetes"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class Base64ImageRequest(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded image data")
    filename: Optional[str] = Field(None, description="Original filename (used for type detection)")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class TextBlock(BaseModel):
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: Optional[list[list[int]]] = Field(
        None, description="Bounding box coordinates [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]"
    )


class ExtractedBiomarker(BaseModel):
    name: str = Field(..., description="Canonical biomarker name")
    value: Optional[float] = Field(None, description="Numeric value")
    value_raw: str = Field("", description="Raw string value as extracted")
    unit: str = Field("", description="Unit of measurement")
    reference_range: str = Field("", description="Reference/normal range string")
    status: str = Field("normal", description="normal | low | high | critical")


class OCRExtractionResponse(BaseModel):
    raw_text: str = Field("", description="Full extracted raw text")
    text_blocks: list[TextBlock] = Field(default_factory=list)
    normalized_text: str = Field("", description="Cleaned/normalized text")


class BiomarkerExtractionResponse(BaseModel):
    report_type: ReportType = ReportType.UNKNOWN
    biomarkers: list[ExtractedBiomarker] = Field(default_factory=list)
    raw_text: str = ""
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class PipelineResponse(BaseModel):
    ocr: OCRExtractionResponse
    biomarkers: BiomarkerExtractionResponse


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "ocr-service"
    version: str = "1.0.0"
