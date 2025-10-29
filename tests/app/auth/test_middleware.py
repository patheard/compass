"""Unit tests for authentication middleware and dependencies."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request

from app.auth.middleware import (
    check_session_security,
    get_user_from_session,
    require_authenticated_user,
)
from app.database.models.users import User


@pytest.fixture
def mock_user() -> User:
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.user_id = "test-user-id"
    user.google_id = "test-google-id"
    user.email = "test@example.com"
    user.name = "Test User"
    return user


@pytest.fixture
def mock_request() -> Request:
    """Create a mock request."""
    request = MagicMock(spec=Request)
    request.session = {}
    request.headers = {"User-Agent": "test-user-agent"}
    return request


class TestGetUserFromSession:
    """Tests for get_user_from_session function."""

    @pytest.mark.asyncio
    async def test_get_user_from_session_success(
        self, mock_request: Request, mock_user: User
    ) -> None:
        """Test getting user from session successfully."""
        mock_request.session = {"user": {"user_id": "test-user-id"}}

        with patch.object(User, "from_dict", return_value=mock_user):
            result = await get_user_from_session(mock_request)

            assert result == mock_user
            User.from_dict.assert_called_once_with({"user_id": "test-user-id"})

    @pytest.mark.asyncio
    async def test_get_user_from_session_no_user(self, mock_request: Request) -> None:
        """Test getting user when no user in session."""
        mock_request.session = {}

        result = await get_user_from_session(mock_request)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_from_session_invalid_data(
        self, mock_request: Request
    ) -> None:
        """Test getting user when session data is invalid."""
        mock_request.session = {"user": {"invalid": "data"}}

        with patch.object(User, "from_dict", side_effect=Exception("Invalid data")):
            result = await get_user_from_session(mock_request)

            assert result is None
            assert mock_request.session == {}

    @pytest.mark.asyncio
    async def test_get_user_from_session_clears_session_on_error(
        self, mock_request: Request
    ) -> None:
        """Test that session is cleared when user creation fails."""
        mock_request.session = {"user": {"data": "test"}}

        with patch.object(User, "from_dict", side_effect=ValueError("Parse error")):
            result = await get_user_from_session(mock_request)

            assert result is None
            assert mock_request.session == {}


class TestCheckSessionSecurity:
    """Tests for check_session_security function."""

    @pytest.mark.asyncio
    async def test_check_session_security_no_stored_user_agent(
        self, mock_request: Request
    ) -> None:
        """Test security check when no user agent is stored."""
        mock_request.session = {}
        mock_request.headers = {"User-Agent": "test-agent"}

        await check_session_security(mock_request)

        assert mock_request.session["user_agent"] == "test-agent"

    @pytest.mark.asyncio
    async def test_check_session_security_matching_user_agent(
        self, mock_request: Request
    ) -> None:
        """Test security check when user agent matches."""
        mock_request.session = {"user_agent": "test-agent"}
        mock_request.headers = {"User-Agent": "test-agent"}

        await check_session_security(mock_request)

        assert mock_request.session["user_agent"] == "test-agent"

    @pytest.mark.asyncio
    async def test_check_session_security_mismatched_user_agent(
        self, mock_request: Request
    ) -> None:
        """Test security check when user agent doesn't match."""
        mock_request.session = {"user_agent": "original-agent"}
        mock_request.headers = {"User-Agent": "different-agent"}

        with pytest.raises(HTTPException) as exc_info:
            await check_session_security(mock_request)

        assert exc_info.value.status_code == 401
        assert "Session security violation detected" in exc_info.value.detail
        assert mock_request.session == {}

    @pytest.mark.asyncio
    async def test_check_session_security_no_user_agent_header(
        self, mock_request: Request
    ) -> None:
        """Test security check when no user agent header is present."""
        mock_request.session = {}
        mock_request.headers = {}

        await check_session_security(mock_request)

        assert mock_request.session["user_agent"] == ""


class TestRequireAuthenticatedUser:
    """Tests for require_authenticated_user dependency."""

    @pytest.mark.asyncio
    async def test_require_authenticated_user_success(
        self, mock_request: Request, mock_user: User
    ) -> None:
        """Test require_authenticated_user when user is authenticated."""
        mock_request.session = {"user": {"user_id": "test-user-id"}}

        with patch(
            "app.auth.middleware.get_user_from_session",
            new=AsyncMock(return_value=mock_user),
        ):
            with patch(
                "app.auth.middleware.check_session_security", new=AsyncMock()
            ) as mock_check:
                result = await require_authenticated_user(mock_request)

                assert result == mock_user
                mock_check.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_require_authenticated_user_no_user(
        self, mock_request: Request
    ) -> None:
        """Test require_authenticated_user when no user in session."""
        with patch(
            "app.auth.middleware.get_user_from_session",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await require_authenticated_user(mock_request)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Authentication required"

    @pytest.mark.asyncio
    async def test_require_authenticated_user_security_violation(
        self, mock_request: Request, mock_user: User
    ) -> None:
        """Test require_authenticated_user when security check fails."""
        mock_request.session = {"user": {"user_id": "test-user-id"}}

        with patch(
            "app.auth.middleware.get_user_from_session",
            new=AsyncMock(return_value=mock_user),
        ):
            with patch(
                "app.auth.middleware.check_session_security",
                new=AsyncMock(
                    side_effect=HTTPException(
                        status_code=401, detail="Security violation"
                    )
                ),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await require_authenticated_user(mock_request)

                assert exc_info.value.status_code == 401
                assert exc_info.value.detail == "Security violation"
