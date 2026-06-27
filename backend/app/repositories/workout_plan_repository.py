from typing import Optional

from app.repositories.base import BaseRepository


class WorkoutPlanRepository(BaseRepository):
    collection_name = "workout_plans"

    async def create(self, plan_doc: dict) -> dict:
        return await self.insert_one(plan_doc)

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
