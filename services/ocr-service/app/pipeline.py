"""Full OCR pipeline orchestrator.

Receives a file (PDF or image), runs the complete extraction pipeline,
and returns structured biomarker JSON.
"""

from __future__ import annotations

import base64
import logging
import re
import tempfile
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from app.biomarker_engine import (
    PARSER_REGISTRY,
    BaseReportParser,
    run_all_parsers,
)
from app.extractor import extract_from_image, extract_from_pdf
from app.medical_parser import MedicalParser, ParsedBiomarker
from app.normalizer import normalize
from app.preprocessor import preprocess
from app.schemas import (
    BiomarkerExtractionResponse,
    ExtractedBiomarker,
    OCRExtractionResponse,
    PipelineResponse,
    ReportType,
    TextBlock,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# File type detection
# ---------------------------------------------------------------------------

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
_PDF_EXTENSIONS = {".pdf"}


def _detect_file_type(filename: str) -> str:
    """Return 'image', 'pdf', or 'unknown'."""
    ext = Path(filename).suffix.lower()
    if ext in _IMAGE_EXTENSIONS:
        return "image"
    if ext in _PDF_EXTENSIONS:
        return "pdf"
    return "unknown"


# ---------------------------------------------------------------------------
# Report type detection
# ---------------------------------------------------------------------------

_REPORT_TYPE_KEYWORDS: dict[str, list[str]] = {
    "cbc": [
        r"complete\s*blood\s*count", r"cbc", r"haemogram", r"hemogram",
        r"blood\s*count", r"total\s*leucocyte",
    ],
    "lipid_profile": [
        r"lipid\s*profile", r"lipid\s*panel", r"cholesterol\s*panel",
        r"lipid\s*test",
    ],
    "lft": [
        r"liver\s*function", r"lft", r"hepatic\s*panel",
        r"hepatic\s*function",
    ],
    "kft": [
        r"kidney\s*function", r"kft", r"renal\s*function", r"rft",
        r"renal\s*panel",
    ],
    "thyroid": [
        r"thyroid\s*function", r"thyroid\s*profile", r"thyroid\s*panel",
        r"tft",
    ],
    "vitamin": [
        r"vitamin\s*(?:d|b\s*12)", r"vit\s*(?:d|b\s*12)",
        r"iron\s*(?:study|profile)", r"ferritin",
    ],
    "diabetes": [
        r"diabet", r"hba1c", r"glyc(?:osyl|at)ed", r"glucose\s*(?:fasting|random|pp)",
        r"blood\s*sugar",
    ],
}


def detect_report_type(text: str) -> ReportType:
    """Detect the report type from the extracted text."""
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for rtype, patterns in _REPORT_TYPE_KEYWORDS.items():
        count = 0
        for pat in patterns:
            matches = re.findall(pat, text_lower)
            count += len(matches)
        if count > 0:
            scores[rtype] = count

    if not scores:
        return ReportType.UNKNOWN

    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    try:
        return ReportType(best)
    except ValueError:
        return ReportType.UNKNOWN


# ---------------------------------------------------------------------------
# Value validation
# ---------------------------------------------------------------------------

# Plausible ranges for sanity-checking extracted values
_PLAUSIBLE_RANGES: dict[str, tuple[float, float]] = {
    "hemoglobin": (2.0, 25.0),
    "rbc": (0.5, 10.0),
    "wbc": (500, 100000),
    "platelets": (0.1, 20.0),  # in lakhs
    "pcv": (10, 70),
    "mcv": (50, 150),
    "mch": (15, 45),
    "mchc": (25, 40),
    "total_cholesterol": (50, 500),
    "ldl": (20, 400),
    "hdl": (10, 150),
    "vldl": (5, 100),
    "triglycerides": (30, 1000),
    "alt": (1, 2000),
    "ast": (1, 2000),
    "alp": (10, 1000),
    "total_bilirubin": (0.1, 30),
    "direct_bilirubin": (0.0, 20),
    "creatinine": (0.1, 20),
    "urea": (5, 300),
    "bun": (2, 150),
    "uric_acid": (1, 20),
    "tsh": (0.01, 100),
    "free_t3": (0.1, 20),
    "free_t4": (0.1, 10),
    "fasting_glucose": (20, 600),
    "pp_glucose": (30, 700),
    "hba1c": (3, 20),
    "vitamin_d": (1, 200),
    "vitamin_b12": (50, 3000),
    "ferritin": (1, 5000),
    "iron": (5, 500),
    "sodium": (100, 180),
    "potassium": (1.5, 8.0),
    "calcium": (4, 16),
    "egfr": (5, 200),
}


def _validate_biomarker(bio: ParsedBiomarker) -> tuple[bool, Optional[str]]:
    """Check if a parsed biomarker value is within plausible range."""
    if bio.value is None:
        return True, None  # Can't validate without a value

    bounds = _PLAUSIBLE_RANGES.get(bio.canonical_name)
    if bounds is None:
        return True, None

    low, high = bounds
    if bio.value < low or bio.value > high:
        return False, (
            f"{bio.canonical_name} value {bio.value} outside plausible range "
            f"[{low}, {high}]"
        )
    return True, None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_pipeline_from_file(
    file_path: str,
    filename: Optional[str] = None,
) -> PipelineResponse:
    """Run the full OCR + biomarker extraction pipeline on a file.

    Parameters
    ----------
    file_path : str
        Path to the uploaded file on disk.
    filename : str, optional
        Original filename (used for type detection if provided).

    Returns
    -------
    PipelineResponse
        Combined OCR + biomarker extraction results.
    """
    fname = filename or Path(file_path).name
    file_type = _detect_file_type(fname)

    if file_type == "unknown":
        # Try to detect from content (magic bytes)
        with open(file_path, "rb") as f:
            header = f.read(8)
        if header[:4] == b"%PDF":
            file_type = "pdf"
        elif header[:3] == b"\xff\xd8\xff":  # JPEG
            file_type = "image"
        elif header[:8] == b"\x89PNG\r\n\x1a\n":  # PNG
            file_type = "image"
        else:
            file_type = "image"  # Default to image

    logger.info("Processing file '%s' as %s", fname, file_type)

    # Step 1: Extract text
    if file_type == "pdf":
        text_blocks, raw_text = extract_from_pdf(file_path)
    else:
        # Preprocess image
        img = cv2.imread(file_path)
        if img is None:
            raise ValueError(f"Could not read image file: {file_path}")
        preprocessed = preprocess(img)
        text_blocks = extract_from_image(preprocessed)
        raw_text = " ".join(b.text for b in text_blocks)

    # Step 2: Normalize text
    normalized = normalize(raw_text)

    # Step 3: Build OCR response
    ocr_response = OCRExtractionResponse(
        raw_text=raw_text,
        text_blocks=text_blocks,
        normalized_text=normalized,
    )

    # Step 4: Detect report type
    report_type = detect_report_type(normalized)

    # Step 5: Run appropriate parser(s)
    biomarkers, warnings = _extract_biomarkers(normalized, report_type)

    # Step 6: Compute confidence
    confidence = _compute_confidence(text_blocks, biomarkers)

    biomarker_response = BiomarkerExtractionResponse(
        report_type=report_type,
        biomarkers=biomarkers,
        raw_text=normalized,
        confidence=confidence,
        warnings=warnings,
    )

    return PipelineResponse(ocr=ocr_response, biomarkers=biomarker_response)


def run_pipeline_from_base64(
    image_base64: str,
    filename: Optional[str] = None,
) -> PipelineResponse:
    """Run the pipeline from a base64-encoded image."""
    # Decode base64 to bytes
    try:
        # Handle data URI prefix if present
        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]
        image_bytes = base64.b64decode(image_base64)
    except Exception as exc:
        raise ValueError(f"Invalid base64 image data: {exc}") from exc

    # Determine extension
    ext = ".png"
    if filename:
        ext = Path(filename).suffix or ".png"
    elif image_bytes[:3] == b"\xff\xd8\xff":
        ext = ".jpg"
    elif image_bytes[:4] == b"%PDF":
        ext = ".pdf"

    # Write to temp file
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        return run_pipeline_from_file(tmp_path, filename=filename)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_biomarkers(
    text: str,
    report_type: ReportType,
) -> tuple[list[ExtractedBiomarker], list[str]]:
    """Run parser(s) and validate results."""
    warnings: list[str] = []
    parsed: list[ParsedBiomarker] = []

    # Use specific parser if report type is known
    if report_type != ReportType.UNKNOWN:
        parser = PARSER_REGISTRY.get(report_type.value)
        if parser:
            parsed = parser.parse(text)
            # Also evaluate status
            for bio in parsed:
                status = parser.evaluate_status(bio)
                bio._status = status  # type: ignore[attr-defined]

    # If specific parser found nothing, run all parsers
    if not parsed:
        parsed = run_all_parsers(text)

    # Also run the general MedicalParser as a fallback to catch anything missed
    general_parser = MedicalParser()
    general_results = general_parser.parse(text)
    seen_names = {p.canonical_name for p in parsed}
    for gr in general_results:
        if gr.canonical_name not in seen_names:
            parsed.append(gr)
            seen_names.add(gr.canonical_name)

    # Validate and convert
    biomarkers: list[ExtractedBiomarker] = []
    for bio in parsed:
        valid, warning = _validate_biomarker(bio)
        if not valid and warning:
            warnings.append(warning)

        status = getattr(bio, "_status", "normal")
        if not valid:
            status = "suspect"

        biomarkers.append(ExtractedBiomarker(
            name=bio.canonical_name,
            value=bio.value,
            value_raw=bio.value_raw,
            unit=bio.unit,
            reference_range=bio.reference_range,
            status=status,
        ))

    return biomarkers, warnings


def _compute_confidence(
    text_blocks: list[TextBlock],
    biomarkers: list[ExtractedBiomarker],
) -> float:
    """Compute an overall confidence score for the extraction."""
    if not text_blocks and not biomarkers:
        return 0.0

    scores: list[float] = []

    # OCR confidence
    if text_blocks:
        ocr_confidences = [b.confidence for b in text_blocks if b.confidence > 0]
        if ocr_confidences:
            scores.append(sum(ocr_confidences) / len(ocr_confidences))

    # Biomarker extraction confidence: more markers found = higher confidence
    if biomarkers:
        valid_count = sum(1 for b in biomarkers if b.value is not None)
        marker_confidence = min(valid_count / 5.0, 1.0)  # 5+ markers = full confidence
        scores.append(marker_confidence)

    if not scores:
        return 0.0

    return round(sum(scores) / len(scores), 3)
