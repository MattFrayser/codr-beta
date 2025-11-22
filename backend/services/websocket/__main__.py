"""
WebSocket Server Entry Point
Starts the FastAPI application w/ middleware and routes configured.
"""

# Load environment first
from dotenv import load_dotenv

load_dotenv()

import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Import from service-specific modules
from .routes import router as websocket_router
from .middleware.auth import APIKeyMiddleware
from .middleware.rate_limiter import limiter

# Import from shared lib
from lib.redis import AsyncRedisManager, get_async_redis
from lib.services import JobService
from lib.config import get_settings
settings = get_settings()

from lib.logger import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager (startup and shutdown events)"""

    try:
        redis_client = await get_async_redis()
    except Exception as e:
        log.error(f"Redis connection failed: {e}")
        raise  # Fail fast

    app.state.job_service = JobService(redis_client)

    if not settings.api_key and settings.env != "development":
        log.error("API key not set")
        raise

    log.info("Websocket server started")

    yield

    log.info("Shutting down websocket server...")
    await AsyncRedisManager.close_connection()


def create_app() -> FastAPI:
    """Create FastAPI app"""

    app = FastAPI(
        title="Codr API",
        description="Secure code execution API with sandboxing",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Add rate limiter to app state
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

    # Root endpoint
    @app.get("/")
    async def root():
        """API information"""
        return {
            "service": "Codr Websocket Server",
            "version": "2.0.0",
            "description": "Secure code execution platform",
            "endpoints": {
                "websocket": "WS /ws/execute",
                "health": "GET /health",
                "status": "GET /api/websocket/status",
            },
        }

    # Health check endpoint
    @app.get("/health")
    async def health_check():
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
                "redis": "connected" if redis_healthy else "disconnected",
            },
        )

    return app


if __name__ == "__main__":

    app = create_app()

    uvicorn.run(
        app, host=settings.host, port=settings.port, reload=False, log_level="info"
    )
