"""
Tests for Authentication Middleware

Covers:
- API key validation
- Timing attack prevention
- Path exclusions
- HTTP exception handling
"""

import pytest
from fastapi import HTTPException
from unittest.mock import Mock
from api.middleware.auth import verify_api_key, APIKeyMiddleware


class TestAPIKeyValidation:
    """Test suite for API key validation"""

    @pytest.mark.asyncio
    async def test_accepts_valid_api_key(self):
        """Should accept valid API key"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers.get.return_value = "test-api-key-12345"

        # Should not raise exception
        result = await verify_api_key(request)
        assert result is True

    @pytest.mark.asyncio
    async def test_rejects_invalid_api_key(self):
        """Should reject invalid API key with 403"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers.get.return_value = "wrong-api-key"

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(request)

        assert exc_info.value.status_code == 403
        assert "Invalid API key" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_rejects_missing_api_key(self):
        """Should reject missing API key with 401"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(request)

        assert exc_info.value.status_code == 401

    def test_uses_constant_time_comparison(self):
        """Should use secrets.compare_digest for timing attack prevention"""
        import inspect

        source = inspect.getsource(verify_api_key)

        # Verify constant-time comparison is used
        assert "secrets.compare_digest" in source


class TestAuthMiddleware:
    """Test suite for authentication middleware configuration"""

    @pytest.mark.asyncio
    async def test_excludes_health_endpoint(self):
        """Should exclude /health from authentication"""
        from fastapi import Request
        from unittest.mock import AsyncMock

        middleware = APIKeyMiddleware(app=Mock())

        # Create mock request for /health
        request = Mock(spec=Request)
        request.url.path = "/health"

        # Mock call_next
        call_next = AsyncMock(return_value=Mock())

        # Should call next without checking auth
        await middleware.dispatch(request, call_next)
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_excludes_docs_endpoints(self):
        """Should exclude documentation endpoints from authentication"""
        from fastapi import Request
        from unittest.mock import AsyncMock

        middleware = APIKeyMiddleware(app=Mock())

        # Test /docs endpoint
        request = Mock(spec=Request)
        request.url.path = "/docs"
        call_next = AsyncMock(return_value=Mock())

        await middleware.dispatch(request, call_next)
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_protects_api_endpoints(self):
        """Should protect API endpoints by requiring authentication"""
        from fastapi import Request
        from fastapi.responses import JSONResponse
        from unittest.mock import AsyncMock

        middleware = APIKeyMiddleware(app=Mock())

        # Create mock request for protected endpoint
        request = Mock(spec=Request)
        request.url.path = "/api/execute"
        request.headers.get.return_value = None  # No API key

        # Mock call_next
        call_next = AsyncMock()

        # Should return 401 error without calling next
        response = await middleware.dispatch(request, call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
        call_next.assert_not_called()
