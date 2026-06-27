from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.core.dependencies import get_current_user, get_db
from app.repositories.biomarker_repository import BiomarkerRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workout_plan_repository import WorkoutPlanRepository
from app.repositories.diet_plan_repository import DietPlanRepository
from app.services.lab_interpretation_service import LabInterpretationService
from app.services.nutrition_service import NutritionService
from app.services.fitness_service import FitnessService
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations")


class GenerateRequest(BaseModel):
    report_id: Optional[str] = None


def _build_recommendation_service(db: AsyncIOMotorDatabase) -> RecommendationService:
    return RecommendationService(
        recommendation_repo=RecommendationRepository(db),
        biomarker_repo=BiomarkerRepository(db),
        user_repo=UserRepository(db),
        lab_service=LabInterpretationService(),
        nutrition_service=NutritionService(DietPlanRepository(db)),
        fitness_service=FitnessService(WorkoutPlanRepository(db)),
    )


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_recommendation(
    body: GenerateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    service = _build_recommendation_service(db)
    result = await service.generate(
        user_id=current_user["id"],
        report_id=body.report_id,
    )
    return result


@router.get("/", response_model=list[dict])
async def list_recommendations(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    service = _build_recommendation_service(db)
    return await service.get_recommendations(current_user["id"])


@router.get("/latest")
async def get_latest_recommendation(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    service = _build_recommendation_service(db)
    return await service.get_latest(current_user["id"])


@router.get("/{user_id}")
async def get_user_recommendations(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    # Users can only access their own recommendations unless admin
    if current_user["id"] != user_id and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    service = _build_recommendation_service(db)
    return await service.get_recommendations(user_id)
