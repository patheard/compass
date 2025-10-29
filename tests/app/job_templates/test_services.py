"""Unit tests for job template services."""

from unittest.mock import MagicMock, patch

import pytest

from app.job_templates.services import JobTemplateService
from app.job_templates.validation import JobTemplateRequest


@pytest.fixture
def mock_job_template() -> MagicMock:
    """Create a mock job template."""
    template = MagicMock()
    template.template_id = "test-template-id"
    template.name = "Test Template"
    template.description = "Test description"
    template.scan_type = "aws_config"
    template.is_active = "true"
    template.aws_resources = ["s3"]
    template.nist_control_ids = ["AC-6"]
    return template


@pytest.fixture
def job_template_request() -> JobTemplateRequest:
    """Create a valid job template request."""
    return JobTemplateRequest(
        name="Test Template",
        description="Test description",
        scan_type="aws_config",
        config='{"key": "value"}',
        aws_resources=["s3"],
        nist_control_ids=["AC-6"],
    )


class TestJobTemplateService:
    """Tests for JobTemplateService class."""

    @patch("app.job_templates.services.JobTemplate")
    def test_create_template(
        self,
        mock_template_class: MagicMock,
        mock_job_template: MagicMock,
        job_template_request: JobTemplateRequest,
    ) -> None:
        """Test creating a job template."""
        mock_template_class.create_template.return_value = mock_job_template

        result = JobTemplateService.create_template(job_template_request)

        assert result == mock_job_template
        mock_template_class.create_template.assert_called_once_with(
            name=job_template_request.name,
            description=job_template_request.description,
            scan_type=job_template_request.scan_type,
            config=job_template_request.config,
            aws_resources=job_template_request.aws_resources,
            nist_control_ids=job_template_request.nist_control_ids,
        )

    @patch("app.job_templates.services.JobTemplate")
    def test_get_template_success(
        self, mock_template_class: MagicMock, mock_job_template: MagicMock
    ) -> None:
        """Test getting a template by ID when it exists."""
        mock_template_class.get.return_value = mock_job_template

        result = JobTemplateService.get_template("test-template-id")

        assert result == mock_job_template
        mock_template_class.get.assert_called_once_with("test-template-id")

    @patch("app.job_templates.services.JobTemplate")
    def test_get_template_not_found(self, mock_template_class: MagicMock) -> None:
        """Test getting a template by ID when it doesn't exist."""

        # Create a proper exception class
        class DoesNotExist(Exception):
            pass

        mock_template_class.DoesNotExist = DoesNotExist
        mock_template_class.get.side_effect = DoesNotExist("Template not found")

        result = JobTemplateService.get_template("nonexistent-id")

        assert result is None
        mock_template_class.get.assert_called_once_with("nonexistent-id")

    @patch("app.job_templates.services.JobTemplate")
    def test_get_all_templates_active_only(
        self, mock_template_class: MagicMock, mock_job_template: MagicMock
    ) -> None:
        """Test getting all active templates."""
        mock_template_class.get_all_templates.return_value = [mock_job_template]

        result = JobTemplateService.get_all_templates(active_only=True)

        assert result == [mock_job_template]
        mock_template_class.get_all_templates.assert_called_once_with(True)

    @patch("app.job_templates.services.JobTemplate")
    def test_get_all_templates_include_inactive(
        self, mock_template_class: MagicMock, mock_job_template: MagicMock
    ) -> None:
        """Test getting all templates including inactive."""
        mock_template_class.get_all_templates.return_value = [mock_job_template]

        result = JobTemplateService.get_all_templates(active_only=False)

        assert result == [mock_job_template]
        mock_template_class.get_all_templates.assert_called_once_with(False)

    @patch("app.job_templates.services.JobTemplate")
    def test_get_templates_by_type(
        self, mock_template_class: MagicMock, mock_job_template: MagicMock
    ) -> None:
        """Test getting templates by scan type."""
        mock_template_class.get_by_type.return_value = [mock_job_template]

        result = JobTemplateService.get_templates_by_type(
            "aws_config", active_only=True
        )

        assert result == [mock_job_template]
        mock_template_class.get_by_type.assert_called_once_with("aws_config", True)

    @patch("app.job_templates.services.JobTemplate")
    def test_update_template_success(
        self,
        mock_template_class: MagicMock,
        mock_job_template: MagicMock,
        job_template_request: JobTemplateRequest,
    ) -> None:
        """Test updating a template successfully."""
        mock_template_class.get.return_value = mock_job_template

        result = JobTemplateService.update_template(
            "test-template-id", job_template_request
        )

        assert result == mock_job_template
        assert mock_job_template.name == job_template_request.name
        assert mock_job_template.description == job_template_request.description
        assert mock_job_template.scan_type == job_template_request.scan_type
        mock_job_template.update_config.assert_called_once_with(
            job_template_request.config
        )

    @patch("app.job_templates.services.JobTemplate")
    def test_update_template_not_found(
        self, mock_template_class: MagicMock, job_template_request: JobTemplateRequest
    ) -> None:
        """Test updating a template that doesn't exist."""

        class DoesNotExist(Exception):
            pass

        mock_template_class.DoesNotExist = DoesNotExist
        mock_template_class.get.side_effect = DoesNotExist

        result = JobTemplateService.update_template(
            "nonexistent-id", job_template_request
        )

        assert result is None

    @patch("app.job_templates.services.JobTemplate")
    def test_delete_template_success(
        self, mock_template_class: MagicMock, mock_job_template: MagicMock
    ) -> None:
        """Test deleting a template successfully."""
        mock_template_class.get.return_value = mock_job_template

        result = JobTemplateService.delete_template("test-template-id")

        assert result is True
        mock_job_template.deactivate.assert_called_once()

    @patch("app.job_templates.services.JobTemplate")
    def test_delete_template_not_found(self, mock_template_class: MagicMock) -> None:
        """Test deleting a template that doesn't exist."""

        # Create a proper exception class
        class DoesNotExist(Exception):
            pass

        mock_template_class.DoesNotExist = DoesNotExist
        mock_template_class.get.side_effect = DoesNotExist("Template not found")

        result = JobTemplateService.delete_template("nonexistent-id")

        assert result is False

    @patch("app.job_templates.services.JobTemplate")
    def test_activate_template_success(
        self, mock_template_class: MagicMock, mock_job_template: MagicMock
    ) -> None:
        """Test activating a template successfully."""
        mock_template_class.get.return_value = mock_job_template

        result = JobTemplateService.activate_template("test-template-id")

        assert result is True
        mock_job_template.activate.assert_called_once()

    @patch("app.job_templates.services.JobTemplate")
    def test_activate_template_not_found(self, mock_template_class: MagicMock) -> None:
        """Test activating a template that doesn't exist."""

        # Create a proper exception class
        class DoesNotExist(Exception):
            pass

        mock_template_class.DoesNotExist = DoesNotExist
        mock_template_class.get.side_effect = DoesNotExist("Template not found")

        result = JobTemplateService.activate_template("nonexistent-id")

        assert result is False

    @patch("app.job_templates.services.JobTemplate")
    def test_get_active_templates(
        self, mock_template_class: MagicMock, mock_job_template: MagicMock
    ) -> None:
        """Test getting all active templates."""
        mock_template_class.get_active_templates.return_value = [mock_job_template]

        result = JobTemplateService.get_active_templates()

        assert result == [mock_job_template]
        mock_template_class.get_active_templates.assert_called_once()
