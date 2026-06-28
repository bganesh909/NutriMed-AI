import os
import uuid
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.dependencies import get_current_user, get_db
from app.core.security import encrypt_data
from app.models.report import ReportModel, ReportStatus, ReportType
from app.schemas.report import ReportAnalysisResponse, ReportResponse

router = APIRouter(prefix="/reports")

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "uploads")


@router.post("/upload", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def upload_report(
    file: UploadFile,
    report_type: ReportType,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    content = await file.read()
    encrypted = encrypt_data(content)
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(encrypted)

    report = ReportModel(
        user_id=current_user["id"],
        report_type=report_type,
        file_path=file_path,
        original_filename=file.filename or "unknown",
        status=ReportStatus.UPLOADED,
    )
    result = await db["reports"].insert_one(report.to_dict())
    report_id = str(result.inserted_id)

    return ReportResponse(
        id=report_id,
        user_id=current_user["id"],
        report_type=report_type.value,
        original_filename=report.original_filename,
        status=ReportStatus.UPLOADED.value,
        uploaded_at=report.uploaded_at,
    )


@router.get("/", response_model=list[ReportResponse])
async def list_reports(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cursor = db["reports"].find({"user_id": current_user["id"]}).sort("uploaded_at", -1)
    reports = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        reports.append(ReportResponse(**doc))
    return reports


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db["reports"].find_one({"_id": ObjectId(report_id), "user_id": current_user["id"]})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    doc["id"] = str(doc.pop("_id"))
    return ReportResponse(**doc)


@router.post("/{report_id}/analyze")
async def trigger_analysis(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Trigger analysis pipeline for a report."""
    doc = await db["reports"].find_one(
        {"_id": ObjectId(report_id), "user_id": current_user["id"]}
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if doc["status"] == ReportStatus.PROCESSING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Report is already being processed",
        )

    # Mark as processing
    await db["reports"].update_one(
        {"_id": ObjectId(report_id)},
        {
            "$set": {
                "status": ReportStatus.PROCESSING.value,
                "processed_at": None,
            }
        },
    )

    # Dispatch Celery task. process_ocr is the pipeline entry point; it chains
    # to biomarker extraction and AI analysis.
    try:
        from app.workers.ocr_worker import process_ocr

        process_ocr.delay(report_id, doc["file_path"])
    except (ImportError, Exception):
        # Workers module may not be available in dev; revert status
        await db["reports"].update_one(
            {"_id": ObjectId(report_id)},
            {"$set": {"status": ReportStatus.UPLOADED.value}},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analysis worker is not available. Ensure Celery workers are running.",
        )

    return {"report_id": report_id, "status": "processing", "message": "Analysis task dispatched"}


@router.get("/{report_id}/analysis", response_model=ReportAnalysisResponse)
async def get_report_analysis(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    report_doc = await db["reports"].find_one({"_id": ObjectId(report_id), "user_id": current_user["id"]})
    if not report_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if report_doc["status"] != ReportStatus.COMPLETED.value:
        return ReportAnalysisResponse(report_id=report_id, status=report_doc["status"])

    biomarker_doc = await db["biomarkers"].find_one({"report_id": report_id})
    rec_doc = await db["recommendations"].find_one({"biomarker_id": str(biomarker_doc["_id"])}) if biomarker_doc else None

    biomarkers = {}
    if biomarker_doc:
        exclude_keys = {"_id", "user_id", "report_id", "extracted_at"}
        biomarkers = {k: v for k, v in biomarker_doc.items() if k not in exclude_keys and v is not None}

    return ReportAnalysisResponse(
        report_id=report_id,
        status=report_doc["status"],
        biomarkers=biomarkers or None,
        deficiencies=rec_doc.get("deficiencies", []) if rec_doc else [],
        risk_factors=rec_doc.get("risk_factors", []) if rec_doc else [],
        dietary_suggestions=rec_doc.get("dietary_suggestions", []) if rec_doc else [],
        supplement_suggestions=rec_doc.get("supplement_suggestions", []) if rec_doc else [],
        warnings=rec_doc.get("warnings", []) if rec_doc else [],
    )
