"""Unit tests for job execution services."""

from unittest.mock import MagicMock, patch

import pytest

from app.job_executions.services import JobExecutionService


@pytest.fixture
def mock_job_execution() -> MagicMock:
    """Create a mock job execution."""
    execution = MagicMock()
    execution.execution_id = "test-execution-id"
    execution.template_id = "test-template-id"
    execution.evidence_id = "test-evidence-id"
    execution.status = "completed"
    execution.is_active.return_value = True
    return execution


@pytest.fixture
def mock_evidence() -> MagicMock:
    """Create a mock evidence."""
    evidence = MagicMock()
    evidence.evidence_id = "test-evidence-id"
    evidence.control_id = "test-control-id"
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
    assessment.owner_id = "test-user-id"
    return assessment


class TestJobExecutionService:
    """Tests for JobExecutionService class."""

    @patch("app.job_executions.services.JobExecution")
    def test_create_execution(
        self, mock_execution_class: MagicMock, mock_job_execution: MagicMock
    ) -> None:
        """Test creating a job execution."""
        mock_execution_class.create_execution.return_value = mock_job_execution

        result = JobExecutionService.create_execution(
            template_id="test-template-id",
            evidence_id="test-evidence-id",
            execution_config={"key": "value"},
        )

        assert result == mock_job_execution
        mock_execution_class.create_execution.assert_called_once_with(
            template_id="test-template-id",
            evidence_id="test-evidence-id",
            execution_config={"key": "value"},
        )

    @patch(
        "app.job_executions.services.JobExecutionService._user_has_access_to_execution"
    )
    @patch("app.job_executions.services.JobExecution")
    def test_get_execution_success(
        self,
        mock_execution_class: MagicMock,
        mock_access_check: MagicMock,
        mock_job_execution: MagicMock,
    ) -> None:
        """Test getting an execution by ID when user has access."""
        mock_execution_class.get.return_value = mock_job_execution
        mock_access_check.return_value = True

        result = JobExecutionService.get_execution("test-execution-id", "test-user-id")

        assert result == mock_job_execution
        mock_execution_class.get.assert_called_once_with("test-execution-id")
        mock_access_check.assert_called_once_with(mock_job_execution, "test-user-id")

    @patch(
        "app.job_executions.services.JobExecutionService._user_has_access_to_execution"
    )
    @patch("app.job_executions.services.JobExecution")
    def test_get_execution_no_access(
        self,
        mock_execution_class: MagicMock,
        mock_access_check: MagicMock,
        mock_job_execution: MagicMock,
    ) -> None:
        """Test getting an execution by ID when user doesn't have access."""
        mock_execution_class.get.return_value = mock_job_execution
        mock_access_check.return_value = False

        result = JobExecutionService.get_execution("test-execution-id", "test-user-id")

        assert result is None

    @patch("app.job_executions.services.JobExecution")
    def test_get_execution_not_found(self, mock_execution_class: MagicMock) -> None:
        """Test getting an execution by ID when it doesn't exist."""
        mock_execution_class.get.side_effect = mock_execution_class.DoesNotExist
        mock_execution_class.DoesNotExist = Exception

        result = JobExecutionService.get_execution("nonexistent-id", "test-user-id")

        assert result is None

    @patch(
        "app.job_executions.services.JobExecutionService._user_has_access_to_evidence"
    )
    @patch("app.job_executions.services.JobExecution")
    def test_get_evidence_executions_with_access(
        self,
        mock_execution_class: MagicMock,
        mock_access_check: MagicMock,
        mock_job_execution: MagicMock,
    ) -> None:
        """Test getting evidence executions when user has access."""
        mock_access_check.return_value = True
        mock_execution_class.get_by_evidence.return_value = [mock_job_execution]

        result = JobExecutionService.get_evidence_executions(
            "test-evidence-id", "test-user-id"
        )

        assert result == [mock_job_execution]
        mock_access_check.assert_called_once_with("test-evidence-id", "test-user-id")
        mock_execution_class.get_by_evidence.assert_called_once_with("test-evidence-id")

    @patch(
        "app.job_executions.services.JobExecutionService._user_has_access_to_evidence"
    )
    def test_get_evidence_executions_no_access(
        self, mock_access_check: MagicMock
    ) -> None:
        """Test getting evidence executions when user doesn't have access."""
        mock_access_check.return_value = False

        result = JobExecutionService.get_evidence_executions(
            "test-evidence-id", "test-user-id"
        )

        assert result == []

    @patch(
        "app.job_executions.services.JobExecutionService._user_has_access_to_evidence"
    )
    @patch("app.job_executions.services.JobExecution")
    def test_get_latest_execution_with_access(
        self,
        mock_execution_class: MagicMock,
        mock_access_check: MagicMock,
        mock_job_execution: MagicMock,
    ) -> None:
        """Test getting latest execution when user has access."""
        mock_access_check.return_value = True
        mock_execution_class.get_latest_execution.return_value = mock_job_execution

        result = JobExecutionService.get_latest_execution(
            "test-evidence-id", "test-user-id"
        )

        assert result == mock_job_execution
        mock_access_check.assert_called_once_with("test-evidence-id", "test-user-id")
        mock_execution_class.get_latest_execution.assert_called_once_with(
            "test-evidence-id"
        )

    @patch(
        "app.job_executions.services.JobExecutionService._user_has_access_to_evidence"
    )
    def test_get_latest_execution_no_access(self, mock_access_check: MagicMock) -> None:
        """Test getting latest execution when user doesn't have access."""
        mock_access_check.return_value = False

        result = JobExecutionService.get_latest_execution(
            "test-evidence-id", "test-user-id"
        )

        assert result is None

    @patch("app.job_executions.services.JobExecutionService.get_execution")
    def test_cancel_execution_success(
        self, mock_get: MagicMock, mock_job_execution: MagicMock
    ) -> None:
        """Test cancelling an active execution."""
        mock_get.return_value = mock_job_execution
        mock_job_execution.is_active.return_value = True

        result = JobExecutionService.cancel_execution(
            "test-execution-id", "test-user-id"
        )

        assert result is True
        mock_job_execution.cancel_execution.assert_called_once()

    @patch("app.job_executions.services.JobExecutionService.get_execution")
    def test_cancel_execution_not_found(self, mock_get: MagicMock) -> None:
        """Test cancelling an execution that doesn't exist."""
        mock_get.return_value = None

        result = JobExecutionService.cancel_execution(
            "test-execution-id", "test-user-id"
        )

        assert result is False

    @patch("app.job_executions.services.JobExecutionService.get_execution")
    def test_cancel_execution_not_active(
        self, mock_get: MagicMock, mock_job_execution: MagicMock
    ) -> None:
        """Test cancelling an execution that is not active."""
        mock_get.return_value = mock_job_execution
        mock_job_execution.is_active.return_value = False

        result = JobExecutionService.cancel_execution(
            "test-execution-id", "test-user-id"
        )

        assert result is False

    @patch("app.job_executions.services.JobExecutionService.get_execution")
    def test_retry_execution_success(
        self, mock_get: MagicMock, mock_job_execution: MagicMock
    ) -> None:
        """Test retrying a failed execution."""
        mock_get.return_value = mock_job_execution
        mock_job_execution.status = "failed"

        result = JobExecutionService.retry_execution(
            "test-execution-id", "test-user-id"
        )

        assert result is True
        mock_job_execution.increment_retry.assert_called_once()

    @patch("app.job_executions.services.JobExecutionService.get_execution")
    def test_retry_execution_not_failed(
        self, mock_get: MagicMock, mock_job_execution: MagicMock
    ) -> None:
        """Test retrying an execution that is not failed."""
        mock_get.return_value = mock_job_execution
        mock_job_execution.status = "completed"

        result = JobExecutionService.retry_execution(
            "test-execution-id", "test-user-id"
        )

        assert result is False

    @patch("app.job_executions.services.JobExecutionService.get_execution")
    def test_delete_execution_success(
        self, mock_get: MagicMock, mock_job_execution: MagicMock
    ) -> None:
        """Test deleting an execution successfully."""
        mock_get.return_value = mock_job_execution

        result = JobExecutionService.delete_execution(
            "test-execution-id", "test-user-id"
        )

        assert result is True
        mock_job_execution.delete.assert_called_once()

    @patch("app.job_executions.services.JobExecutionService.get_execution")
    def test_delete_execution_not_found(self, mock_get: MagicMock) -> None:
        """Test deleting an execution that doesn't exist."""
        mock_get.return_value = None

        result = JobExecutionService.delete_execution(
            "test-execution-id", "test-user-id"
        )

        assert result is False

    @patch("app.job_executions.services.JobExecutionService.get_execution")
    def test_delete_execution_exception(
        self, mock_get: MagicMock, mock_job_execution: MagicMock
    ) -> None:
        """Test deleting an execution when exception occurs."""
        mock_get.return_value = mock_job_execution
        mock_job_execution.delete.side_effect = Exception("Delete failed")

        result = JobExecutionService.delete_execution(
            "test-execution-id", "test-user-id"
        )

        assert result is False

    @patch("app.job_executions.services.JobExecutionService.get_evidence_executions")
    def test_delete_executions_by_evidence(
        self, mock_get_executions: MagicMock, mock_job_execution: MagicMock
    ) -> None:
        """Test deleting all executions for an evidence."""
        mock_get_executions.return_value = [mock_job_execution]

        result = JobExecutionService.delete_executions_by_evidence(
            "test-evidence-id", "test-user-id"
        )

        assert result is True
        mock_job_execution.delete.assert_called_once()

    @patch("app.job_executions.services.Evidence")
    @patch("app.job_executions.services.Control")
    @patch("app.job_executions.services.SecurityAssessment")
    def test_user_has_access_to_evidence_success(
        self,
        mock_assessment_class: MagicMock,
        mock_control_class: MagicMock,
        mock_evidence_class: MagicMock,
        mock_evidence: MagicMock,
        mock_control: MagicMock,
        mock_assessment: MagicMock,
    ) -> None:
        """Test user has access to evidence."""
        mock_evidence_class.get.return_value = mock_evidence
        mock_control_class.get.return_value = mock_control
        mock_assessment_class.get.return_value = mock_assessment

        result = JobExecutionService._user_has_access_to_evidence(
            "test-evidence-id", "test-user-id"
        )

        assert result is True

    @patch("app.job_executions.services.Evidence")
    def test_user_has_access_to_evidence_not_found(
        self, mock_evidence_class: MagicMock
    ) -> None:
        """Test user access check when evidence doesn't exist."""
        mock_evidence_class.get.side_effect = mock_evidence_class.DoesNotExist
        mock_evidence_class.DoesNotExist = Exception

        result = JobExecutionService._user_has_access_to_evidence(
            "test-evidence-id", "test-user-id"
        )

        assert result is False

    @patch(
        "app.job_executions.services.JobExecutionService._user_has_access_to_evidence"
    )
    def test_user_has_access_to_execution(
        self, mock_access_check: MagicMock, mock_job_execution: MagicMock
    ) -> None:
        """Test user has access to execution through evidence."""
        mock_access_check.return_value = True

        result = JobExecutionService._user_has_access_to_execution(
            mock_job_execution, "test-user-id"
        )

        assert result is True
        mock_access_check.assert_called_once_with(
            mock_job_execution.evidence_id, "test-user-id"
        )
