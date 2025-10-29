"""Unit tests for User model."""

from datetime import datetime, timezone
from unittest.mock import MagicMock


from app.database.models.users import User


class TestUserModel:
    """Tests for User model."""

    def test_user_has_required_attributes(self) -> None:
        """Test that User model has required attributes."""
        user = MagicMock(spec=User)
        user.user_id = "user-123"
        user.google_id = "google-123"
        user.email = "test@example.com"
        user.name = "Test User"

        assert user.user_id is not None
        assert user.google_id is not None
        assert user.email is not None
        assert user.name is not None

    def test_from_dict(self) -> None:
        """Test creating user from dictionary."""
        user_dict = {
            "user_id": "user-123",
            "google_id": "google-123",
            "email": "test@example.com",
            "name": "Test User",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        user = User.from_dict(user_dict)

        assert isinstance(user, User)
        assert user.user_id == "user-123"
        assert user.email == "test@example.com"
