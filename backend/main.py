"""
Codr - Code Execution API
Main FastAPI application entry point
"""

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add backend directory to Python path for executor imports
import sys
import os
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Rate limiting
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Import routers
from api.websocket import router as websocket_router

# Import middleware
from api.middleware.auth import APIKeyMiddleware
from api.middleware.rate_limiter import limiter

# Import async Redis manager for lifecycle management
from api.connect.redis_manager import AsyncRedisManager, get_async_redis

# Import settings
from config.settings import get_settings
settings = get_settings()

from logger.logger import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager
    Handles startup and shutdown events
    """
    try:
        redis_client = await get_async_redis()
    except Exception as e:
        log.error(f"Redis connection failed: {e}")
        raise # Failt fast 
    # Initialize services
    from api.services import JobService

    app.state.job_service = JobService(redis_client)

    if not settings.api_key:
        log.warning("API key not set")

    yield

    log.info("Shutting down...")

    # Close async Redis connection
    await AsyncRedisManager.close_connection()


# Create FastAPI app
app = FastAPI(
    title="Codr API",
    description="Secure code execution API with sandboxing",
    version="2.0.0",
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add API key middleware
app.add_middleware(APIKeyMiddleware)


# Include routers
app.include_router(websocket_router, tags=["WebSocket Execution"])


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        redis = await get_async_redis()
        redis_healthy = await redis.ping()
    except Exception:
        redis_healthy = False

    return JSONResponse(
        status_code=200 if redis_healthy else 503,
        content={
            "status": "healthy" if redis_healthy else "unhealthy",
            "service": "codr-api",
            "redis": "connected" if redis_healthy else "disconnected"
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """API information"""
    return {
        "service": "Codr API",
        "version": "2.0.0",
        "description": "Secure code execution platform",
        "endpoints": {
            "websocket": "WS /ws/execute",
            "health": "GET /health",
            "docs": "GET /docs"
        },
        "supported_languages": ["python", "javascript", "c", "cpp", "rust"]
    }


if __name__ == "__main__":
    import uvicorn

    # Get configuration from settings

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.env == "development",
        log_level="info"
    )
