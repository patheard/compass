"""Unit tests for localization middleware."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, Response
from starlette.requests import Request

from app.localization.middleware import LocalizationMiddleware, get_request_locale


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI test application."""
    return FastAPI()


@pytest.fixture
def middleware(app: FastAPI) -> LocalizationMiddleware:
    """Create LocalizationMiddleware instance."""
    return LocalizationMiddleware(app)


@pytest.fixture
def mock_request() -> Request:
    """Create a mock request."""
    request = MagicMock(spec=Request)
    request.headers.get.return_value = None
    request.state = MagicMock()
    return request


@pytest.fixture
def mock_response() -> Response:
    """Create a mock response."""
    return Response(content="test")


class TestLocalizationMiddleware:
    """Tests for LocalizationMiddleware class."""

    def test_middleware_initialization(self, app: FastAPI) -> None:
        """Test middleware initialization."""
        middleware = LocalizationMiddleware(app)
        assert middleware.app == app

    @pytest.mark.asyncio
    async def test_locale_set_in_request_state(
        self,
        middleware: LocalizationMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that locale is set in request state."""
        call_next = AsyncMock(return_value=mock_response)

        await middleware.dispatch(mock_request, call_next)

        assert hasattr(mock_request.state, "locale")
        assert mock_request.state.locale in ["en", "fr"]

    @pytest.mark.asyncio
    async def test_default_locale_when_no_preferences(
        self,
        middleware: LocalizationMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that default locale is set when no preferences provided."""
        call_next = AsyncMock(return_value=mock_response)

        await middleware.dispatch(mock_request, call_next)

        assert mock_request.state.locale == "en"

    @pytest.mark.asyncio
    async def test_accept_language_header_used(
        self,
        middleware: LocalizationMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that Accept-Language header is used for locale detection."""
        mock_request.headers.get.return_value = "fr"
        call_next = AsyncMock(return_value=mock_response)

        await middleware.dispatch(mock_request, call_next)

        assert mock_request.state.locale == "fr"

    @pytest.mark.asyncio
    async def test_session_preference_takes_priority(
        self,
        middleware: LocalizationMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that session preference takes priority over Accept-Language."""
        mock_request.headers.get.return_value = "en"
        mock_request.session = {"preferred_language": "fr"}
        call_next = AsyncMock(return_value=mock_response)

        await middleware.dispatch(mock_request, call_next)

        assert mock_request.state.locale == "fr"

    @pytest.mark.asyncio
    async def test_handles_missing_session(
        self,
        middleware: LocalizationMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that middleware handles missing session gracefully."""
        mock_request.headers.get.return_value = "fr"
        delattr(mock_request, "session")
        call_next = AsyncMock(return_value=mock_response)

        await middleware.dispatch(mock_request, call_next)

        assert mock_request.state.locale == "fr"

    @pytest.mark.asyncio
    async def test_handles_session_attribute_error(
        self,
        middleware: LocalizationMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that middleware handles session AttributeError gracefully."""
        mock_request.headers.get.return_value = "en"
        type(mock_request).session = property(
            lambda self: (_ for _ in ()).throw(AttributeError("No session"))
        )
        call_next = AsyncMock(return_value=mock_response)

        await middleware.dispatch(mock_request, call_next)

        assert mock_request.state.locale == "en"

    @pytest.mark.asyncio
    async def test_handles_session_assertion_error(
        self,
        middleware: LocalizationMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that middleware handles session AssertionError gracefully."""
        mock_request.headers.get.return_value = "en"
        type(mock_request).session = property(
            lambda self: (_ for _ in ()).throw(AssertionError("Session not available"))
        )
        call_next = AsyncMock(return_value=mock_response)

        await middleware.dispatch(mock_request, call_next)

        assert mock_request.state.locale == "en"

    @pytest.mark.asyncio
    async def test_complex_accept_language_header(
        self,
        middleware: LocalizationMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that complex Accept-Language header is parsed correctly."""
        mock_request.headers.get.return_value = "en-US,en;q=0.9,fr;q=0.8"
        call_next = AsyncMock(return_value=mock_response)

        await middleware.dispatch(mock_request, call_next)

        assert mock_request.state.locale in ["en", "fr"]

    @pytest.mark.asyncio
    async def test_call_next_is_invoked(
        self,
        middleware: LocalizationMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that call_next is invoked during dispatch."""
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        call_next.assert_called_once_with(mock_request)
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_response_returned_unchanged(
        self,
        middleware: LocalizationMiddleware,
        mock_request: Request,
        mock_response: Response,
    ) -> None:
        """Test that response is returned unchanged."""
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert response == mock_response
        assert response.body == b"test"


class TestGetRequestLocale:
    """Tests for get_request_locale function."""

    def test_get_request_locale_returns_locale(self) -> None:
        """Test that get_request_locale returns locale from request state."""
        mock_request = MagicMock(spec=Request)
        mock_request.state.locale = "fr"

        result = get_request_locale(mock_request)

        assert result == "fr"

    def test_get_request_locale_default_when_missing(self) -> None:
        """Test that default locale is returned when state.locale is missing."""
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        delattr(mock_request.state, "locale")

        result = get_request_locale(mock_request)

        assert result == "en"

    def test_get_request_locale_returns_string(self) -> None:
        """Test that get_request_locale returns a string."""
        mock_request = MagicMock(spec=Request)
        mock_request.state.locale = "en"

        result = get_request_locale(mock_request)

        assert isinstance(result, str)

    def test_get_request_locale_english(self) -> None:
        """Test get_request_locale with English locale."""
        mock_request = MagicMock(spec=Request)
        mock_request.state.locale = "en"

        result = get_request_locale(mock_request)

        assert result == "en"

    def test_get_request_locale_french(self) -> None:
        """Test get_request_locale with French locale."""
        mock_request = MagicMock(spec=Request)
        mock_request.state.locale = "fr"

        result = get_request_locale(mock_request)

        assert result == "fr"
