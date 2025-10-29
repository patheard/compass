"""Unit tests for authentication models."""

import pytest
from pydantic import ValidationError

from app.auth.models import GoogleUserInfo


class TestGoogleUserInfo:
    """Tests for GoogleUserInfo model."""

    def test_google_user_info_valid(self) -> None:
        """Test creating GoogleUserInfo with valid data."""
        user_info = GoogleUserInfo(
            email="test@example.com",
            name="Test User",
            picture="https://example.com/picture.jpg",
            sub="google-user-id-123",
            email_verified=True,
        )

        assert user_info.email == "test@example.com"
        assert user_info.name == "Test User"
        assert user_info.picture == "https://example.com/picture.jpg"
        assert user_info.sub == "google-user-id-123"
        assert user_info.email_verified is True

    def test_google_user_info_without_picture(self) -> None:
        """Test creating GoogleUserInfo without picture."""
        user_info = GoogleUserInfo(
            email="test@example.com",
            name="Test User",
            sub="google-user-id-123",
            email_verified=True,
        )

        assert user_info.email == "test@example.com"
        assert user_info.name == "Test User"
        assert user_info.picture is None
        assert user_info.sub == "google-user-id-123"
        assert user_info.email_verified is True

    def test_google_user_info_invalid_email(self) -> None:
        """Test that invalid email raises validation error."""
        with pytest.raises(ValidationError):
            GoogleUserInfo(
                email="not-an-email",
                name="Test User",
                sub="google-user-id-123",
                email_verified=True,
            )

    def test_google_user_info_missing_required_fields(self) -> None:
        """Test that missing required fields raises validation error."""
        with pytest.raises(ValidationError):
            GoogleUserInfo(
                email="test@example.com",
                name="Test User",
            )

    def test_google_user_info_email_verified_false(self) -> None:
        """Test GoogleUserInfo with unverified email."""
        user_info = GoogleUserInfo(
            email="test@example.com",
            name="Test User",
            sub="google-user-id-123",
            email_verified=False,
        )

        assert user_info.email_verified is False

    def test_google_user_info_all_fields(self) -> None:
        """Test GoogleUserInfo with all fields populated."""
        user_info = GoogleUserInfo(
            email="test@example.com",
            name="Test User",
            picture="https://example.com/pic.jpg",
            sub="google-123",
            email_verified=True,
        )

        assert user_info.email == "test@example.com"
        assert user_info.name == "Test User"
        assert user_info.picture == "https://example.com/pic.jpg"
        assert user_info.sub == "google-123"
        assert user_info.email_verified is True
