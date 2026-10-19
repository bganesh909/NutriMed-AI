import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import close_mongo, close_redis, connect_mongo, connect_redis

logger = logging.getLogger("nutrimed")


def _configure_logging() -> None:
    """
    Configure application logging.

    Without this only uvicorn's own access log reaches stdout: every
    logger.info/warning in the app -- including the grounding self-check and
    the "falling back to template" warnings -- is silently discarded, which
    makes a degraded deployment invisible.
    """
    level = getattr(logging, str(settings.LOG_LEVEL).upper(), logging.INFO)
    root = logging.getLogger("nutrimed")
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"))
        root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


_configure_logging()


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    # First, so a production deployment with placeholder secrets fails fast.
    from app.core.secrets_check import enforce_secrets

    enforce_secrets(settings)

    logger.info("Connecting to MongoDB...")
    await connect_mongo()
    logger.info("MongoDB connected.")

    from app.core.database import get_database
    from app.db.indexes import ensure_indexes

    try:
        await ensure_indexes(get_database())
    except Exception:
        # Never block startup on index maintenance; the API works without them.
        logger.exception("Could not ensure MongoDB indexes")

    logger.info("Connecting to Redis...")
    await connect_redis()
    logger.info("Redis connected.")

    # Surface a degraded deployment at boot rather than letting every user
    # silently receive template plans.
    from app.services.grounding_selfcheck import log_startup_selfcheck

    log_startup_selfcheck()

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
# CORS is registered last, below, so that it is the outermost middleware.
# ---------------------------------------------------------------------------


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

# Added last = outermost. Preflight requests are then answered before the rate
# limiter counts them, and responses produced by inner middleware (such as a
# 429) still carry CORS headers, so the browser lets the app read them.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Lets the web app read the filename of PDF downloads.
    expose_headers=["Content-Disposition"],
)


# ---------------------------------------------------------------------------
# Router includes  (api/v1/endpoints/)
# ---------------------------------------------------------------------------

from app.api.v1.endpoints import (  # noqa: E402
    admin,
    auth,
    fitness,
    notifications,
    nutrition,
    pdf,
    progress,
    recommendations,
    reports,
    suggestions,
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
app.include_router(suggestions.router, prefix=API_V1_PREFIX, tags=["Suggestions"])
app.include_router(notifications.router, prefix=API_V1_PREFIX, tags=["Notifications"])
app.include_router(admin.router, prefix=API_V1_PREFIX, tags=["Admin"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Health"])
async def health_check():
    """Liveness: the process is up. Kept cheap for container health checks."""
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness, including the things plan accuracy depends on.

    Plain liveness is not enough here: this service degrades quietly. With the
    curated datasets missing or the LLM unreachable it still answers requests
    and still returns plans -- just template ones, for every user, indefinitely.
    That is worth surfacing rather than reporting a bare "ok".
    """
    from app.core.database import get_database
    from app.services.generation_metrics import summarise
    from app.services.grounding_selfcheck import check_grounding_data

    checks: dict = {}
    degraded: list[str] = []

    # --- MongoDB ---
    try:
        db = get_database()
        await db.command("ping")
        checks["mongodb"] = "ok"
    except Exception as exc:
        checks["mongodb"] = f"error: {exc}"
        degraded.append("mongodb")
        db = None

    # --- Curated grounding data ---
    grounding = check_grounding_data()
    checks["grounding"] = {
        "ok": grounding["ok"],
        "foods": grounding.get("foods"),
        "exercises": grounding.get("exercises"),
        "problems": grounding["problems"],
    }
    if not grounding["ok"]:
        degraded.append("grounding")

    # --- LLM ---
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            available = {m.get("name") for m in resp.json().get("models", [])}
        if settings.OLLAMA_MODEL in available:
            checks["llm"] = {"status": "ok", "model": settings.OLLAMA_MODEL}
        else:
            checks["llm"] = {
                "status": "model_not_pulled",
                "model": settings.OLLAMA_MODEL,
                "available": sorted(available),
            }
            degraded.append("llm")
    except Exception as exc:
        checks["llm"] = {"status": f"unreachable: {exc}", "model": settings.OLLAMA_MODEL}
        degraded.append("llm")

    # --- OCR service ---
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.OCR_SERVICE_URL}/health")
            resp.raise_for_status()
            body = resp.json()
        checks["ocr"] = {"status": "ok", "engine": body.get("ocr_engine")}
        if not body.get("ocr_engine"):
            degraded.append("ocr_engine")
    except Exception as exc:
        checks["ocr"] = {"status": f"unreachable: {exc}"}
        degraded.append("ocr")

    # --- Recent generation quality ---
    if db is not None:
        checks["generation_quality"] = await summarise(db, days=7)

    return {
        "status": "degraded" if degraded else "ready",
        "degraded": degraded,
        "checks": checks,
    }
