from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import verify_access_token

_bearer_scheme = HTTPBearer()


# ---------------------------------------------------------------------------
# Database dependency
# ---------------------------------------------------------------------------

async def get_db() -> AsyncIOMotorDatabase:
    return get_database()


# ---------------------------------------------------------------------------
# Current user dependency
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    """Extract and validate the JWT, then load the user document from MongoDB."""
    token = credentials.credentials
    try:
        payload = verify_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject",
        )

    from bson import ObjectId

    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user["id"] = str(user.pop("_id"))
    return user


# ---------------------------------------------------------------------------
# Role-based access dependency
# ---------------------------------------------------------------------------

def require_role(role: str) -> Callable:
    """Return a dependency that checks the current user has the required role."""

    async def _role_checker(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        if current_user.get("role") != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required",
            )
        return current_user

    return _role_checker
