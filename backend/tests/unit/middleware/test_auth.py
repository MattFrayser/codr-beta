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

    def test_accepts_valid_api_key(self):
        """Should accept valid API key"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers.get.return_value = "test-api-key-12345"

        # Should not raise exception
        verify_api_key(request)

    def test_rejects_invalid_api_key(self):
        """Should reject invalid API key with 403"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers.get.return_value = "wrong-api-key"

        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(request)

        assert exc_info.value.status_code == 403
        assert "Invalid API key" in str(exc_info.value.detail)

    def test_rejects_missing_api_key(self):
        """Should reject missing API key with 403"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(request)

        assert exc_info.value.status_code == 403

    def test_uses_constant_time_comparison(self):
        """Should use secrets.compare_digest for timing attack prevention"""
        import inspect

        source = inspect.getsource(verify_api_key)

        # Verify constant-time comparison is used
        assert "secrets.compare_digest" in source


class TestAuthMiddleware:
    """Test suite for authentication middleware configuration"""

    def test_excludes_health_endpoint(self):
        """Should exclude /health from authentication"""
        middleware = APIKeyMiddleware(app=Mock())

        assert "/health" in middleware.excluded_paths

    def test_excludes_docs_endpoints(self):
        """Should exclude documentation endpoints from authentication"""
        middleware = APIKeyMiddleware(app=Mock())

        assert "/docs" in middleware.excluded_paths
        assert "/redoc" in middleware.excluded_paths
        assert "/openapi.json" in middleware.excluded_paths

    def test_protects_api_endpoints(self):
        """Should protect API endpoints (not in exclusion list)"""
        middleware = APIKeyMiddleware(app=Mock())

        # Root endpoint should NOT be in excluded paths
        assert "/" not in middleware.excluded_paths

        # WebSocket status should NOT be in excluded paths
        assert "/api/websocket/status" not in middleware.excluded_paths
