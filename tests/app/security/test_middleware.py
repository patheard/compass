"""Unit tests for security headers middleware."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Response
from starlette.requests import Request

from app.security.middleware import SecurityHeadersMiddleware


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI test application."""
    return FastAPI()


@pytest.fixture
def middleware(app: FastAPI) -> SecurityHeadersMiddleware:
    """Create SecurityHeadersMiddleware instance."""
    return SecurityHeadersMiddleware(app)


@pytest.fixture
def middleware_no_https(app: FastAPI) -> SecurityHeadersMiddleware:
    """Create SecurityHeadersMiddleware with HTTPS enforcement disabled."""
    return SecurityHeadersMiddleware(app, enforce_https=False)


@pytest.fixture
def mock_request() -> Request:
    """Create a mock request."""
    request = MagicMock(spec=Request)
    request.url.path = "/test"
    return request


@pytest.fixture
def mock_response() -> Response:
    """Create a mock response."""
    return Response(content="test")


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware class."""

    def test_middleware_initialization(self, app: FastAPI) -> None:
        """Test middleware initialization with default values."""
        middleware = SecurityHeadersMiddleware(app)

        assert middleware.enforce_https is True
        assert middleware.max_age == 31536000
        assert middleware.include_subdomains is True

    def test_middleware_initialization_custom_values(self, app: FastAPI) -> None:
        """Test middleware initialization with custom values."""
        middleware = SecurityHeadersMiddleware(
            app,
            enforce_https=False,
            max_age=86400,
            include_subdomains=False,
        )

        assert middleware.enforce_https is False
        assert middleware.max_age == 86400
        assert middleware.include_subdomains is False

    @pytest.mark.asyncio
    async def test_hsts_header_added(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that HSTS header is added when enforce_https is True."""
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert "Strict-Transport-Security" in response.headers
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
        assert "includeSubDomains" in response.headers["Strict-Transport-Security"]

    @pytest.mark.asyncio
    async def test_hsts_header_not_added_when_disabled(
        self,
        middleware_no_https: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that HSTS header is not added when enforce_https is False."""
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware_no_https.dispatch(mock_request, call_next)

        assert "Strict-Transport-Security" not in response.headers

    @pytest.mark.asyncio
    async def test_csp_header_added(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that Content Security Policy header is added."""
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "object-src 'none'" in csp
        assert "base-uri 'self'" in csp
        assert "form-action 'self'" in csp

    @pytest.mark.asyncio
    async def test_x_frame_options_header(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that X-Frame-Options header is set to DENY."""
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert response.headers["X-Frame-Options"] == "DENY"

    @pytest.mark.asyncio
    async def test_x_content_type_options_header(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that X-Content-Type-Options header is set."""
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert response.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_x_xss_protection_header(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that X-XSS-Protection header is set."""
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    @pytest.mark.asyncio
    async def test_referrer_policy_header(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that Referrer-Policy header is set."""
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    @pytest.mark.asyncio
    async def test_permissions_policy_header(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that Permissions-Policy header is set."""
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert "Permissions-Policy" in response.headers
        policy = response.headers["Permissions-Policy"]
        assert "accelerometer=()" in policy
        assert "camera=()" in policy
        assert "microphone=()" in policy

    @pytest.mark.asyncio
    async def test_cache_control_for_auth_paths(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_response: Response,
    ) -> None:
        """Test that Cache-Control headers are set for auth paths."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/auth/login"
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert (
            response.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
        )
        assert response.headers["Pragma"] == "no-cache"
        assert response.headers["Expires"] == "0"

    @pytest.mark.asyncio
    async def test_cache_control_for_root_path(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_response: Response,
    ) -> None:
        """Test that Cache-Control headers are set for root path."""
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/"
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert (
            response.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
        )
        assert response.headers["Pragma"] == "no-cache"
        assert response.headers["Expires"] == "0"

    @pytest.mark.asyncio
    async def test_no_cache_control_for_other_paths(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that Cache-Control headers are not set for non-sensitive paths."""
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert "Cache-Control" not in response.headers
        assert "Pragma" not in response.headers
        assert "Expires" not in response.headers

    @pytest.mark.asyncio
    async def test_all_security_headers_present(
        self,
        middleware: SecurityHeadersMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that all security headers are present in response."""
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        expected_headers = [
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Permissions-Policy",
        ]

        for header in expected_headers:
            assert header in response.headers
