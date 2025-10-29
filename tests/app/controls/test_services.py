"""Unit tests for control services."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.controls.services import ControlService
from app.controls.validation import ControlRequest


@pytest.fixture
def control_service() -> ControlService:
    """Create control service instance."""
    return ControlService()


@pytest.fixture
def mock_control() -> MagicMock:
    """Create a mock control."""
    control = MagicMock()
    control.control_id = "test-control-id"
    control.assessment_id = "test-assessment-id"
    control.nist_control_id = "AC-1"
    control.control_title = "Test Control"
    control.control_description = "Test description"
    control.status = "not_started"
    return control


@pytest.fixture
def mock_assessment() -> MagicMock:
    """Create a mock assessment."""
    assessment = MagicMock()
    assessment.assessment_id = "test-assessment-id"
    assessment.is_owner.return_value = True
    return assessment


@pytest.fixture
def control_request() -> ControlRequest:
    """Create a valid control request."""
    return ControlRequest(
        nist_control_id="AC-1",
        control_title="Test Control",
        control_description="Test description for control",
        status="not_started",
    )


class TestControlService:
    """Tests for ControlService class."""

    @patch("app.controls.services.SecurityAssessment")
    def test_validate_ownership_success(
        self,
        mock_assessment_class: MagicMock,
        control_service: ControlService,
        mock_control: MagicMock,
        mock_assessment: MagicMock,
    ) -> None:
        """Test validate ownership when user owns assessment."""
        mock_assessment_class.get.return_value = mock_assessment

        result = control_service.validate_ownership(mock_control, "test-user-id")

        assert result is True
        mock_assessment.is_owner.assert_called_once_with("test-user-id")

    @patch("app.controls.services.SecurityAssessment")
    def test_validate_ownership_assessment_not_found(
        self,
        mock_assessment_class: MagicMock,
        control_service: ControlService,
        mock_control: MagicMock,
    ) -> None:
        """Test validate ownership when assessment doesn't exist."""

        # Create a proper exception class
        class DoesNotExist(Exception):
            pass

        mock_assessment_class.DoesNotExist = DoesNotExist
        mock_assessment_class.get.side_effect = DoesNotExist("Assessment not found")

        result = control_service.validate_ownership(mock_control, "test-user-id")

        assert result is False

    @patch("app.controls.services.SecurityAssessment")
    def test_validate_assessment_access_success(
        self,
        mock_assessment_class: MagicMock,
        control_service: ControlService,
        mock_assessment: MagicMock,
    ) -> None:
        """Test validating assessment access when user has access."""
        mock_assessment_class.get.return_value = mock_assessment

        control_service.validate_assessment_access("test-assessment-id", "test-user-id")

        mock_assessment.is_owner.assert_called_once_with("test-user-id")

    @patch("app.controls.services.SecurityAssessment")
    def test_validate_assessment_access_not_found(
        self,
        mock_assessment_class: MagicMock,
        control_service: ControlService,
    ) -> None:
        """Test validating assessment access when assessment doesn't exist."""

        # Create a proper exception class
        class DoesNotExist(Exception):
            pass

        mock_assessment_class.DoesNotExist = DoesNotExist
        mock_assessment_class.get.side_effect = DoesNotExist("Assessment not found")

        with pytest.raises(HTTPException) as exc_info:
            control_service.validate_assessment_access(
                "test-assessment-id", "test-user-id"
            )

        assert exc_info.value.status_code == 404
        assert "Assessment not found" in str(exc_info.value.detail)

    @patch("app.controls.services.SecurityAssessment")
    def test_validate_assessment_access_no_permission(
        self,
        mock_assessment_class: MagicMock,
        control_service: ControlService,
        mock_assessment: MagicMock,
    ) -> None:
        """Test validating assessment access when user doesn't have permission."""

        class DoesNotExist(Exception):
            pass

        mock_assessment_class.DoesNotExist = DoesNotExist
        mock_assessment_class.get.return_value = mock_assessment
        mock_assessment.is_owner.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            control_service.validate_assessment_access(
                "test-assessment-id", "test-user-id"
            )

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail)

    @patch("app.controls.services.Control")
    @patch("app.controls.services.ControlService.validate_assessment_access")
    def test_create_control_success(
        self,
        mock_validate: MagicMock,
        mock_control_class: MagicMock,
        control_service: ControlService,
        mock_control: MagicMock,
        control_request: ControlRequest,
    ) -> None:
        """Test creating a control successfully."""
        mock_control_class.get_by_assessment_and_nist_id.return_value = None
        mock_control_class.create_control.return_value = mock_control
        mock_control.created_at = "2025-01-01T00:00:00"
        mock_control.updated_at = "2025-01-01T00:00:00"

        result = control_service.create_control(
            "test-assessment-id", "test-user-id", control_request
        )

        assert result is not None
        mock_validate.assert_called_once_with("test-assessment-id", "test-user-id")
        mock_control_class.create_control.assert_called_once()

    @patch("app.controls.services.Control")
    @patch("app.controls.services.ControlService.validate_assessment_access")
    def test_create_control_duplicate(
        self,
        mock_validate: MagicMock,
        mock_control_class: MagicMock,
        control_service: ControlService,
        mock_control: MagicMock,
        control_request: ControlRequest,
    ) -> None:
        """Test creating a control with duplicate NIST control ID."""
        mock_control_class.get_by_assessment_and_nist_id.return_value = mock_control

        with pytest.raises(HTTPException) as exc_info:
            control_service.create_control(
                "test-assessment-id", "test-user-id", control_request
            )

        assert exc_info.value.status_code == 400
        assert "already exists" in str(exc_info.value.detail)

    @patch("app.controls.services.ControlService.get_entity_or_404")
    def test_update_control_success(
        self,
        mock_get: MagicMock,
        control_service: ControlService,
        mock_control: MagicMock,
        control_request: ControlRequest,
    ) -> None:
        """Test updating a control successfully."""
        mock_get.return_value = mock_control
        mock_control.created_at = "2025-01-01T00:00:00"
        mock_control.updated_at = "2025-01-01T00:00:00"

        result = control_service.update_control(
            "test-control-id", "test-user-id", control_request
        )

        assert result is not None
        assert mock_control.nist_control_id == control_request.nist_control_id
        assert mock_control.control_title == control_request.control_title

    @patch("app.controls.services.Control")
    @patch("app.controls.services.ControlService.get_entity_or_404")
    def test_update_control_duplicate_nist_id(
        self,
        mock_get: MagicMock,
        mock_control_class: MagicMock,
        control_service: ControlService,
        mock_control: MagicMock,
    ) -> None:
        """Test updating a control with duplicate NIST control ID."""
        mock_get.return_value = mock_control
        duplicate_control = MagicMock()
        duplicate_control.control_id = "different-control-id"
        duplicate_control.created_at = "2025-01-01T00:00:00"
        duplicate_control.updated_at = "2025-01-01T00:00:00"
        mock_control_class.get_by_assessment_and_nist_id.return_value = (
            duplicate_control
        )

        control_request = ControlRequest(
            nist_control_id="AC-17",
            control_title="Test Control",
            control_description="Test description for control",
        )

        with pytest.raises(HTTPException):
            control_service.update_control(
                "test-control-id", "test-user-id", control_request
            )

    @patch("app.controls.services.Evidence")
    @patch("app.controls.services.ControlService.get_entity_or_404")
    def test_delete_control_success(
        self,
        mock_get: MagicMock,
        mock_evidence_class: MagicMock,
        control_service: ControlService,
        mock_control: MagicMock,
    ) -> None:
        """Test deleting a control successfully."""
        mock_get.return_value = mock_control
        mock_evidence = MagicMock()
        mock_evidence_class.get_by_control.return_value = [mock_evidence]

        control_service.delete_control("test-control-id", "test-user-id")

        mock_evidence.delete.assert_called_once()
        mock_control.delete.assert_called_once()

    @patch("app.controls.services.Control")
    @patch("app.controls.services.ControlService.validate_assessment_access")
    def test_create_controls_from_github_success(
        self,
        mock_validate: MagicMock,
        mock_control_class: MagicMock,
        control_service: ControlService,
        mock_control: MagicMock,
    ) -> None:
        """Test creating controls from GitHub issues."""
        mock_control_class.get_by_assessment_and_nist_id.return_value = None
        mock_control_class.create_control.return_value = mock_control
        mock_control.created_at = "2025-01-01T00:00:00"
        mock_control.updated_at = "2025-01-01T00:00:00"

        controls_data = [
            {
                "nist_control_id": "AC-6",
                "control_title": "Test Control",
                "control_description": "Test description",
            }
        ]

        result = control_service.create_controls_from_github(
            "test-assessment-id", "test-user-id", controls_data
        )

        assert result["created_count"] == 1
        assert result["skipped_count"] == 0
        assert result["error_count"] == 0

    @patch("app.controls.services.Control")
    @patch("app.controls.services.ControlService.validate_assessment_access")
    def test_create_controls_from_github_with_duplicates(
        self,
        mock_validate: MagicMock,
        mock_control_class: MagicMock,
        control_service: ControlService,
        mock_control: MagicMock,
    ) -> None:
        """Test creating controls from GitHub with duplicates."""
        mock_control_class.get_by_assessment_and_nist_id.return_value = mock_control

        controls_data = [
            {
                "nist_control_id": "AC-1",
                "control_title": "Test Control",
                "control_description": "Test description",
            }
        ]

        result = control_service.create_controls_from_github(
            "test-assessment-id", "test-user-id", controls_data
        )

        assert result["created_count"] == 0
        assert result["skipped_count"] == 1
        assert result["error_count"] == 0

    @patch("app.controls.services.Control")
    @patch("app.controls.services.ControlService.validate_assessment_access")
    def test_list_controls_by_assessment(
        self,
        mock_validate: MagicMock,
        mock_control_class: MagicMock,
        control_service: ControlService,
        mock_control: MagicMock,
    ) -> None:
        """Test listing controls by assessment."""
        mock_control.created_at = "2025-01-01T00:00:00"
        mock_control.updated_at = "2025-01-01T00:00:00"
        mock_control_class.get_by_assessment.return_value = [mock_control]

        result = control_service.list_controls_by_assessment(
            "test-assessment-id", "test-user-id"
        )

        assert len(result) == 1
        mock_validate.assert_called_once_with("test-assessment-id", "test-user-id")
