import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import close_mongo, close_redis, connect_mongo, connect_redis

logger = logging.getLogger("nutrimed")


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Connecting to MongoDB...")
    await connect_mongo()
    logger.info("MongoDB connected.")

    logger.info("Connecting to Redis...")
    await connect_redis()
    logger.info("Redis connected.")

    yield

    # --- Shutdown ---
    logger.info("Closing MongoDB connection...")
    await close_mongo()
    logger.info("MongoDB disconnected.")

    logger.info("Closing Redis connection...")
    await close_redis()
    logger.info("Redis disconnected.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    description="Healthcare + Nutrition + Fitness AI platform",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug("%s %s", request.method, request.url.path)
    response = await call_next(request)
    return response


# ---------------------------------------------------------------------------
# Custom middleware (audit logging, rate limiting)
# ---------------------------------------------------------------------------

from app.middleware.audit_logging import AuditLoggingMiddleware  # noqa: E402
from app.middleware.rate_limiting import RateLimitingMiddleware  # noqa: E402

app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(RateLimitingMiddleware, max_requests=60, window_seconds=60)


# ---------------------------------------------------------------------------
# Router includes  (api/v1/endpoints/)
# ---------------------------------------------------------------------------

from app.api.v1.endpoints import (  # noqa: E402
    auth,
    fitness,
    nutrition,
    pdf,
    progress,
    recommendations,
    reports,
    users,
)

API_V1_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_V1_PREFIX, tags=["Auth"])
app.include_router(users.router, prefix=API_V1_PREFIX, tags=["Users"])
app.include_router(reports.router, prefix=API_V1_PREFIX, tags=["Reports"])
app.include_router(nutrition.router, prefix=API_V1_PREFIX, tags=["Nutrition"])
app.include_router(fitness.router, prefix=API_V1_PREFIX, tags=["Fitness"])
app.include_router(recommendations.router, prefix=API_V1_PREFIX, tags=["Recommendations"])
app.include_router(progress.router, prefix=API_V1_PREFIX, tags=["Progress"])
app.include_router(pdf.router, prefix=API_V1_PREFIX, tags=["PDF"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
