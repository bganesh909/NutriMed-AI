from datetime import timedelta

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_access_token,
    verify_password,
)
from app.models.user import UserModel
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def register(self, email: str, password: str, full_name: str) -> dict:
        existing = await self.user_repo.find_by_email(email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user = UserModel(
            name=full_name,
            email=email,
            hashed_password=hash_password(password),
        )
        created = await self.user_repo.create_user(user.to_dict())
        tokens = self._generate_tokens(created["id"], "user")
        return {
            "user": created,
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
        }

    async def login(self, email: str, password: str) -> dict:
        user = await self.user_repo.find_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not verify_password(password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        tokens = self._generate_tokens(user["id"], user.get("role", "user"))
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
        }

    async def refresh_token(self, refresh_token: str) -> dict:
        try:
            payload = verify_access_token(refresh_token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user = await self.user_repo.find_by_id(payload["sub"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        tokens = self._generate_tokens(user["id"], user.get("role", "user"))
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
        }

    @staticmethod
    def _generate_tokens(user_id: str, role: str) -> dict:
        access_token = create_access_token(
            subject=user_id,
            role=role,
            expires_delta=timedelta(minutes=settings.JWT_EXPIRY_MINUTES),
        )
        refresh_token = create_access_token(
            subject=user_id,
            role=role,
            extra={"type": "refresh"},
            expires_delta=timedelta(days=7),
        )
        return {"access_token": access_token, "refresh_token": refresh_token}
