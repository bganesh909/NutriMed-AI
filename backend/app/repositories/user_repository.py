from typing import Optional
from datetime import datetime, timezone

from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    collection_name = "users"

    async def find_by_email(self, email: str) -> Optional[dict]:
        return await self.find_one({"email": email})

    async def create_user(self, user_doc: dict) -> dict:
        return await self.insert_one(user_doc)

    async def update_user(self, user_id: str, data: dict) -> Optional[dict]:
        data["updated_at"] = datetime.now(timezone.utc)
        return await self.update_one(user_id, data)
