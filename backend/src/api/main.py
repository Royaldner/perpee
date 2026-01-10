"""
FastAPI application entry point for Perpee.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from src.api.routes import (
    alerts_router,
    chat_router,
    health_router,
    products_router,
    schedules_router,
    stores_router,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Startup: Initialize database, seed stores, start scheduler.
    Shutdown: Clean up resources.
    """
    # Startup
    logger.info("Starting Perpee...")

    # Ensure data directory exists
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)

    # Seed stores if needed
    try:
        from config.stores_seed import seed_stores
        from src.database.session import get_session

        async with get_session() as session:
            await seed_stores(session)
            await session.commit()
        logger.info("Stores seeded successfully")
    except Exception as e:
        logger.warning(f"Failed to seed stores: {e}")

    # Start scheduler (if configured)
    try:
        from src.scheduler.service import get_scheduler_service

        scheduler = get_scheduler_service()
        scheduler.start()
        logger.info("Scheduler started")
    except Exception as e:
        logger.warning(f"Failed to start scheduler: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Perpee...")

    # Stop scheduler
    try:
        from src.scheduler.service import get_scheduler_service

        scheduler = get_scheduler_service()
        scheduler.shutdown()
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.warning(f"Failed to stop scheduler: {e}")


# Create FastAPI app
app = FastAPI(
    title="Perpee",
    description="AI-powered price monitoring agent for Canadian online retailers",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(health_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(schedules_router, prefix="/api")
app.include_router(stores_router, prefix="/api")
app.include_router(chat_router, prefix="/api/chat")

# Mount static files for frontend (production)
# The frontend build is placed in frontend/dist
frontend_path = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
    logger.info(f"Serving frontend from {frontend_path}")


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "Perpee API",
        "version": "0.1.0",
        "description": "AI-powered price monitoring for Canadian retailers",
        "docs": "/docs",
        "health": "/api/health",
    }
