"""Unit tests for evidence services."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.evidence.services import EvidenceService
from app.evidence.validation import EvidenceRequest


@pytest.fixture
def evidence_service() -> EvidenceService:
    """Create evidence service instance."""
    return EvidenceService()


@pytest.fixture
def mock_evidence() -> MagicMock:
    """Create a mock evidence."""
    evidence = MagicMock()
    evidence.evidence_id = "test-evidence-id"
    evidence.control_id = "test-control-id"
    evidence.title = "Test Evidence"
    evidence.description = "Test description"
    evidence.evidence_type = "document"
    evidence.status = "not_started"
    evidence.file_keys = []
    evidence.get_file_keys.return_value = []
    evidence.has_file.return_value = False
    evidence.is_automated_collection.return_value = False
    return evidence


@pytest.fixture
def mock_control() -> MagicMock:
    """Create a mock control."""
    control = MagicMock()
    control.control_id = "test-control-id"
    control.assessment_id = "test-assessment-id"
    return control


@pytest.fixture
def mock_assessment() -> MagicMock:
    """Create a mock assessment."""
    assessment = MagicMock()
    assessment.assessment_id = "test-assessment-id"
    assessment.is_owner.return_value = True
    return assessment


@pytest.fixture
def evidence_request() -> EvidenceRequest:
    """Create a valid evidence request."""
    return EvidenceRequest(
        title="Test Evidence",
        description="Test description",
        evidence_type="document",
        status="compliant",
    )


class TestEvidenceService:
    """Tests for EvidenceService class."""

    @patch("app.evidence.services.Control")
    @patch("app.evidence.services.SecurityAssessment")
    def test_validate_ownership_success(
        self,
        mock_assessment_class: MagicMock,
        mock_control_class: MagicMock,
        evidence_service: EvidenceService,
        mock_evidence: MagicMock,
        mock_control: MagicMock,
        mock_assessment: MagicMock,
    ) -> None:
        """Test validate ownership when user owns assessment."""
        mock_control_class.get.return_value = mock_control
        mock_assessment_class.get.return_value = mock_assessment

        result = evidence_service.validate_ownership(mock_evidence, "test-user-id")

        assert result is True
        mock_assessment.is_owner.assert_called_once_with("test-user-id")

    @patch("app.evidence.services.Control")
    def test_validate_ownership_control_not_found(
        self,
        mock_control_class: MagicMock,
        evidence_service: EvidenceService,
        mock_evidence: MagicMock,
    ) -> None:
        """Test validate ownership when control doesn't exist."""
        mock_control_class.get.side_effect = mock_control_class.DoesNotExist
        mock_control_class.DoesNotExist = Exception

        result = evidence_service.validate_ownership(mock_evidence, "test-user-id")

        assert result is False

    @patch("app.evidence.services.Control")
    @patch("app.evidence.services.SecurityAssessment")
    def test_validate_control_access_success(
        self,
        mock_assessment_class: MagicMock,
        mock_control_class: MagicMock,
        evidence_service: EvidenceService,
        mock_control: MagicMock,
        mock_assessment: MagicMock,
    ) -> None:
        """Test validating control access when user has access."""
        mock_control_class.get.return_value = mock_control
        mock_assessment_class.get.return_value = mock_assessment

        result = evidence_service.validate_control_access(
            "test-control-id", "test-user-id"
        )

        assert result == mock_control

    @patch("app.evidence.services.Control")
    def test_validate_control_access_control_not_found(
        self,
        mock_control_class: MagicMock,
        evidence_service: EvidenceService,
    ) -> None:
        """Test validating control access when control doesn't exist."""
        mock_control_class.get.side_effect = mock_control_class.DoesNotExist
        mock_control_class.DoesNotExist = Exception

        with pytest.raises(HTTPException) as exc_info:
            evidence_service.validate_control_access("test-control-id", "test-user-id")

        assert exc_info.value.status_code == 404
        assert "Control not found" in str(exc_info.value.detail)

    @patch("app.evidence.services.Control")
    @patch("app.evidence.services.SecurityAssessment")
    def test_validate_control_access_no_permission(
        self,
        mock_assessment_class: MagicMock,
        mock_control_class: MagicMock,
        evidence_service: EvidenceService,
        mock_control: MagicMock,
        mock_assessment: MagicMock,
    ) -> None:
        """Test validating control access when user doesn't have permission."""

        class ControlDoesNotExist(Exception):
            pass

        class AssessmentDoesNotExist(Exception):
            pass

        mock_control_class.DoesNotExist = ControlDoesNotExist
        mock_assessment_class.DoesNotExist = AssessmentDoesNotExist
        mock_control_class.get.return_value = mock_control
        mock_assessment_class.get.return_value = mock_assessment
        mock_assessment.is_owner.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            evidence_service.validate_control_access("test-control-id", "test-user-id")

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail)

    @patch("app.evidence.services.Evidence")
    @patch("app.evidence.services.EvidenceService.validate_control_access")
    def test_create_evidence_document_type(
        self,
        mock_validate: MagicMock,
        mock_evidence_class: MagicMock,
        evidence_service: EvidenceService,
        mock_evidence: MagicMock,
        evidence_request: EvidenceRequest,
    ) -> None:
        """Test creating evidence with document type."""
        mock_evidence_class.create_evidence.return_value = mock_evidence

        result = evidence_service.create_evidence(
            "test-control-id", "test-user-id", evidence_request
        )

        assert result == mock_evidence
        mock_validate.assert_called_once_with("test-control-id", "test-user-id")
        mock_evidence_class.create_evidence.assert_called_once()

    @patch("app.evidence.services.Evidence")
    @patch("app.evidence.services.EvidenceService.validate_control_access")
    @patch("app.evidence.services.EvidenceService._validate_scan_template_access")
    @patch("app.evidence.services.SQSService")
    def test_create_evidence_automated_collection(
        self,
        mock_sqs_class: MagicMock,
        mock_validate_template: MagicMock,
        mock_validate: MagicMock,
        mock_evidence_class: MagicMock,
        evidence_service: EvidenceService,
        mock_evidence: MagicMock,
    ) -> None:
        """Test creating evidence with automated collection type."""
        evidence_request = EvidenceRequest(
            title="Test Evidence",
            description="Test description",
            evidence_type="automated_collection",
            job_template_id="test-template-id",
        )
        mock_evidence_class.create_evidence.return_value = mock_evidence

        result = evidence_service.create_evidence(
            "test-control-id", "test-user-id", evidence_request
        )

        assert result == mock_evidence
        mock_validate_template.assert_called_once_with(
            "test-template-id", "test-user-id"
        )

    @patch("app.evidence.services.EvidenceService.get_entity_or_404")
    def test_update_evidence_success(
        self,
        mock_get: MagicMock,
        evidence_service: EvidenceService,
        mock_evidence: MagicMock,
        evidence_request: EvidenceRequest,
    ) -> None:
        """Test updating evidence successfully."""
        mock_get.return_value = mock_evidence

        result = evidence_service.update_evidence(
            "test-evidence-id", "test-user-id", evidence_request
        )

        assert result == mock_evidence
        assert mock_evidence.title == evidence_request.title
        assert mock_evidence.description == evidence_request.description
        mock_evidence.save.assert_called_once()

    @patch("app.evidence.services.EvidenceService.get_entity_or_404")
    @patch("app.evidence.services.JobExecutionService")
    def test_delete_evidence_success(
        self,
        mock_execution_service: MagicMock,
        mock_get: MagicMock,
        evidence_service: EvidenceService,
        mock_evidence: MagicMock,
    ) -> None:
        """Test deleting evidence successfully."""
        mock_get.return_value = mock_evidence

        evidence_service.delete_evidence("test-evidence-id", "test-user-id")

        mock_execution_service.delete_executions_by_evidence.assert_called_once_with(
            "test-evidence-id", "test-user-id"
        )
        mock_evidence.delete.assert_called_once()

    @patch("app.evidence.services.Control")
    @patch("app.evidence.services.SecurityAssessment")
    def test_get_control_and_assessment_info_success(
        self,
        mock_assessment_class: MagicMock,
        mock_control_class: MagicMock,
        evidence_service: EvidenceService,
        mock_control: MagicMock,
        mock_assessment: MagicMock,
    ) -> None:
        """Test getting control and assessment info."""
        mock_control_class.get.return_value = mock_control
        mock_assessment_class.get.return_value = mock_assessment
        mock_assessment.is_owner.return_value = True

        control, assessment = evidence_service.get_control_and_assessment_info(
            "test-control-id", "test-user-id"
        )

        assert control == mock_control
        assert assessment == mock_assessment

    @patch("app.evidence.services.JobTemplate")
    def test_validate_scan_template_access_success(
        self, mock_template_class: MagicMock, evidence_service: EvidenceService
    ) -> None:
        """Test validating scan template access when template exists and is active."""
        mock_template = MagicMock()
        mock_template.is_active = "true"
        mock_template_class.get.return_value = mock_template

        evidence_service._validate_scan_template_access(
            "test-template-id", "test-user-id"
        )

        mock_template_class.get.assert_called_once_with("test-template-id")

    def test_validate_scan_template_access_no_template_id(
        self, evidence_service: EvidenceService
    ) -> None:
        """Test validating scan template access when template ID is None."""
        with pytest.raises(HTTPException) as exc_info:
            evidence_service._validate_scan_template_access(None, "test-user-id")

        assert exc_info.value.status_code == 400
        assert "required" in str(exc_info.value.detail)

    @patch("app.evidence.services.JobTemplate")
    def test_validate_scan_template_access_not_active(
        self, mock_template_class: MagicMock, evidence_service: EvidenceService
    ) -> None:
        """Test validating scan template access when template is not active."""

        class DoesNotExist(Exception):
            pass

        mock_template_class.DoesNotExist = DoesNotExist
        mock_template = MagicMock()
        mock_template.is_active = "false"
        mock_template_class.get.return_value = mock_template

        with pytest.raises(HTTPException) as exc_info:
            evidence_service._validate_scan_template_access(
                "test-template-id", "test-user-id"
            )

        assert exc_info.value.status_code == 400
        assert "not active" in str(exc_info.value.detail)

    @patch("app.evidence.services.JobTemplate")
    def test_validate_scan_template_access_not_found(
        self, mock_template_class: MagicMock, evidence_service: EvidenceService
    ) -> None:
        """Test validating scan template access when template doesn't exist."""
        mock_template_class.get.side_effect = mock_template_class.DoesNotExist
        mock_template_class.DoesNotExist = Exception

        with pytest.raises(HTTPException) as exc_info:
            evidence_service._validate_scan_template_access(
                "test-template-id", "test-user-id"
            )

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)
