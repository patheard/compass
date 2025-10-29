"""Unit tests for control validation."""

import pytest

from app.controls.validation import ControlRequest


class TestControlRequest:
    """Tests for ControlRequest validation."""

    def test_valid_request_with_all_fields(self) -> None:
        """Test validation with all fields provided."""
        data = ControlRequest(
            nist_control_id="AC-1",
            control_title="Test Control",
            control_description="Test description for control",
            status="not_started",
        )

        assert data.nist_control_id == "AC-1"
        assert data.control_title == "Test Control"
        assert data.control_description == "Test description for control"
        assert data.status == "not_started"

    def test_valid_request_with_minimal_fields(self) -> None:
        """Test validation with only required fields."""
        data = ControlRequest(
            nist_control_id="AC-1",
            control_title="Test Control",
            control_description="Test description for control",
        )

        assert data.nist_control_id == "AC-1"
        assert data.control_title == "Test Control"
        assert data.control_description == "Test description for control"
        assert data.status is None

    def test_validate_nist_control_id_lowercase_converted(self) -> None:
        """Test that lowercase NIST control ID is converted to uppercase."""
        data = ControlRequest(
            nist_control_id="ac-1",
            control_title="Test Control",
            control_description="Test description for control",
        )

        assert data.nist_control_id == "AC-1"

    def test_validate_nist_control_id_empty_string(self) -> None:
        """Test that empty control ID is rejected."""
        with pytest.raises(ValueError):
            ControlRequest(
                nist_control_id="   ",
                control_title="Test Control",
                control_description="Test description for control",
            )

    def test_validate_nist_control_id_invalid_format(self) -> None:
        """Test that invalid NIST control ID format is rejected."""
        with pytest.raises(ValueError, match="Control ID must follow format"):
            ControlRequest(
                nist_control_id="INVALID",
                control_title="Test Control",
                control_description="Test description for control",
            )

    def test_validate_control_title_empty_string(self) -> None:
        """Test that empty control title is rejected."""
        with pytest.raises(ValueError):
            ControlRequest(
                nist_control_id="AC-1",
                control_title="   ",
                control_description="Test description for control",
            )

    def test_validate_control_title_too_short(self) -> None:
        """Test that control title shorter than 3 characters is rejected."""
        with pytest.raises(
            ValueError, match="Control title must be at least 3 characters"
        ):
            ControlRequest(
                nist_control_id="AC-1",
                control_title="AB",
                control_description="Test description for control",
            )

    def test_validate_control_description_empty_string(self) -> None:
        """Test that empty control description is rejected."""
        with pytest.raises(ValueError):
            ControlRequest(
                nist_control_id="AC-1",
                control_title="Test Control",
                control_description="   ",
            )

    def test_validate_control_description_too_short(self) -> None:
        """Test that control description shorter than 10 characters is rejected."""
        with pytest.raises(
            ValueError, match="Control description must be at least 10 characters"
        ):
            ControlRequest(
                nist_control_id="AC-1",
                control_title="Test Control",
                control_description="Too short",
            )

    def test_validate_status_invalid(self) -> None:
        """Test that invalid status is rejected."""
        with pytest.raises(ValueError, match="Status must be one of"):
            ControlRequest(
                nist_control_id="AC-1",
                control_title="Test Control",
                control_description="Test description for control",
                status="invalid_status",
            )

    def test_validate_status_none(self) -> None:
        """Test that None status is accepted."""
        data = ControlRequest(
            nist_control_id="AC-1",
            control_title="Test Control",
            control_description="Test description for control",
            status=None,
        )

        assert data.status is None
