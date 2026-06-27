"""
NutriMed AI - Nutrition Service
FastAPI application for nutrition calculations and diet plan generation.
"""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.schemas import (
    NutritionCalculateRequest,
    NutritionCalculateResponse,
    DietGenerateRequest,
    DietPlanResponse,
    MealPlanRequest,
    MealPlanResponse,
    HealthResponse,
)
from app.calculator import (
    calculate_bmr,
    calculate_tdee,
    calculate_bmi,
    get_bmi_category,
    estimate_body_fat,
    calculate_macros,
    calculate_hydration,
)
from app.diet_generator import (
    generate_template_diet_plan,
    generate_llm_diet_plan,
    generate_single_meal_plan,
)

settings = get_settings()

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NutriMed AI - Nutrition Service",
    description="Nutrition calculations, diet plans, and meal planning",
    version=settings.SERVICE_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/nutrition/calculate", response_model=NutritionCalculateResponse)
async def calculate_nutrition(request: NutritionCalculateRequest):
    """Calculate BMR, TDEE, BMI, body fat percentage, and macronutrient targets."""
    try:
        bmr = calculate_bmr(request.weight_kg, request.height_cm, request.age, request.gender)
        tdee = calculate_tdee(bmr, request.activity_level)
        bmi = calculate_bmi(request.weight_kg, request.height_cm)
        bmi_category = get_bmi_category(bmi)
        macros = calculate_macros(tdee, request.goal, request.weight_kg)
        hydration = calculate_hydration(request.weight_kg, request.activity_level)

        body_fat = None
        if request.waist_cm and request.neck_cm:
            body_fat = estimate_body_fat(
                request.waist_cm,
                request.neck_cm,
                request.height_cm,
                request.hip_cm,
                request.gender,
            )

        return NutritionCalculateResponse(
            bmr=round(bmr, 1),
            tdee=tdee,
            bmi=bmi,
            bmi_category=bmi_category,
            body_fat_percentage=body_fat,
            macros=macros,
            hydration_ml=hydration,
            target_calories=macros["calories"],
        )
    except Exception as e:
        logger.error(f"Calculation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/nutrition/generate-diet", response_model=DietPlanResponse)
async def generate_diet(request: DietGenerateRequest):
    """Generate a comprehensive 7-day diet plan."""
    try:
        llm_plan = None
        if request.use_llm:
            llm_plan = await generate_llm_diet_plan(
                weight_kg=request.weight_kg,
                height_cm=request.height_cm,
                age=request.age,
                gender=request.gender,
                activity_level=request.activity_level,
                goal=request.goal,
                dietary_preference=request.dietary_preference,
                cuisine_preference=request.cuisine_preference,
                conditions=request.conditions,
                allergies=request.allergies,
                target_calories=request.target_calories,
            )

        if llm_plan is None:
            # Fallback to template-based plan
            plan = generate_template_diet_plan(
                weight_kg=request.weight_kg,
                height_cm=request.height_cm,
                age=request.age,
                gender=request.gender,
                activity_level=request.activity_level,
                goal=request.goal,
                dietary_preference=request.dietary_preference,
                cuisine_preference=request.cuisine_preference,
                conditions=request.conditions,
                target_calories=request.target_calories,
            )
            return DietPlanResponse(**plan)

        # If LLM returned data, still wrap in template structure
        plan = generate_template_diet_plan(
            weight_kg=request.weight_kg,
            height_cm=request.height_cm,
            age=request.age,
            gender=request.gender,
            activity_level=request.activity_level,
            goal=request.goal,
            dietary_preference=request.dietary_preference,
            cuisine_preference=request.cuisine_preference,
            conditions=request.conditions,
            target_calories=request.target_calories,
        )
        return DietPlanResponse(**plan)

    except Exception as e:
        logger.error(f"Diet generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/nutrition/meal-plan", response_model=MealPlanResponse)
async def create_meal_plan(request: MealPlanRequest):
    """Generate a specific single-day meal plan matching target macros."""
    try:
        plan = generate_single_meal_plan(
            target_calories=request.target_calories,
            protein_g=request.protein_g,
            carbs_g=request.carbs_g,
            fat_g=request.fat_g,
            dietary_preference=request.dietary_preference,
            cuisine_preference=request.cuisine_preference,
            meal_count=request.meal_count,
            allergies=request.allergies,
            conditions=request.conditions,
        )
        return MealPlanResponse(**plan)
    except Exception as e:
        logger.error(f"Meal plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
    )
