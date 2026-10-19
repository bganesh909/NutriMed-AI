import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.core.security import (
    create_access_token,
    hash_password,
    token_predates_password_change,
    verify_access_token,
    verify_password,
)
from app.models.user import UserModel
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


def _token_response(user_id: str, role: str) -> AuthTokenResponse:
    """Issue a fresh access + refresh token pair."""
    return AuthTokenResponse(
        access_token=create_access_token(subject=user_id, role=role),
        refresh_token=create_access_token(
            subject=user_id,
            role=role,
            extra={"type": "refresh"},
            expires_delta=timedelta(days=7),
        ),
        token_type="bearer",
        expires_in=settings.JWT_EXPIRY_MINUTES * 60,
    )


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    existing = await db["users"].find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = UserModel(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        age=body.age,
        gender=body.gender,
        weight=body.weight,
        height=body.height,
        activity_level=body.activity_level,
        goals=body.goals,
        terms_accepted_at=datetime.now(UTC) if body.accepted_terms else None,
    )
    result = await db["users"].insert_one(user.to_dict())
    return _token_response(str(result.inserted_id), user.role)


@router.post("/login", response_model=AuthTokenResponse)
async def login(body: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    user_doc = await db["users"].find_one({"email": body.email})
    if not user_doc or not verify_password(body.password, user_doc["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return _token_response(str(user_doc["_id"]), user_doc.get("role", "user"))


@router.post("/refresh", response_model=AuthTokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        payload = verify_access_token(body.refresh_token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from exc

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
    if token_predates_password_change(payload, user_doc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session ended by a password change. Please sign in again.",
        )

    return _token_response(user_id, user_doc.get("role", "user"))


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=20)
    password: str = Field(..., min_length=8, max_length=128)


_RESET_SENT = {"message": "If an account exists for that email, a reset link has been sent."}


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _frontend_url(request: Request) -> str:
    """Link back to the app the user is on, provided it is a trusted origin."""
    origin = request.headers.get("origin")
    if origin and origin in settings.ALLOWED_ORIGINS:
        return origin
    return settings.FRONTEND_URL.rstrip("/")


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Email a single-use reset link. Always answers the same way, so the endpoint
    cannot be used to discover which emails are registered.
    """
    user_doc = await db["users"].find_one({"email": body.email})
    if not user_doc:
        return _RESET_SENT

    user_id = str(user_doc["_id"])
    # At most one email a minute per account, so the endpoint cannot be used
    # to flood someone's inbox. The answer stays the same either way.
    recent = await db["password_resets"].find_one(
        {"user_id": user_id, "created_at": {"$gte": datetime.now(UTC) - timedelta(seconds=60)}}
    )
    if recent:
        return _RESET_SENT

    token = secrets.token_urlsafe(32)
    # Only the hash is stored: a database leak must not yield usable links.
    await db["password_resets"].delete_many({"user_id": user_id})
    await db["password_resets"].insert_one(
        {
            "user_id": user_id,
            "token_hash": _hash_reset_token(token),
            "expires_at": datetime.now(UTC) + timedelta(minutes=settings.PASSWORD_RESET_EXPIRY_MINUTES),
            "created_at": datetime.now(UTC),
        }
    )

    link = f"{_frontend_url(request)}/reset-password?token={token}"
    await send_email(
        to=body.email,
        subject="Reset your NutriMed AI password",
        body=(
            f"Hi {user_doc.get('name', 'there')},\n\n"
            f"Use the link below to choose a new password. It expires in "
            f"{settings.PASSWORD_RESET_EXPIRY_MINUTES} minutes and can be used once.\n\n"
            f"{link}\n\n"
            "If you didn't ask for this, you can ignore this email.\n"
        ),
    )
    return _RESET_SENT


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    reset_doc = await db["password_resets"].find_one({"token_hash": _hash_reset_token(body.token)})
    expires_at = reset_doc.get("expires_at") if reset_doc else None
    if expires_at and expires_at.tzinfo is None:
        # Mongo returns naive UTC datetimes.
        expires_at = expires_at.replace(tzinfo=UTC)
    if not reset_doc or not expires_at or expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired. Request a new one.",
        )

    from bson import ObjectId

    now = datetime.now(UTC)
    await db["users"].update_one(
        {"_id": ObjectId(reset_doc["user_id"])},
        {
            "$set": {
                "hashed_password": hash_password(body.password),
                # Signs out sessions issued before the reset (see get_current_user).
                "password_changed_at": now,
                "updated_at": now,
            }
        },
    )
    await db["password_resets"].delete_many({"user_id": reset_doc["user_id"]})
    logger.info("Password reset completed for user %s", reset_doc["user_id"])
    return {"message": "Your password has been updated. You can now sign in."}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post("/change-password", response_model=AuthTokenResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Change the password of the signed-in user. Every other session is signed
    out; this one continues with the fresh tokens returned.
    """
    if not verify_password(body.current_password, current_user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current password is incorrect")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current one",
        )

    from bson import ObjectId

    now = datetime.now(UTC)
    await db["users"].update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": {"hashed_password": hash_password(body.new_password), "password_changed_at": now, "updated_at": now}},
    )
    return _token_response(current_user["id"], current_user.get("role", "user"))
