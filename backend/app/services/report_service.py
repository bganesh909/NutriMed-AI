import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.security import encrypt_data
from app.repositories.report_repository import ReportRepository

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


class ReportService:
    def __init__(self, report_repo: ReportRepository) -> None:
        self.report_repo = report_repo

    async def upload_report(
        self,
        user_id: str,
        file: UploadFile,
    ) -> dict:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file.content_type}. "
                f"Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
            )

        raw_bytes = await file.read()
        if len(raw_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 20 MB limit",
            )

        # Encrypt and persist
        encrypted = encrypt_data(raw_bytes)
        unique_name = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = UPLOAD_DIR / unique_name

        with open(file_path, "wb") as f:
            f.write(encrypted)

        report_doc = {
            "user_id": user_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "content_type": file.content_type,
            "status": "uploaded",
            "analysis_result": None,
        }

        from datetime import datetime, timezone

        report_doc["created_at"] = datetime.now(timezone.utc)
        report_doc["updated_at"] = datetime.now(timezone.utc)

        created = await self.report_repo.create(report_doc)
        return created

    async def get_report(self, report_id: str, user_id: str) -> dict:
        report = await self.report_repo.get_by_id(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found",
            )
        if report["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        return report

    async def get_user_reports(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> dict:
        reports = await self.report_repo.get_by_user(user_id, skip=skip, limit=limit)
        total = await self.report_repo.count({"user_id": user_id})
        return {"reports": reports, "total": total}

    async def trigger_analysis(self, report_id: str, user_id: str) -> dict:
        report = await self.get_report(report_id, user_id)

        if report["status"] == "processing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Report is already being processed",
            )

        # Update status to processing
        await self.report_repo.update_status(report_id, "processing")

        # Dispatch Celery task (import lazily to avoid circular imports)
        try:
            from app.workers.tasks import analyse_report_task

            analyse_report_task.delay(report_id)
        except ImportError:
            # Workers module may not be available; update status directly
            await self.report_repo.update_status(report_id, "uploaded")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Analysis worker is not available",
            )

        return {"report_id": report_id, "status": "processing"}
