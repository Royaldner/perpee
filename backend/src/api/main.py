"""
FastAPI application entry point for Perpee.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Startup: Initialize database, seed stores, start scheduler.
    Shutdown: Clean up resources.
    """
    # Startup
    print("Starting Perpee...")

    # Ensure data directory exists
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)

    yield

    # Shutdown
    print("Shutting down Perpee...")


# Create FastAPI app
app = FastAPI(
    title="Perpee",
    description="AI-powered price monitoring agent for Canadian online retailers",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - redirect to docs."""
    return {"message": "Welcome to Perpee API", "docs": "/docs"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.environment,
    }


@app.get("/api/stats")
async def stats():
    """
    Dashboard statistics endpoint.
    Returns basic stats about tracked products, alerts, etc.
    """
    # TODO: Implement actual stats from database
    return {
        "products": {
            "total": 0,
            "active": 0,
            "needs_attention": 0,
        },
        "alerts": {
            "total": 0,
            "active": 0,
            "triggered_today": 0,
        },
        "stores": {
            "total": 16,
            "healthy": 16,
        },
    }
