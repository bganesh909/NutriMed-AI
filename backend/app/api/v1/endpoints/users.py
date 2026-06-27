from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.dependencies import get_current_user, get_db, require_role
from app.schemas.user import UserProfile, UserResponse, UserUpdate
from app.schemas.medical_profile import MedicalProfileCreate, MedicalProfileOut

router = APIRouter(prefix="/users")


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserProfile(**current_user)


@router.put("/me", response_model=UserProfile)
async def update_me(
    body: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    update_data["updated_at"] = datetime.now(timezone.utc)
    await db["users"].update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": update_data},
    )
    updated = await db["users"].find_one({"_id": ObjectId(current_user["id"])})
    updated["id"] = str(updated.pop("_id"))
    return UserProfile(**updated)


@router.post("/me/medical-profile", response_model=MedicalProfileOut, status_code=status.HTTP_200_OK)
async def create_or_update_medical_profile(
    body: MedicalProfileCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_id = current_user["id"]
    profile_data = body.model_dump()
    profile_data["user_id"] = user_id
    profile_data["updated_at"] = datetime.now(timezone.utc)

    existing = await db["medical_profiles"].find_one({"user_id": user_id})
    if existing:
        await db["medical_profiles"].update_one(
            {"_id": existing["_id"]},
            {"$set": profile_data},
        )
        updated = await db["medical_profiles"].find_one({"_id": existing["_id"]})
        updated["id"] = str(updated.pop("_id"))
        return MedicalProfileOut(**updated)
    else:
        result = await db["medical_profiles"].insert_one(profile_data)
        profile_data["id"] = str(result.inserted_id)
        return MedicalProfileOut(**profile_data)


@router.get("/me/medical-profile", response_model=MedicalProfileOut)
async def get_medical_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db["medical_profiles"].find_one({"user_id": current_user["id"]})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical profile not found. Create one first.",
        )
    doc["id"] = str(doc.pop("_id"))
    return MedicalProfileOut(**doc)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    _admin: dict = Depends(require_role("admin")),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_doc["id"] = str(user_doc.pop("_id"))
    return UserResponse(**user_doc)
