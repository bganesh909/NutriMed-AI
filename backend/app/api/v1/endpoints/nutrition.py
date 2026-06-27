from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user, get_db
from app.repositories.diet_plan_repository import DietPlanRepository
from app.services.nutrition_service import NutritionService
from app.schemas.nutrition import MacroBreakdown, NutritionCalculation

router = APIRouter(prefix="/nutrition")


class NutritionCalcRequest(BaseModel):
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    activity_level: str = "moderate"
    goal: str = "maintenance"
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    neck_cm: Optional[float] = None


class GenerateDietRequest(BaseModel):
    goal: str = "maintenance"
    dietary_restrictions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)


@router.post("/calculate", response_model=NutritionCalculation)
async def calculate_nutrition(
    body: NutritionCalcRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    service = NutritionService(DietPlanRepository(db))

    weight = body.weight_kg or current_user.get("weight") or 70.0
    height = body.height_cm or current_user.get("height") or 170.0
    age = body.age or current_user.get("age") or 25
    gender = body.gender or current_user.get("gender", "male")

    result = service.calculate_all(
        weight_kg=weight,
        height_cm=height,
        age=age,
        gender=gender,
        activity_level=body.activity_level,
        goal=body.goal,
        waist_cm=body.waist_cm,
        hip_cm=body.hip_cm,
        neck_cm=body.neck_cm,
    )

    return NutritionCalculation(
        bmr=result["bmr"],
        tdee=result["tdee"],
        bmi=result["bmi"],
        bmi_category=result["bmi_category"],
        body_fat_estimate=result["body_fat_estimate"],
        target_calories=result["target_calories"],
        macros=MacroBreakdown(**result["macros"]),
    )


@router.get("/calculate", response_model=NutritionCalculation)
async def calculate_nutrition_from_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Calculate nutrition using stored user profile data."""
    service = NutritionService(DietPlanRepository(db))

    weight = current_user.get("weight") or 70.0
    height = current_user.get("height") or 170.0
    age = current_user.get("age") or 25
    gender = current_user.get("gender", "male")
    activity = current_user.get("activity_level", "moderately_active")
    goals = current_user.get("goals", [])
    goal = "maintenance"
    if "weight_loss" in goals:
        goal = "weight_loss"
    elif "muscle_gain" in goals:
        goal = "muscle_gain"

    result = service.calculate_all(
        weight_kg=weight,
        height_cm=height,
        age=age,
        gender=gender,
        activity_level=activity,
        goal=goal,
    )

    return NutritionCalculation(
        bmr=result["bmr"],
        tdee=result["tdee"],
        bmi=result["bmi"],
        bmi_category=result["bmi_category"],
        body_fat_estimate=result["body_fat_estimate"],
        target_calories=result["target_calories"],
        macros=MacroBreakdown(**result["macros"]),
    )


@router.post("/generate-diet", status_code=status.HTTP_201_CREATED)
async def generate_diet_plan(
    body: GenerateDietRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Generate a personalised diet plan using the LLM service."""
    service = NutritionService(DietPlanRepository(db))
    result = await service.generate_diet_plan(
        user_id=current_user["id"],
        user_profile=current_user,
        goal=body.goal,
        dietary_restrictions=body.dietary_restrictions,
        allergies=body.allergies,
    )
    return result
