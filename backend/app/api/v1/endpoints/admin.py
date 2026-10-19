"""
Admin console API: platform stats and user management. Admin role only.

Admins see account metadata and counts, never report contents or biomarkers.
"""

import re
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.core.config import settings
from app.core.dependencies import get_db, require_role
from app.models.user import UserRole
from app.services import account_service
from app.utils.validators import to_object_id

router = APIRouter(prefix="/admin")

_admin = require_role("admin")


class RoleUpdate(BaseModel):
    role: UserRole


@router.get("/stats")
async def get_stats(
    _: dict = Depends(_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    week_ago = datetime.now(UTC) - timedelta(days=7)
    reports_by_status = {
        row["_id"] or "unknown": row["count"]
        async for row in db["reports"].aggregate([{"$group": {"_id": "$status", "count": {"$sum": 1}}}])
    }
    return {
        "users": await db["users"].count_documents({}),
        "new_users_7d": await db["users"].count_documents({"created_at": {"$gte": week_ago}}),
        "reports": sum(reports_by_status.values()),
        "reports_7d": await db["reports"].count_documents({"uploaded_at": {"$gte": week_ago}}),
        "reports_by_status": reports_by_status,
        "diet_plans": await db["diet_plans"].count_documents({}),
        "workout_plans": await db["workout_plans"].count_documents({}),
        "progress_entries": await db["progress"].count_documents({}),
    }


# Headers hosting proxies use to pass on the visitor's address and scheme.
_PROXY_HEADERS = (
    "x-forwarded-for",
    "x-forwarded-proto",
    "cf-connecting-ip",
    "true-client-ip",
    "x-real-ip",
    "forwarded",
)


@router.get("/client-ip")
async def get_client_ip(request: Request, _: dict = Depends(_admin)):
    """
    The address the API records for this request (rate limiting, audit log)
    and the proxy headers it arrived with, for checking CLIENT_IP_HEADER after
    deploying behind a hosting proxy (docs/DEPLOY_RENDER_VERCEL.md).
    """
    return {
        "client_ip": request.client.host if request.client else None,
        "scheme": request.url.scheme,
        "client_ip_header": settings.CLIENT_IP_HEADER or None,
        "client_ip_hops": settings.CLIENT_IP_HOPS,
        "headers": {name: ", ".join(request.headers.getlist(name)) or None for name in _PROXY_HEADERS},
    }


@router.get("/users")
async def list_users(
    q: str = Query("", max_length=100),
    limit: int = Query(100, ge=1, le=500),
    _: dict = Depends(_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    query: dict = {}
    if q.strip():
        pattern = re.escape(q.strip())
        match = {"$regex": pattern, "$options": "i"}
        query = {"$or": [{"name": match}, {"email": match}]}

    users = [doc async for doc in db["users"].find(query, {"hashed_password": 0}).sort("created_at", -1).limit(limit)]
    ids = [str(u["_id"]) for u in users]
    report_counts = {
        row["_id"]: row["count"]
        async for row in db["reports"].aggregate(
            [{"$match": {"user_id": {"$in": ids}}}, {"$group": {"_id": "$user_id", "count": {"$sum": 1}}}]
        )
    }
    return [
        {
            "id": str(u["_id"]),
            "name": u.get("name"),
            "email": u.get("email"),
            "role": u.get("role", "user"),
            "created_at": u.get("created_at"),
            "report_count": report_counts.get(str(u["_id"]), 0),
        }
        for u in users
    ]


@router.patch("/users/{user_id}/role")
async def update_role(
    user_id: str,
    body: RoleUpdate,
    admin: dict = Depends(_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if user_id == admin["id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot change your own role")
    result = await db["users"].update_one(
        {"_id": to_object_id(user_id, "User")},
        {"$set": {"role": body.role.value, "updated_at": datetime.now(UTC)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"id": user_id, "role": body.role.value}


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    admin: dict = Depends(_admin),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if user_id == admin["id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account here")
    if not await db["users"].find_one({"_id": to_object_id(user_id, "User")}, {"_id": 1}):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await account_service.delete_user(db, user_id)
