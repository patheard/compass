"""Service layer for job execution operations."""

from typing import Dict, List, Optional, Any

from app.database.models.job_executions import JobExecution
from app.database.models.evidence import Evidence
from app.database.models.controls import Control
from app.database.models.assessments import SecurityAssessment


class JobExecutionService:
    """Service for managing job executions."""

    @staticmethod
    def create_execution(
        template_id: str,
        evidence_id: str,
        execution_config: Optional[Dict[str, Any]] = None,
    ) -> JobExecution:
        """Create a new job execution."""
        return JobExecution.create_execution(
            template_id=template_id,
            evidence_id=evidence_id,
            execution_config=execution_config,
        )

    @staticmethod
    def get_execution(execution_id: str, user_id: str) -> Optional[JobExecution]:
        """Get an execution by ID if user has access."""
        try:
            execution = JobExecution.get(execution_id)
            # Check if user has access to this execution through evidence ownership
            if JobExecutionService._user_has_access_to_execution(execution, user_id):
                return execution
            return None
        except JobExecution.DoesNotExist:
            return None

    @staticmethod
    def get_evidence_executions(evidence_id: str, user_id: str) -> List[JobExecution]:
        """Get all executions for evidence if user has access."""
        # Verify user has access to the evidence
        if not JobExecutionService._user_has_access_to_evidence(evidence_id, user_id):
            return []

        return JobExecution.get_by_evidence(evidence_id)

    @staticmethod
    def get_latest_execution(evidence_id: str, user_id: str) -> Optional[JobExecution]:
        """Get latest execution for evidence if user has access."""
        # Verify user has access to the evidence
        if not JobExecutionService._user_has_access_to_evidence(evidence_id, user_id):
            return None

        return JobExecution.get_latest_execution(evidence_id)

    @staticmethod
    def cancel_execution(execution_id: str, user_id: str) -> bool:
        """Cancel an execution if user has access."""
        execution = JobExecutionService.get_execution(execution_id, user_id)
        if not execution or not execution.is_active():
            return False

        execution.cancel_execution()
        return True

    @staticmethod
    def retry_execution(execution_id: str, user_id: str) -> bool:
        """Retry a failed execution if user has access."""
        execution = JobExecutionService.get_execution(execution_id, user_id)
        if not execution or execution.status != "failed":
            return False

        execution.increment_retry()
        return True

    @staticmethod
    def delete_execution(execution_id: str, user_id: str) -> bool:
        """Delete a job execution."""
        execution = JobExecutionService.get_execution(execution_id, user_id)
        if not execution:
            return False

        try:
            execution.delete()
            return True
        except JobExecution.DoesNotExist:  # Race condition after fetch
            return False
        except Exception:
            # Intentionally swallow to keep interface simple (bool result)
            return False

    @staticmethod
    def delete_executions_by_evidence(evidence_id: str, user_id: str) -> bool:
        """Delete all job executions for a specific evidence."""
        executions = JobExecutionService.get_evidence_executions(evidence_id, user_id)
        for execution in executions:
            execution.delete()
        return True

    @staticmethod
    def get_user_pending_executions(user_id: str) -> List[JobExecution]:
        """Get all pending executions for user's evidence."""
        # This would require a more complex query in production
        # For now, we'll get all pending and filter by user access
        pending_executions = JobExecution.get_pending_executions()
        return [
            execution
            for execution in pending_executions
            if JobExecutionService._user_has_access_to_execution(execution, user_id)
        ]

    @staticmethod
    def get_user_running_executions(user_id: str) -> List[JobExecution]:
        """Get all running executions for user's evidence."""
        # This would require a more complex query in production
        # For now, we'll get all running and filter by user access
        running_executions = JobExecution.get_running_executions()
        return [
            execution
            for execution in running_executions
            if JobExecutionService._user_has_access_to_execution(execution, user_id)
        ]

    @staticmethod
    def _user_has_access_to_evidence(evidence_id: str, user_id: str) -> bool:
        """Check if user has access to evidence through assessment ownership."""
        try:
            evidence = Evidence.get(evidence_id)
            control = Control.get(evidence.control_id)
            assessment = SecurityAssessment.get(control.assessment_id)
            return assessment.owner_id == user_id
        except (
            Evidence.DoesNotExist,
            Control.DoesNotExist,
            SecurityAssessment.DoesNotExist,
        ):
            return False

    @staticmethod
    def _user_has_access_to_execution(execution: JobExecution, user_id: str) -> bool:
        """Check if user has access to execution through evidence ownership."""
        return JobExecutionService._user_has_access_to_evidence(
            execution.evidence_id, user_id
        )
