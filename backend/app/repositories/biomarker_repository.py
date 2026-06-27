from typing import Optional

from app.repositories.base import BaseRepository


class BiomarkerRepository(BaseRepository):
    collection_name = "biomarkers"

    async def create(self, biomarker_doc: dict) -> dict:
        return await self.insert_one(biomarker_doc)

    async def get_by_report(self, report_id: str) -> Optional[dict]:
        return await self.find_one({"report_id": report_id})

    async def get_by_user(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> list[dict]:
        return await self.find_many(
            {"user_id": user_id},
            sort=[("created_at", -1)],
            skip=skip,
            limit=limit,
        )

    async def get_latest_by_user(self, user_id: str) -> Optional[dict]:
        results = await self.find_many(
            {"user_id": user_id},
            sort=[("created_at", -1)],
            limit=1,
        )
        return results[0] if results else None
