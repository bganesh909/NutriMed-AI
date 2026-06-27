"""
Biomarker extraction worker.

Reads the raw OCR result stored in MongoDB, parses numeric biomarker values
from the extracted text, persists them in the biomarkers collection, and
chains to the analysis task.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from pymongo import MongoClient

from app.core.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)

# Map of canonical biomarker names to regex patterns that may appear in OCR text.
# Each pattern captures a floating-point number following the marker label.
_MARKER_PATTERNS: dict[str, list[str]] = {
    "hemoglobin": [r"h(?:ae)?moglobin\s*[:\-]?\s*([\d]+\.?\d*)"],
    "vitamin_d": [
        r"vitamin\s*d\s*(?:\(25-?oh\))?\s*[:\-]?\s*([\d]+\.?\d*)",
        r"25[\s\-]?oh[\s\-]?(?:vitamin\s*)?d\s*[:\-]?\s*([\d]+\.?\d*)",
    ],
    "vitamin_b12": [
        r"vitamin\s*b[\s\-]?12\s*[:\-]?\s*([\d]+\.?\d*)",
        r"b[\s\-]?12\s*[:\-]?\s*([\d]+\.?\d*)",
    ],
    "ldl": [r"ldl\s*(?:cholesterol)?\s*[:\-]?\s*([\d]+\.?\d*)"],
    "hdl": [r"hdl\s*(?:cholesterol)?\s*[:\-]?\s*([\d]+\.?\d*)"],
    "triglycerides": [r"triglycerides?\s*[:\-]?\s*([\d]+\.?\d*)"],
    "fasting_sugar": [
        r"fasting\s*(?:blood\s*)?(?:sugar|glucose)\s*[:\-]?\s*([\d]+\.?\d*)",
        r"fbs\s*[:\-]?\s*([\d]+\.?\d*)",
    ],
    "hba1c": [r"hba1c\s*[:\-]?\s*([\d]+\.?\d*)", r"glycated\s*h(?:ae)?moglobin\s*[:\-]?\s*([\d]+\.?\d*)"],
    "creatinine": [r"creatinine\s*[:\-]?\s*([\d]+\.?\d*)"],
    "tsh": [r"tsh\s*[:\-]?\s*([\d]+\.?\d*)"],
    "sgpt": [r"sgpt\s*[:\-]?\s*([\d]+\.?\d*)", r"alt\s*[:\-]?\s*([\d]+\.?\d*)"],
    "sgot": [r"sgot\s*[:\-]?\s*([\d]+\.?\d*)", r"ast\s*[:\-]?\s*([\d]+\.?\d*)"],
    "iron": [r"(?:serum\s*)?iron\s*[:\-]?\s*([\d]+\.?\d*)"],
    "calcium": [r"calcium\s*[:\-]?\s*([\d]+\.?\d*)"],
    "urea": [r"(?:blood\s*)?urea(?:\s*nitrogen)?\s*[:\-]?\s*([\d]+\.?\d*)"],
    "uric_acid": [r"uric\s*acid\s*[:\-]?\s*([\d]+\.?\d*)"],
}


def _get_db():
    client = MongoClient(settings.MONGO_URI)
    return client[settings.MONGO_DB_NAME]


def _extract_markers_from_text(raw_text: str) -> dict[str, float]:
    """
    Parse biomarker values from free-form OCR text using regex patterns.
    Returns a dict of marker_name -> numeric value.
    """
    text_lower = raw_text.lower()
    markers: dict[str, float] = {}

    for marker_name, patterns in _MARKER_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    markers[marker_name] = float(match.group(1))
                except (ValueError, IndexError):
                    continue
                break  # first matching pattern wins
    return markers


def _flatten_ocr_text(ocr_result: dict) -> str:
    """
    Combine all text blocks from the OCR result into a single string.
    Supports both a flat 'text' field and a list of 'text_blocks'.
    """
    parts: list[str] = []

    if "text" in ocr_result and isinstance(ocr_result["text"], str):
        parts.append(ocr_result["text"])

    for block in ocr_result.get("text_blocks", []):
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            parts.append(block.get("text", ""))

    return "\n".join(parts)


@celery_app.task(name="tasks.extract_biomarkers", bind=True, max_retries=3)
def extract_biomarkers(self, report_id: str):
    """
    1. Read the OCR result from the report document.
    2. Extract biomarker values using regex-based parsing.
    3. Store extracted biomarkers in the biomarkers collection.
    4. Update report status to 'extracted'.
    5. Dispatch the analysis task.
    """
    db = _get_db()
    report_oid = ObjectId(report_id)

    logger.info("Starting biomarker extraction for report %s", report_id)

    try:
        report = db.reports.find_one({"_id": report_oid})
        if not report:
            raise ValueError(f"Report {report_id} not found in database")

        ocr_result = report.get("ocr_result")
        if not ocr_result:
            raise ValueError(f"No OCR result found for report {report_id}")

        user_id = report["user_id"]
        raw_text = _flatten_ocr_text(ocr_result)
        markers = _extract_markers_from_text(raw_text)

        if not markers:
            logger.warning("No biomarkers extracted from report %s", report_id)

        # Build biomarker document
        biomarker_doc = {
            "user_id": user_id,
            "report_id": report_id,
            "extracted_at": datetime.now(timezone.utc),
        }
        biomarker_doc.update(markers)

        # Insert into biomarkers collection
        insert_result = db.biomarkers.insert_one(biomarker_doc)
        biomarker_id = str(insert_result.inserted_id)

        logger.info(
            "Extracted %d biomarkers for report %s (biomarker_id=%s)",
            len(markers),
            report_id,
            biomarker_id,
        )

        # Update report status
        db.reports.update_one(
            {"_id": report_oid},
            {
                "$set": {
                    "status": "extracted",
                    "biomarker_id": biomarker_id,
                    "extracted_markers": list(markers.keys()),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        # Chain to analysis
        from app.workers.analysis_worker import analyze_biomarkers

        analyze_biomarkers.delay(report_id, user_id)

    except Exception as exc:
        logger.exception("Biomarker extraction failed for report %s", report_id)
        db.reports.update_one(
            {"_id": report_oid},
            {
                "$set": {
                    "status": "failed",
                    "error": str(exc),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        raise self.retry(exc=exc, countdown=60)
