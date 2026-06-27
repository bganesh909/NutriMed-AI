from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user, get_db
from app.repositories.biomarker_repository import BiomarkerRepository
from app.repositories.workout_plan_repository import WorkoutPlanRepository
from app.services.fitness_service import FitnessService
from app.schemas.workout_plan import WorkoutPlanResponse

router = APIRouter(prefix="/fitness")


class GenerateWorkoutRequest(BaseModel):
    goal: str = "general_fitness"
    difficulty: str = "intermediate"
    days_per_week: int = Field(default=4, ge=1, le=7)
    conditions: list[str] = Field(default_factory=list)
    use_biomarkers: bool = True


@router.post("/generate-workout", status_code=status.HTTP_201_CREATED)
async def generate_workout_plan(
    body: GenerateWorkoutRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Generate a personalised workout plan using the LLM service."""
    workout_repo = WorkoutPlanRepository(db)
    service = FitnessService(workout_repo)

    # Optionally fetch latest biomarkers for adaptation
    biomarkers: Optional[dict] = None
    if body.use_biomarkers:
        bio_repo = BiomarkerRepository(db)
        bio_doc = await bio_repo.get_latest_by_user(current_user["id"])
        if bio_doc:
            # Extract marker values from biomarker doc
            exclude_keys = {"id", "user_id", "report_id", "created_at", "extracted_at"}
            biomarkers = {
                k: v for k, v in bio_doc.items()
                if k not in exclude_keys and v is not None and isinstance(v, (int, float))
            }
            # Also check for "markers" dict format
            if "markers" in bio_doc and isinstance(bio_doc["markers"], dict):
                biomarkers = bio_doc["markers"]

    result = await service.generate_workout_plan(
        user_id=current_user["id"],
        user_profile=current_user,
        goal=body.goal,
        difficulty=body.difficulty,
        days_per_week=body.days_per_week,
        conditions=body.conditions,
        biomarkers=biomarkers,
    )
    return result


@router.get("/workout-plans", response_model=list[WorkoutPlanResponse])
async def list_workout_plans(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    cursor = db["workout_plans"].find({"user_id": current_user["id"]}).sort("created_at", -1)
    plans = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        plans.append(WorkoutPlanResponse(**doc))
    return plans


@router.get("/workout-plans/{plan_id}", response_model=WorkoutPlanResponse)
async def get_workout_plan(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db["workout_plans"].find_one({"_id": ObjectId(plan_id), "user_id": current_user["id"]})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found")
    doc["id"] = str(doc.pop("_id"))
    return WorkoutPlanResponse(**doc)
