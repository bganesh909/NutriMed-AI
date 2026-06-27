from typing import Optional
from datetime import datetime, timezone

from app.repositories.base import BaseRepository


class MedicalProfileRepository(BaseRepository):
    collection_name = "medical_profiles"

    async def create_or_update(self, user_id: str, data: dict) -> dict:
        data["user_id"] = user_id
        data["updated_at"] = datetime.now(timezone.utc)
        existing = await self.find_one({"user_id": user_id})
        if existing:
            result = await self.update_one(existing["id"], data)
            return result
        return await self.insert_one(data)

    async def get_by_user(self, user_id: str) -> Optional[dict]:
        return await self.find_one({"user_id": user_id})
