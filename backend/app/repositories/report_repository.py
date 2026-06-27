from typing import Optional
from datetime import datetime, timezone

from app.repositories.base import BaseRepository


class ReportRepository(BaseRepository):
    collection_name = "reports"

    async def create(self, report_doc: dict) -> dict:
        return await self.insert_one(report_doc)

    async def get_by_id(self, report_id: str) -> Optional[dict]:
        return await self.find_by_id(report_id)

    async def get_by_user(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> list[dict]:
        return await self.find_many(
            {"user_id": user_id},
            sort=[("created_at", -1)],
            skip=skip,
            limit=limit,
        )

    async def update_status(
        self, report_id: str, status: str, analysis_result: dict | None = None
    ) -> Optional[dict]:
        update: dict = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        if analysis_result is not None:
            update["analysis_result"] = analysis_result
        return await self.update_one(report_id, update)
