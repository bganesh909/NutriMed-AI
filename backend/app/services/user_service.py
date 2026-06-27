from fastapi import HTTPException, status

from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def get_profile(self, user_id: str) -> dict:
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        user.pop("hashed_password", None)
        return user

    async def update_profile(self, user_id: str, data: dict) -> dict:
        # Remove None values so we only update provided fields
        update_data = {k: v for k, v in data.items() if v is not None}
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        updated = await self.user_repo.update_user(user_id, update_data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        updated.pop("hashed_password", None)
        return updated
