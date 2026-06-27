from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.core.config import settings
from app.core.dependencies import get_db
from app.core.security import (
    create_access_token,
    hash_password,
    verify_access_token,
    verify_password,
)
from app.models.user import UserModel
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth")


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    existing = await db["users"].find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = UserModel(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    result = await db["users"].insert_one(user.to_dict())
    user_id = str(result.inserted_id)

    access_token = create_access_token(subject=user_id, role=user.role)
    refresh_token = create_access_token(
        subject=user_id,
        role=user.role,
        extra={"type": "refresh"},
        expires_delta=timedelta(days=7),
    )
    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRY_MINUTES * 60,
    )


@router.post("/login", response_model=AuthTokenResponse)
async def login(body: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    user_doc = await db["users"].find_one({"email": body.email})
    if not user_doc or not verify_password(body.password, user_doc["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user_id = str(user_doc["_id"])
    role = user_doc.get("role", "user")
    access_token = create_access_token(subject=user_id, role=role)
    refresh_token = create_access_token(
        subject=user_id,
        role=role,
        extra={"type": "refresh"},
        expires_delta=timedelta(days=7),
    )
    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRY_MINUTES * 60,
    )


@router.post("/refresh", response_model=AuthTokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        payload = verify_access_token(body.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type -- expected refresh token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject",
        )

    from bson import ObjectId

    user_doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    role = user_doc.get("role", "user")
    new_access_token = create_access_token(subject=user_id, role=role)
    new_refresh_token = create_access_token(
        subject=user_id,
        role=role,
        extra={"type": "refresh"},
        expires_delta=timedelta(days=7),
    )
    return AuthTokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRY_MINUTES * 60,
    )
