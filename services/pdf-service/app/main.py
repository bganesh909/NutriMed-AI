"""
NutriMed AI - PDF Report Service
FastAPI application for generating PDF health reports, diet plans, and workout plans.
"""

import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import get_settings
from app.schemas import (
    HealthReportRequest,
    DietPlanPDFRequest,
    WorkoutPlanPDFRequest,
    PDFResponse,
    HealthResponse,
)
from app.report_generator import (
    generate_health_report,
    generate_diet_plan_pdf,
    generate_workout_plan_pdf,
)

settings = get_settings()

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NutriMed AI - PDF Report Service",
    description="Generate professional PDF health reports, diet plans, and workout plans",
    version=settings.SERVICE_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/pdf/generate-report", response_model=PDFResponse)
async def generate_report(request: HealthReportRequest):
    """Generate a comprehensive health report PDF."""
    try:
        report_data = request.model_dump()
        result = generate_health_report(report_data)
        return PDFResponse(**result)
    except Exception as e:
        logger.error(f"Report generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pdf/generate-diet-plan", response_model=PDFResponse)
async def generate_diet_plan(request: DietPlanPDFRequest):
    """Generate a diet plan PDF."""
    try:
        data = request.model_dump()
        result = generate_diet_plan_pdf(data)
        return PDFResponse(**result)
    except Exception as e:
        logger.error(f"Diet plan PDF error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pdf/generate-workout-plan", response_model=PDFResponse)
async def generate_workout_plan(request: WorkoutPlanPDFRequest):
    """Generate a workout plan PDF."""
    try:
        data = request.model_dump()
        result = generate_workout_plan_pdf(data)
        return PDFResponse(**result)
    except Exception as e:
        logger.error(f"Workout plan PDF error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pdf/download/{filename}")
async def download_pdf(filename: str):
    """Download a generated PDF file."""
    file_path = os.path.join(settings.OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename,
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
    )
