"""
API key authentication 
"""

import secrets
from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from config.settings import get_settings


API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(request: Request, api_key: str = None):

    settings = get_settings()
    expected_api_key = settings.api_key

    if not expected_api_key and settings.env == 'development':
        # allow all requests in dev mode
        return True

    # Get API key from header
    if not api_key:
        api_key = request.headers.get(API_KEY_NAME)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(api_key, expected_api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return True


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Check API key on all requests
    """

    async def dispatch(self, request: Request, call_next):
        # These paths dont need auth
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        try:
            await verify_api_key(request)
        except HTTPException as e:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )

        return await call_next(request)
