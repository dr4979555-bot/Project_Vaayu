import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.limiter import limiter
from app.routers import (
    chat_router,
    alert_router,
    voice_router,
    ml_prediction_router,
)
from app.services.cache_service import CacheService
from app.services.ingestion_worker import MeteorologicalIngestionWorker


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize cache
    await CacheService.get_client()

    # 2. Start ingestion worker ONLY outside production
    is_production = (
        os.getenv("ENVIRONMENT", "").lower() == "production"
    )

    if not is_production:
        MeteorologicalIngestionWorker.start_background_worker()
        print("Meteorological ingestion worker: ENABLED")
    else:
        print("Meteorological ingestion worker: DISABLED in production")

    yield

    # 3. Graceful shutdown
    if not is_production:
        await MeteorologicalIngestionWorker.stop_background_worker()

    client = await CacheService.get_client()
    if client:
        await client.aclose()


# --------------------------------------------------
# FastAPI Application
# --------------------------------------------------

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "MoES/IMD WeatherGPT - Zero-hallucination "
        "meteorological and disaster platform"
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# --------------------------------------------------
# Rate Limiting
# --------------------------------------------------

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)

app.add_middleware(SlowAPIMiddleware)


# --------------------------------------------------
# Security Headers
# --------------------------------------------------

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' 'unsafe-inline' https:; "
        "img-src 'self' data: https:;"
    )

    return response


# --------------------------------------------------
# CORS
# --------------------------------------------------

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")

if allowed_origins_env:
    origins = [
        origin.strip()
        for origin in allowed_origins_env.split(",")
        if origin.strip()
    ]
else:
    origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Root
# --------------------------------------------------

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


# --------------------------------------------------
# Health Check
# --------------------------------------------------

@app.get("/health")
async def health():
    client = await CacheService.get_client()

    is_production = (
        os.getenv("ENVIRONMENT", "").lower() == "production"
    )

    return {
        "service": settings.PROJECT_NAME,
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "anti_hallucination_guard": "ACTIVE",
        "spatial_indexing": "PostGIS_ENABLED",
        "redis_caching": "ENABLED" if client else "BYPASS_MODE",
        "realtime_engine": "Open-Meteo (ECMWF/GFS)",
        "rate_limiting": "ENABLED",
        "alert_broadcast": "WEBSOCKETS_AND_SSE_ENABLED",
        "ingestion_worker": (
            "DISABLED (production)"
            if is_production
            else "ACTIVE (15-min cycle)"
        ),
        "indic_voice_pipeline": "ENABLED (hi, bn, mr, en)",
        "ml_prediction": "ENABLED",
    }


# --------------------------------------------------
# Admin Manual Ingestion
# --------------------------------------------------

@app.post(
    "/api/v1/admin/ingest-now",
    tags=["Meteorological Ingestion Worker"],
    summary=(
        "Trigger an immediate meteorological ingestion "
        "cycle into PostGIS"
    ),
)
@limiter.limit("5/minute")
async def trigger_manual_ingestion(request: Request):
    """
    Manually triggers a live weather ingestion cycle
    across all primary Indian stations.
    """
    result = await MeteorologicalIngestionWorker.run_ingestion_cycle()
    return result


# --------------------------------------------------
# Routers
# --------------------------------------------------

app.include_router(
    chat_router,
    prefix="/api/v1/chat",
    tags=["Conversational Weather"],
)

app.include_router(
    alert_router,
    prefix="/api/v1/alerts",
    tags=["Disaster Alerts (CAP v1.2)"],
)

app.include_router(
    voice_router,
    prefix="/api/v1/voice",
    tags=["Bhashini Indic Voice Pipeline"],
)

app.include_router(
    ml_prediction_router,
    prefix="/api/v1/ml",
    tags=["Machine Learning"],
)