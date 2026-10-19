"""
OCR processing worker.

Sends uploaded lab report files to the OCR microservice, stores the raw
extraction result in MongoDB, and chains to the biomarker extraction task.
"""

import logging
from datetime import UTC, datetime

import httpx
from bson import ObjectId
from pymongo import MongoClient

from app.core.celery_app import celery_app
from app.core.config import settings
from app.services import report_files

logger = logging.getLogger(__name__)

OCR_SERVICE_URL = f"{settings.OCR_SERVICE_URL}/ocr/extract"
OCR_TIMEOUT_SECONDS = 120.0


def _get_db():
    """Return a pymongo database handle (sync driver for Celery tasks)."""
    client = MongoClient(settings.MONGO_URI)
    return client[settings.MONGO_DB_NAME]


@celery_app.task(name="tasks.process_ocr", bind=True, max_retries=3)
def process_ocr(self, report_id: str, file_path: str | None = None):
    """
    1. Read the report's uploaded file (GridFS, or local disk for old reports).
    2. POST it to the OCR microservice for text extraction.
    3. Store the raw OCR result in MongoDB and set status to 'ocr_completed'.
    4. Dispatch the biomarker extraction task.

    ``file_path`` is ignored: tasks queued before files moved to GridFS still
    pass it, and the report document says where its file is.
    """
    db = _get_db()
    report_oid = ObjectId(report_id)

    logger.info("Starting OCR processing for report %s", report_id)

    # Mark the report as processing
    db.reports.update_one(
        {"_id": report_oid},
        {"$set": {"status": "processing", "updated_at": datetime.now(UTC)}},
    )

    try:
        report = db.reports.find_one({"_id": report_oid})
        if not report:
            raise ValueError(f"Report {report_id} not found")
        # Stored AES-encrypted; read_sync returns the decrypted bytes.
        file_bytes = report_files.read_sync(db, report)
        # The OCR service picks its extractor from the file extension.
        filename = report.get("original_filename") or "report.pdf"
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
                    "updated_at": datetime.now(UTC),
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
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        raise self.retry(exc=exc, countdown=60) from exc
