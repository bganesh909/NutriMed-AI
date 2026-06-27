from typing import Optional
from datetime import datetime

from app.repositories.base import BaseRepository


class ProgressRepository(BaseRepository):
    collection_name = "progress"

    async def create(self, progress_doc: dict) -> dict:
        return await self.insert_one(progress_doc)

    async def get_history(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        filter_: dict = {"user_id": user_id}
        if start_date or end_date:
            date_filter: dict = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            filter_["recorded_at"] = date_filter
        return await self.find_many(
            filter_,
            sort=[("recorded_at", -1)],
            skip=skip,
            limit=limit,
        )

    async def get_latest(self, user_id: str) -> Optional[dict]:
        results = await self.find_many(
            {"user_id": user_id},
            sort=[("recorded_at", -1)],
            limit=1,
        )
        return results[0] if results else None
