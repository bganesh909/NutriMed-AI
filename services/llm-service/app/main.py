import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.ollama_client import OllamaClient, get_ollama_client
from app.prompt_manager import PromptManager, get_prompt_manager
from app.schemas import (
    DietPlanRequest,
    DietPlanResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    LabAnalysisRequest,
    LabAnalysisResponse,
    ModelInfo,
    ModelsResponse,
    SupplementRequest,
    SupplementResponse,
    WorkoutPlanRequest,
    WorkoutPlanResponse,
)

settings = get_settings()

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.SERVICE_NAME, settings.SERVICE_VERSION)
    client = get_ollama_client()
    healthy = await client.is_healthy()
    if healthy:
        logger.info("Ollama connection established at %s", settings.OLLAMA_BASE_URL)
    else:
        logger.warning("Ollama not reachable at %s — will retry on requests", settings.OLLAMA_BASE_URL)
    yield
    await client.close()
    logger.info("Shut down %s", settings.SERVICE_NAME)


app = FastAPI(
    title="NutriMed AI - LLM Service",
    description="LLM inference service powered by Ollama for health analysis and plan generation",
    version=settings.SERVICE_VERSION,
    lifespan=lifespan,
)


def _parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        start = 1
        end = len(lines)
        for i in range(1, len(lines)):
            if lines[i].strip() == "```":
                end = i
                break
        cleaned = "\n".join(lines[start:end]).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass
        return {"raw_response": text}


@app.post("/llm/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Generic text generation endpoint."""
    client = get_ollama_client()
    model = request.model or settings.DEFAULT_MODEL
    temperature = request.temperature if request.temperature is not None else settings.DEFAULT_TEMPERATURE
    max_tokens = request.max_tokens or settings.DEFAULT_MAX_TOKENS

    try:
        result = await client.generate(
            model=model,
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return GenerateResponse(
            text=result["text"],
            model=result["model"],
            tokens_used=result["tokens_used"],
            duration_ms=result["duration_ms"],
        )
    except Exception as exc:
        logger.error("Generation failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {exc}")


@app.post("/llm/analyze-labs", response_model=LabAnalysisResponse)
async def analyze_labs(request: LabAnalysisRequest):
    """Analyze lab biomarkers and provide medical interpretation."""
    client = get_ollama_client()
    pm = get_prompt_manager()
    model = request.model or settings.DEFAULT_MODEL

    try:
        prompt = pm.render(
            "lab_analysis",
            age=request.age,
            gender=request.gender,
            weight=request.weight,
            height=request.height,
            activity_level=request.activity_level,
            conditions=", ".join(request.conditions) if request.conditions else "None",
            biomarker_json=request.biomarkers,
            reference_ranges=request.reference_ranges or "Use standard medical reference ranges",
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        result = await client.generate(
            model=model,
            prompt=prompt,
            temperature=0.2,
            max_tokens=settings.DEFAULT_MAX_TOKENS,
        )
        analysis = _parse_json_response(result["text"])
        return LabAnalysisResponse(
            analysis=analysis,
            model=result["model"],
            tokens_used=result["tokens_used"],
            duration_ms=result["duration_ms"],
        )
    except Exception as exc:
        logger.error("Lab analysis failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Lab analysis failed: {exc}")


@app.post("/llm/generate-diet", response_model=DietPlanResponse)
async def generate_diet(request: DietPlanRequest):
    """Generate a personalized diet plan."""
    client = get_ollama_client()
    pm = get_prompt_manager()
    model = request.model or settings.DEFAULT_MODEL

    bmr = _calculate_bmr(request.weight, request.height, request.age, request.gender)
    calories = request.calories or _estimate_tdee(bmr, request.activity_level, request.goal)
    protein_g = request.protein_g or round(request.weight * 1.6, 1)
    fat_g = request.fat_g or round(calories * 0.25 / 9, 1)
    carbs_g = request.carbs_g or round((calories - protein_g * 4 - fat_g * 9) / 4, 1)

    try:
        prompt = pm.render(
            "diet_generation",
            age=request.age,
            gender=request.gender,
            weight=request.weight,
            height=request.height,
            activity_level=request.activity_level,
            goal=request.goal,
            dietary_preference=request.dietary_preference,
            allergies=", ".join(request.allergies) if request.allergies else "None",
            conditions=", ".join(request.conditions) if request.conditions else "None",
            calories=calories,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            biomarker_considerations=request.biomarker_considerations or "None provided",
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        result = await client.generate(
            model=model,
            prompt=prompt,
            temperature=0.4,
            max_tokens=settings.DEFAULT_MAX_TOKENS,
        )
        plan = _parse_json_response(result["text"])
        return DietPlanResponse(
            plan=plan,
            model=result["model"],
            tokens_used=result["tokens_used"],
            duration_ms=result["duration_ms"],
        )
    except Exception as exc:
        logger.error("Diet plan generation failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Diet plan generation failed: {exc}")


@app.post("/llm/generate-workout", response_model=WorkoutPlanResponse)
async def generate_workout(request: WorkoutPlanRequest):
    """Generate a personalized workout plan."""
    client = get_ollama_client()
    pm = get_prompt_manager()
    model = request.model or settings.DEFAULT_MODEL

    try:
        prompt = pm.render(
            "workout_generation",
            age=request.age,
            gender=request.gender,
            weight=request.weight,
            height=request.height,
            activity_level=request.activity_level,
            goal=request.goal,
            fitness_level=request.fitness_level,
            conditions=", ".join(request.conditions) if request.conditions else "None",
            injuries=", ".join(request.injuries) if request.injuries else "None",
            available_equipment=", ".join(request.available_equipment),
            days_per_week=request.days_per_week,
            session_duration_minutes=request.session_duration_minutes,
            biomarker_considerations=request.biomarker_considerations or "None provided",
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        result = await client.generate(
            model=model,
            prompt=prompt,
            temperature=0.4,
            max_tokens=settings.DEFAULT_MAX_TOKENS,
        )
        plan = _parse_json_response(result["text"])
        return WorkoutPlanResponse(
            plan=plan,
            model=result["model"],
            tokens_used=result["tokens_used"],
            duration_ms=result["duration_ms"],
        )
    except Exception as exc:
        logger.error("Workout plan generation failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Workout plan generation failed: {exc}")


@app.post("/llm/suggest-supplements", response_model=SupplementResponse)
async def suggest_supplements(request: SupplementRequest):
    """Generate evidence-based supplement recommendations."""
    client = get_ollama_client()
    pm = get_prompt_manager()
    model = request.model or settings.DEFAULT_MODEL

    try:
        prompt = pm.render(
            "supplement_recommendation",
            age=request.age,
            gender=request.gender,
            weight=request.weight,
            conditions=", ".join(request.conditions) if request.conditions else "None",
            current_medications=", ".join(request.current_medications) if request.current_medications else "None",
            current_supplements=", ".join(request.current_supplements) if request.current_supplements else "None",
            biomarkers=request.biomarkers,
            goal=request.goal,
            dietary_preference=request.dietary_preference,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        result = await client.generate(
            model=model,
            prompt=prompt,
            temperature=0.3,
            max_tokens=settings.DEFAULT_MAX_TOKENS,
        )
        recommendations = _parse_json_response(result["text"])
        return SupplementResponse(
            recommendations=recommendations,
            model=result["model"],
            tokens_used=result["tokens_used"],
            duration_ms=result["duration_ms"],
        )
    except Exception as exc:
        logger.error("Supplement suggestion failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Supplement suggestion failed: {exc}")


@app.get("/llm/models", response_model=ModelsResponse)
async def list_models():
    """List all available Ollama models."""
    client = get_ollama_client()
    try:
        models_data = await client.list_models()
        models = [ModelInfo(**m) for m in models_data]
        return ModelsResponse(models=models)
    except Exception as exc:
        logger.error("Failed to list models: %s", exc)
        raise HTTPException(status_code=502, detail=f"Failed to list models: {exc}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    client = get_ollama_client()
    ollama_ok = await client.is_healthy()
    return HealthResponse(
        status="healthy" if ollama_ok else "degraded",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        ollama_connected=ollama_ok,
    )


def _calculate_bmr(weight: float, height: float, age: int, gender: str) -> float:
    """Mifflin-St Jeor equation for BMR."""
    if gender == "male":
        return 10 * weight + 6.25 * height - 5 * age + 5
    else:
        return 10 * weight + 6.25 * height - 5 * age - 161


def _estimate_tdee(bmr: float, activity_level: str, goal: str) -> int:
    """Estimate Total Daily Energy Expenditure."""
    multipliers = {
        "sedentary": 1.2,
        "lightly_active": 1.375,
        "moderately_active": 1.55,
        "very_active": 1.725,
        "extremely_active": 1.9,
    }
    tdee = bmr * multipliers.get(activity_level, 1.55)
    adjustments = {
        "weight_loss": -500,
        "aggressive_weight_loss": -750,
        "muscle_gain": 300,
        "lean_bulk": 200,
        "maintenance": 0,
    }
    return int(tdee + adjustments.get(goal, 0))
