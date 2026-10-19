"""
Biomarker extraction worker.

Reads the raw OCR result stored in MongoDB, parses numeric biomarker values
from the extracted text, persists them in the biomarkers collection, and
chains to the analysis task.
"""

import logging
import re
from datetime import UTC, datetime

from bson import ObjectId
from pymongo import MongoClient

from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.lab_units import parse_range, to_canonical

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


def _markers_from_ocr_result(ocr_result: dict) -> tuple[dict[str, float], dict[str, dict]]:
    """
    Reuse the structured biomarkers already parsed by the OCR service, if present.
    The OCR service returns {"ocr": {...}, "biomarkers": {"biomarkers": [ {name, value, unit, ...} ]}}.

    Returns (markers, as_reported): marker_name -> value, with blood counts in
    canonical units (app/services/lab_units.py) so every reader -- rule engine,
    workout adaptations, the PDF -- compares like with like; and the value,
    unit and reference range exactly as printed. A count whose scale is unclear
    is kept in as_reported only, so nothing misreads it.
    """
    markers: dict[str, float] = {}
    as_reported: dict[str, dict] = {}
    bio = ocr_result.get("biomarkers")
    items = bio.get("biomarkers") if isinstance(bio, dict) else None
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            value = item.get("value")
            if not name or not isinstance(value, (int, float)):
                continue
            name = str(name)
            unit = str(item.get("unit") or "")
            reference_range = str(item.get("reference_range") or "")
            as_reported[name] = {"value": float(value), "unit": unit, "reference_range": reference_range}
            canonical = to_canonical(name, float(value), unit, parse_range(reference_range)).value
            if canonical is not None:
                markers[name] = canonical
    return markers, as_reported


def _flatten_ocr_text(ocr_result: dict) -> str:
    """
    Combine all text blocks from the OCR result into a single string.
    Supports a flat 'text'/'raw_text' field, a list of 'text_blocks', and the
    OCR service's nested payload under an 'ocr' key.
    """
    parts: list[str] = []
    source = ocr_result.get("ocr") if isinstance(ocr_result.get("ocr"), dict) else ocr_result

    for key in ("text", "raw_text"):
        if isinstance(source.get(key), str):
            parts.append(source[key])

    for block in source.get("text_blocks", []):
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
        # Prefer biomarkers already parsed by the OCR service; fall back to
        # regex parsing of the raw OCR text.
        markers, as_reported = _markers_from_ocr_result(ocr_result)
        if not markers and not as_reported:
            raw_text = _flatten_ocr_text(ocr_result)
            parsed = _extract_markers_from_text(raw_text)
            # No units here; values are placed by magnitude, or dropped if unclear.
            converted = {name: to_canonical(name, value).value for name, value in parsed.items()}
            markers = {name: value for name, value in converted.items() if value is not None}

        if not markers:
            logger.warning("No biomarkers extracted from report %s", report_id)

        # Build biomarker document
        biomarker_doc = {
            "user_id": user_id,
            "report_id": report_id,
            "extracted_at": datetime.now(UTC),
        }
        biomarker_doc.update(markers)
        if as_reported:
            biomarker_doc["as_reported"] = as_reported

        # Upsert into the biomarkers collection. report_id carries a unique
        # index, so re-running analysis on the same report must replace the
        # existing row rather than insert a duplicate.
        db.biomarkers.replace_one(
            {"report_id": report_id},
            biomarker_doc,
            upsert=True,
        )
        stored = db.biomarkers.find_one({"report_id": report_id}, {"_id": 1})
        biomarker_id = str(stored["_id"]) if stored else ""

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
                    "updated_at": datetime.now(UTC),
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
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        raise self.retry(exc=exc, countdown=60) from exc
