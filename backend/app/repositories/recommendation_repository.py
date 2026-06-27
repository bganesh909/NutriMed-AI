from typing import Optional

from app.repositories.base import BaseRepository


class RecommendationRepository(BaseRepository):
    collection_name = "recommendations"

    async def create(self, rec_doc: dict) -> dict:
        return await self.insert_one(rec_doc)

    async def get_by_user(
        self, user_id: str, skip: int = 0, limit: int = 20
    ) -> list[dict]:
        return await self.find_many(
            {"user_id": user_id},
            sort=[("created_at", -1)],
            skip=skip,
            limit=limit,
        )

    async def get_latest(self, user_id: str) -> Optional[dict]:
        results = await self.find_many(
            {"user_id": user_id},
            sort=[("created_at", -1)],
            limit=1,
        )
        return results[0] if results else None
