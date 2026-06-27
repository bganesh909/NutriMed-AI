from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.dependencies import get_current_user, get_db
from app.models.progress import ProgressModel
from app.schemas.progress import (
    ProgressHistoryResponse,
    ProgressLogCreate,
    ProgressLogResponse,
)

router = APIRouter(prefix="/progress")


@router.post("/", response_model=ProgressLogResponse, status_code=201)
async def create_progress_log(
    body: ProgressLogCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    entry = ProgressModel(
        user_id=current_user["id"],
        date=body.date,
        weight=body.weight,
        body_fat_pct=body.body_fat_pct,
        measurements=body.measurements,
        biomarker_snapshot=body.biomarker_snapshot,
        notes=body.notes,
    )
    result = await db["progress"].insert_one(entry.to_dict())
    entry_id = str(result.inserted_id)

    return ProgressLogResponse(
        id=entry_id,
        user_id=current_user["id"],
        date=entry.date,
        weight=entry.weight,
        body_fat_pct=entry.body_fat_pct,
        measurements=entry.measurements,
        biomarker_snapshot=entry.biomarker_snapshot,
        notes=entry.notes,
        created_at=entry.created_at,
    )


@router.get("/", response_model=ProgressHistoryResponse)
async def get_progress_history(
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    total = await db["progress"].count_documents({"user_id": current_user["id"]})
    cursor = (
        db["progress"]
        .find({"user_id": current_user["id"]})
        .sort("date", -1)
        .skip(skip)
        .limit(limit)
    )

    entries = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        entries.append(ProgressLogResponse(**doc))

    trends: dict[str, float] = {}
    if len(entries) >= 2:
        first_weight = entries[-1].weight
        last_weight = entries[0].weight
        if first_weight is not None and last_weight is not None:
            trends["weight_change"] = round(last_weight - first_weight, 2)

    return ProgressHistoryResponse(entries=entries, total=total, trends=trends)


@router.get("/{entry_id}", response_model=ProgressLogResponse)
async def get_progress_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db["progress"].find_one({"_id": ObjectId(entry_id), "user_id": current_user["id"]})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Progress entry not found")
    doc["id"] = str(doc.pop("_id"))
    return ProgressLogResponse(**doc)
