"""Unit tests for assessment services."""

from unittest.mock import MagicMock, patch

import pytest

from app.assessments.services import AssessmentService
from app.assessments.validation import AssessmentRequest


@pytest.fixture
def assessment_service() -> AssessmentService:
    """Create assessment service instance."""
    return AssessmentService()


@pytest.fixture
def mock_assessment() -> MagicMock:
    """Create a mock security assessment."""
    assessment = MagicMock()
    assessment.assessment_id = "test-assessment-id"
    assessment.owner_id = "test-user-id"
    assessment.product_name = "Test Product"
    assessment.product_description = "Test description"
    assessment.status = "prepare"
    assessment.aws_account_id = "123456789012"
    assessment.github_repo_controls = "owner/repo"
    assessment.aws_resources = ["s3"]
    assessment.created_at = "2025-01-01T00:00:00"
    assessment.updated_at = "2025-01-01T00:00:00"
    assessment.is_owner.return_value = True
    return assessment


@pytest.fixture
def assessment_request() -> AssessmentRequest:
    """Create a valid assessment request."""
    return AssessmentRequest(
        product_name="Test Product",
        product_description="Test description",
        status="prepare",
        aws_account_id="123456789012",
        github_repo_controls="owner/repo",
        aws_resources=["s3"],
    )


class TestAssessmentService:
    """Tests for AssessmentService class."""

    def test_validate_ownership_success(
        self,
        assessment_service: AssessmentService,
        mock_assessment: MagicMock,
    ) -> None:
        """Test validate ownership when user owns assessment."""
        result = assessment_service.validate_ownership(mock_assessment, "test-user-id")

        assert result is True
        mock_assessment.is_owner.assert_called_once_with("test-user-id")

    def test_validate_ownership_failure(
        self,
        assessment_service: AssessmentService,
        mock_assessment: MagicMock,
    ) -> None:
        """Test validate ownership when user doesn't own assessment."""
        mock_assessment.is_owner.return_value = False

        result = assessment_service.validate_ownership(
            mock_assessment, "different-user-id"
        )

        assert result is False

    @patch("app.assessments.services.SecurityAssessment")
    def test_create_assessment_success(
        self,
        mock_assessment_class: MagicMock,
        assessment_service: AssessmentService,
        mock_assessment: MagicMock,
        assessment_request: AssessmentRequest,
    ) -> None:
        """Test creating an assessment successfully."""
        mock_assessment_class.create_assessment.return_value = mock_assessment

        result = assessment_service.create_assessment(
            "test-user-id", assessment_request
        )

        assert result is not None
        mock_assessment_class.create_assessment.assert_called_once()

    @patch("app.assessments.services.AssessmentService.get_entity_or_404")
    def test_get_assessment_success(
        self,
        mock_get: MagicMock,
        assessment_service: AssessmentService,
        mock_assessment: MagicMock,
    ) -> None:
        """Test getting an assessment by ID."""
        mock_get.return_value = mock_assessment

        result = assessment_service.get_assessment("test-assessment-id", "test-user-id")

        assert result is not None
        mock_get.assert_called_once_with("test-assessment-id", "test-user-id")

    @patch("app.assessments.services.AssessmentService.get_user_entities")
    def test_list_assessments(
        self,
        mock_get_entities: MagicMock,
        assessment_service: AssessmentService,
        mock_assessment: MagicMock,
    ) -> None:
        """Test listing all assessments for a user."""
        mock_get_entities.return_value = [mock_assessment]

        result = assessment_service.list_assessments("test-user-id")

        assert len(result) == 1
        mock_get_entities.assert_called_once_with("test-user-id")

    @patch("app.assessments.services.AssessmentService.get_entity_or_404")
    def test_update_assessment_success(
        self,
        mock_get: MagicMock,
        assessment_service: AssessmentService,
        mock_assessment: MagicMock,
        assessment_request: AssessmentRequest,
    ) -> None:
        """Test updating an assessment successfully."""
        mock_get.return_value = mock_assessment

        result = assessment_service.update_assessment(
            "test-assessment-id", "test-user-id", assessment_request
        )

        assert result is not None
        assert mock_assessment.product_name == assessment_request.product_name
        mock_assessment.save.assert_called_once()

    @patch("app.assessments.services.Control")
    @patch("app.assessments.services.Evidence")
    @patch("app.assessments.services.AssessmentService.get_entity_or_404")
    def test_delete_assessment_success(
        self,
        mock_get: MagicMock,
        mock_evidence_class: MagicMock,
        mock_control_class: MagicMock,
        assessment_service: AssessmentService,
        mock_assessment: MagicMock,
    ) -> None:
        """Test deleting an assessment successfully."""
        mock_get.return_value = mock_assessment
        mock_control = MagicMock()
        mock_evidence = MagicMock()
        mock_control_class.get_by_assessment.return_value = [mock_control]
        mock_evidence_class.get_by_control.return_value = [mock_evidence]

        assessment_service.delete_assessment("test-assessment-id", "test-user-id")

        mock_evidence.delete.assert_called_once()
        mock_control.delete.assert_called_once()
        mock_assessment.delete.assert_called_once()

    @patch("app.assessments.services.SecurityAssessment")
    def test_get_user_entities_success(
        self,
        mock_assessment_class: MagicMock,
        assessment_service: AssessmentService,
        mock_assessment: MagicMock,
    ) -> None:
        """Test getting all user entities."""
        mock_assessment_class.get_by_owner.return_value = [mock_assessment]

        result = assessment_service.get_user_entities("test-user-id")

        assert len(result) == 1
        assert result[0] == mock_assessment
        mock_assessment_class.get_by_owner.assert_called_once_with("test-user-id")


class TestGitHubService:
    """Tests for GitHubService class."""

    @patch("app.assessments.services.Github")
    def test_github_service_initialization(self, mock_github_class: MagicMock) -> None:
        """Test GitHubService initialization."""
        from app.assessments.services import GitHubService

        GitHubService("test-token")

        mock_github_class.assert_called_once_with("test-token")

    @patch("app.assessments.services.Github")
    def test_get_repository_success(self, mock_github_class: MagicMock) -> None:
        """Test getting repository from URL."""
        from app.assessments.services import GitHubService

        mock_github = MagicMock()
        mock_github_class.return_value = mock_github
        mock_repo = MagicMock()
        mock_github.get_repo.return_value = mock_repo

        service = GitHubService("test-token")
        result = service.get_repository("https://github.com/owner/repo")

        assert result == mock_repo
        mock_github.get_repo.assert_called_once_with("owner/repo")

    @patch("app.assessments.services.Github")
    def test_get_repository_invalid_url(self, mock_github_class: MagicMock) -> None:
        """Test getting repository with invalid URL."""
        from app.assessments.services import GitHubService

        service = GitHubService("test-token")

        with pytest.raises(ValueError, match="Invalid GitHub repository URL format"):
            service.get_repository("invalid-url")

    @patch("app.assessments.services.Github")
    def test_parse_issue_to_control_valid(self, mock_github_class: MagicMock) -> None:
        """Test parsing GitHub issue to control data."""
        from app.assessments.services import GitHubService

        mock_issue = MagicMock()
        mock_issue.title = "AC-1: Access Control Policy"
        mock_issue.body = "# Control Definition\nTest description\n# Control Management\nManagement info"
        mock_issue.number = 1
        mock_issue.html_url = "https://github.com/owner/repo/issues/1"

        service = GitHubService("test-token")
        result = service.parse_issue_to_control(mock_issue)

        assert result["nist_control_id"] == "AC-1"
        assert result["control_title"] == "Access Control Policy"
        assert "Test description" in result["control_description"]
        assert "Control Management" not in result["control_description"]
        assert result["github_issue_number"] == 1

    @patch("app.assessments.services.Github")
    def test_parse_issue_to_control_invalid_title(
        self, mock_github_class: MagicMock
    ) -> None:
        """Test parsing GitHub issue with invalid title format."""
        from app.assessments.services import GitHubService

        mock_issue = MagicMock()
        mock_issue.title = "Invalid Title Format"

        service = GitHubService("test-token")

        with pytest.raises(ValueError, match="Issue title format invalid"):
            service.parse_issue_to_control(mock_issue)

    @patch("app.assessments.services.Github")
    def test_parse_control_description_removes_control_management(
        self, mock_github_class: MagicMock
    ) -> None:
        """Test that Control Management section is removed from description."""
        from app.assessments.services import GitHubService

        service = GitHubService("test-token")
        body = "Test description\n# Control Management\nManagement info"

        result = service._parse_control_description("Title", body)

        assert "Test description" in result
        assert "Control Management" not in result
        assert "Management info" not in result

    @patch("app.assessments.services.Github")
    def test_parse_control_description_empty_body(
        self, mock_github_class: MagicMock
    ) -> None:
        """Test parsing control description with empty body."""
        from app.assessments.services import GitHubService

        service = GitHubService("test-token")

        result = service._parse_control_description("Title", "")

        assert result == ""
