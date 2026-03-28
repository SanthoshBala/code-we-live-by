"""FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.config import settings
from app.core.cache_middleware import CacheControlMiddleware
from app.core.logging_middleware import RequestLoggingMiddleware
from app.models.base import engine

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """Warm up the database connection pool on startup.

    Cloud Run cold starts pay ~1-2s for the first DB connection to Cloud SQL.
    Priming the pool here moves that cost to container startup (before the
    readiness probe passes) instead of penalising the first user request.
    """
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connection pool warmed up")
    yield


app = FastAPI(
    title="The Code We Live By API",
    description="API for exploring the US Code as a version-controlled repository",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Middleware (order matters — outermost first)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CacheControlMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
