"""
Main API v1 router -- aggregates all endpoint routers with proper prefixes and tags.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    fitness,
    nutrition,
    pdf,
    progress,
    recommendations,
    reports,
    users,
)

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, tags=["Auth"])
api_v1_router.include_router(users.router, tags=["Users"])
api_v1_router.include_router(reports.router, tags=["Reports"])
api_v1_router.include_router(nutrition.router, tags=["Nutrition"])
api_v1_router.include_router(fitness.router, tags=["Fitness"])
api_v1_router.include_router(recommendations.router, tags=["Recommendations"])
api_v1_router.include_router(progress.router, tags=["Progress"])
api_v1_router.include_router(pdf.router, tags=["PDF"])
