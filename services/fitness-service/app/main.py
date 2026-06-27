"""
NutriMed AI - Fitness Service
FastAPI application for workout plan generation and exercise management.
"""

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.schemas import (
    WorkoutGenerateRequest,
    WorkoutPlanResponse,
    AdaptWorkoutRequest,
    AdaptWorkoutResponse,
    ExerciseListResponse,
    ExerciseInfo,
    HealthResponse,
)
from app.workout_generator import generate_workout_plan
from app.adaptation_engine import adapt_workout
from app.exercise_database import (
    get_all_exercises,
    get_exercises_by_muscle_group,
    get_exercises_by_equipment,
    get_exercises_filtered,
    search_exercises,
)

settings = get_settings()

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NutriMed AI - Fitness Service",
    description="Workout generation, exercise database, and health-aware adaptations",
    version=settings.SERVICE_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/fitness/generate-workout", response_model=WorkoutPlanResponse)
async def generate_workout(request: WorkoutGenerateRequest):
    """Generate a complete weekly workout plan based on user profile."""
    try:
        plan = generate_workout_plan(
            age=request.age,
            gender=request.gender,
            weight_kg=request.weight_kg,
            height_cm=request.height_cm,
            fitness_level=request.fitness_level,
            goal=request.goal,
            days_per_week=request.days_per_week,
            session_duration_minutes=request.session_duration_minutes,
            available_equipment=request.available_equipment,
            conditions=request.conditions,
            injuries=request.injuries,
        )
        return WorkoutPlanResponse(**plan)
    except Exception as e:
        logger.error(f"Workout generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/fitness/adapt-workout", response_model=AdaptWorkoutResponse)
async def adapt_workout_endpoint(request: AdaptWorkoutRequest):
    """Adapt an existing workout plan based on health conditions and biomarkers."""
    try:
        result = adapt_workout(
            workout_plan=request.workout_plan,
            biomarkers=request.biomarkers,
            conditions=request.conditions,
            injuries=request.injuries,
        )
        return AdaptWorkoutResponse(**result)
    except Exception as e:
        logger.error(f"Workout adaptation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fitness/exercises", response_model=ExerciseListResponse)
async def list_exercises(
    muscle_group: Optional[str] = Query(None, description="Filter by muscle group"),
    equipment: Optional[str] = Query(None, description="Filter by equipment type"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    search: Optional[str] = Query(None, description="Search by exercise name"),
):
    """List exercises from the database with optional filters."""
    try:
        if search:
            exercises = search_exercises(search)
        elif muscle_group or equipment or difficulty:
            equip_list = [equipment] if equipment else None
            exercises = get_exercises_filtered(
                muscle_group=muscle_group,
                equipment=equip_list,
                difficulty=difficulty,
            )
        else:
            exercises = get_all_exercises()

        exercise_infos = [
            ExerciseInfo(
                name=ex["name"],
                muscle_group=ex["muscle_group"],
                equipment=ex["equipment"],
                difficulty=ex["difficulty"],
                instructions=ex["instructions"],
                alternatives=ex.get("alternatives", []),
            )
            for ex in exercises
        ]

        return ExerciseListResponse(
            exercises=exercise_infos,
            total_count=len(exercise_infos),
        )
    except Exception as e:
        logger.error(f"Exercise listing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
    )
