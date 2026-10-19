from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.dependencies import get_current_user, get_db
from app.utils.validators import to_object_id

router = APIRouter(prefix="/notifications")


@router.get("/")
async def list_notifications(
    limit: int = Query(30, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Recent notifications (written by the report pipeline), newest first."""
    user_id = current_user["id"]
    cursor = db["notifications"].find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    items = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        items.append(doc)
    unread = await db["notifications"].count_documents({"user_id": user_id, "read": False})
    return {"items": items, "unread_count": unread}


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    await db["notifications"].update_many({"user_id": current_user["id"], "read": False}, {"$set": {"read": True}})


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    result = await db["notifications"].update_one(
        {"_id": to_object_id(notification_id, "Notification"), "user_id": current_user["id"]},
        {"$set": {"read": True}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
