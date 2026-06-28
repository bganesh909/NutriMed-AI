"""
OCR processing worker.

Sends uploaded lab report files to the OCR microservice, stores the raw
extraction result in MongoDB, and chains to the biomarker extraction task.
"""

import logging
from datetime import datetime, timezone

import httpx
from bson import ObjectId
from pymongo import MongoClient

from app.core.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)

OCR_SERVICE_URL = f"{settings.OCR_SERVICE_URL}/ocr/extract"
OCR_TIMEOUT_SECONDS = 120.0


def _get_db():
    """Return a pymongo database handle (sync driver for Celery tasks)."""
    client = MongoClient(settings.MONGO_URI)
    return client[settings.MONGO_DB_NAME]


@celery_app.task(name="tasks.process_ocr", bind=True, max_retries=3)
def process_ocr(self, report_id: str, file_path: str):
    """
    1. Read the uploaded file from disk.
    2. POST it to the OCR microservice for text extraction.
    3. Store the raw OCR result in MongoDB and set status to 'ocr_completed'.
    4. Dispatch the biomarker extraction task.
    """
    db = _get_db()
    report_oid = ObjectId(report_id)

    logger.info("Starting OCR processing for report %s (file: %s)", report_id, file_path)

    # Mark the report as processing
    db.reports.update_one(
        {"_id": report_oid},
        {"$set": {"status": "processing", "updated_at": datetime.now(timezone.utc)}},
    )

    try:
        # Uploaded files are stored AES-encrypted on disk; decrypt before OCR.
        from app.core.security import decrypt_data

        with open(file_path, "rb") as f:
            file_bytes = decrypt_data(f.read())

        filename = file_path.rsplit("/", 1)[-1]
        response = httpx.post(
            OCR_SERVICE_URL,
            files={"file": (filename, file_bytes)},
            timeout=OCR_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        ocr_result = response.json()

        logger.info(
            "OCR extraction succeeded for report %s (%d text blocks)",
            report_id,
            len(ocr_result.get("text_blocks", [])),
        )

        # Persist the raw OCR result and advance the status
        db.reports.update_one(
            {"_id": report_oid},
            {
                "$set": {
                    "ocr_result": ocr_result,
                    "status": "ocr_completed",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        # Chain to biomarker extraction
        from app.workers.extraction_worker import extract_biomarkers

        extract_biomarkers.delay(report_id)

    except Exception as exc:
        logger.exception("OCR processing failed for report %s", report_id)
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
