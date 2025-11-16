"""
Unit tests for API Key Authentication Middleware

Tests authentication behavior:
- Valid API key acceptance
- Invalid API key rejection
- Missing API key rejection
- Constant-time comparison (security)
- Path exclusion
"""

import pytest
import secrets
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


@pytest.mark.unit
class TestAuthMiddleware:
    """Test suite for authentication middleware"""

    def test_verify_api_key_valid(self):
        """Test that valid API key is accepted"""
        from api.middleware.auth import verify_api_key

        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-API-Key": "test-api-key-12345"}

        with patch('api.middleware.auth.get_settings') as mock_settings:
            mock_settings.return_value.api_key = "test-api-key-12345"

            # Should not raise exception
            result = pytest.importorskip('asyncio').run(
                verify_api_key(mock_request)
            )
            assert result is True

    def test_verify_api_key_invalid(self):
        """Test that invalid API key is rejected"""
        from api.middleware.auth import verify_api_key

        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-API-Key": "wrong-key"}

        with patch('api.middleware.auth.get_settings') as mock_settings:
            mock_settings.return_value.api_key = "test-api-key-12345"

            with pytest.raises(HTTPException) as exc_info:
                pytest.importorskip('asyncio').run(
                    verify_api_key(mock_request)
                )

            assert exc_info.value.status_code == 403
            assert "Invalid API key" in str(exc_info.value.detail)

    def test_verify_api_key_missing(self):
        """Test that missing API key is rejected"""
        from api.middleware.auth import verify_api_key

        mock_request = Mock(spec=Request)
        mock_request.headers = {}

        with patch('api.middleware.auth.get_settings') as mock_settings:
            mock_settings.return_value.api_key = "test-api-key-12345"

            with pytest.raises(HTTPException) as exc_info:
                pytest.importorskip('asyncio').run(
                    verify_api_key(mock_request)
                )

            assert exc_info.value.status_code == 401
            assert "missing" in str(exc_info.value.detail).lower()

    def test_no_api_key_configured_dev_mode(self):
        """Test that requests pass when no API key is configured (dev mode)"""
        from api.middleware.auth import verify_api_key

        mock_request = Mock(spec=Request)
        mock_request.headers = {}

        with patch('api.middleware.auth.get_settings') as mock_settings:
            mock_settings.return_value.api_key = None

            # Should pass without API key in dev mode
            result = pytest.importorskip('asyncio').run(
                verify_api_key(mock_request)
            )
            assert result is True

    def test_constant_time_comparison_used(self):
        """Test that secrets.compare_digest is used (prevents timing attacks)"""
        from api.middleware.auth import verify_api_key

        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-API-Key": "test-key"}

        with patch('api.middleware.auth.get_settings') as mock_settings, \
             patch('api.middleware.auth.secrets.compare_digest') as mock_compare:

            mock_settings.return_value.api_key = "test-key"
            mock_compare.return_value = True

            pytest.importorskip('asyncio').run(
                verify_api_key(mock_request)
            )

            # Verify constant-time comparison was called
            mock_compare.assert_called_once_with("test-key", "test-key")


@pytest.mark.unit
class TestAPIKeyMiddleware:
    """Test suite for APIKeyMiddleware class"""

    def test_excluded_paths_bypass_auth(self):
        """Test that excluded paths bypass authentication"""
        from api.middleware.auth import APIKeyMiddleware

        excluded_paths = ["/health", "/docs", "/redoc", "/openapi.json"]

        for path in excluded_paths:
            mock_request = Mock(spec=Request)
            mock_request.url.path = path

            middleware = APIKeyMiddleware(app=None)

            # Mock call_next
            async def mock_call_next(request):
                return Mock(status_code=200)

            # Should bypass auth and call next
            result = pytest.importorskip('asyncio').run(
                middleware.dispatch(mock_request, mock_call_next)
            )
            assert result.status_code == 200

    def test_protected_paths_require_auth(self):
        """Test that non-excluded paths require authentication"""
        from api.middleware.auth import APIKeyMiddleware

        protected_paths = ["/", "/api/websocket/status", "/api/execute"]

        for path in protected_paths:
            mock_request = Mock(spec=Request)
            mock_request.url.path = path
            mock_request.headers = {}  # No API key

            middleware = APIKeyMiddleware(app=None)

            async def mock_call_next(request):
                return Mock(status_code=200)

            with patch('api.middleware.auth.get_settings') as mock_settings:
                mock_settings.return_value.api_key = "test-key"

                result = pytest.importorskip('asyncio').run(
                    middleware.dispatch(mock_request, mock_call_next)
                )

                # Should return 401
                assert result.status_code == 401


@pytest.mark.unit
@pytest.mark.security
class TestAuthSecurity:
    """Security-focused tests for authentication"""

    def test_timing_attack_resistance(self):
        """Test that timing attacks are prevented"""
        # This test verifies that secrets.compare_digest is used
        # which provides constant-time comparison

        from api.middleware.auth import verify_api_key

        correct_key = "test-api-key-12345"
        wrong_keys = [
            "aaa",  # Wrong from start
            "test",  # Partially correct
            "test-api-key-12344",  # Off by one character
        ]

        mock_request = Mock(spec=Request)

        with patch('api.middleware.auth.get_settings') as mock_settings:
            mock_settings.return_value.api_key = correct_key

            for wrong_key in wrong_keys:
                mock_request.headers = {"X-API-Key": wrong_key}

                with pytest.raises(HTTPException) as exc_info:
                    pytest.importorskip('asyncio').run(
                        verify_api_key(mock_request)
                    )

                # All should fail with same status code
                assert exc_info.value.status_code == 403

    def test_empty_api_key_rejected(self):
        """Test that empty API key is rejected"""
        from api.middleware.auth import verify_api_key

        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-API-Key": ""}

        with patch('api.middleware.auth.get_settings') as mock_settings:
            mock_settings.return_value.api_key = "test-key"

            with pytest.raises(HTTPException) as exc_info:
                pytest.importorskip('asyncio').run(
                    verify_api_key(mock_request)
                )

            assert exc_info.value.status_code in [401, 403]

    def test_case_sensitive_api_key(self):
        """Test that API key comparison is case-sensitive"""
        from api.middleware.auth import verify_api_key

        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-API-Key": "TEST-API-KEY"}

        with patch('api.middleware.auth.get_settings') as mock_settings:
            mock_settings.return_value.api_key = "test-api-key"

            with pytest.raises(HTTPException):
                pytest.importorskip('asyncio').run(
                    verify_api_key(mock_request)
                )
