from fastapi import HTTPException, status

from app.repositories.biomarker_repository import BiomarkerRepository


class BiomarkerService:
    def __init__(self, biomarker_repo: BiomarkerRepository) -> None:
        self.biomarker_repo = biomarker_repo

    async def save_biomarkers(
        self, user_id: str, report_id: str, markers: dict[str, float]
    ) -> dict:
        doc = {
            "user_id": user_id,
            "report_id": report_id,
            "markers": markers,
        }
        from datetime import datetime, timezone

        doc["created_at"] = datetime.now(timezone.utc)
        return await self.biomarker_repo.create(doc)

    async def get_biomarkers(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> list[dict]:
        return await self.biomarker_repo.get_by_user(user_id, skip=skip, limit=limit)

    async def get_latest(self, user_id: str) -> dict:
        result = await self.biomarker_repo.get_latest_by_user(user_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No biomarkers found for this user",
            )
        return result

    async def get_by_report(self, report_id: str) -> dict:
        result = await self.biomarker_repo.get_by_report(report_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No biomarkers found for this report",
            )
        return result
