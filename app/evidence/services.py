"""Evidence service layer for business logic and data operations."""

import json
import logging
import os
from typing import List, Optional
from fastapi import HTTPException

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.database.models.evidence import Evidence
from app.database.models.controls import Control
from app.database.models.assessments import SecurityAssessment
from app.database.models.job_templates import JobTemplate
from app.job_executions.services import JobExecutionService
from app.assessments.base import BaseService
from app.evidence.validation import (
    EvidenceRequest,
    EvidenceResponse,
)

logger = logging.getLogger(__name__)


class EvidenceService(BaseService[Evidence]):
    """Service class for evidence CRUD operations."""

    def __init__(self):
        super().__init__(Evidence)
        self.sqs_service = SQSService()

    def validate_ownership(self, entity: Evidence, user_id: str) -> bool:
        """Validate that the user owns the assessment containing the evidence."""
        try:
            # Get control that this evidence belongs to
            control = Control.get(entity.control_id)
            # Get assessment that the control belongs to
            assessment = SecurityAssessment.get(control.assessment_id)
            return assessment.is_owner(user_id)
        except (Control.DoesNotExist, SecurityAssessment.DoesNotExist):
            return False

    def get_user_entities(self, user_id: str) -> List[Evidence]:
        """Get all evidence belonging to user's assessments."""
        try:
            # Get all user's assessments
            user_assessments = SecurityAssessment.get_by_owner(user_id)
            all_evidence = []

            for assessment in user_assessments:
                # Get all controls for this assessment
                controls = Control.get_by_assessment(assessment.assessment_id)
                for control in controls:
                    # Get evidence for each control
                    evidence_list = Evidence.get_by_control(control.control_id)
                    all_evidence.extend(evidence_list)

            return all_evidence
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve evidence: {str(e)}"
            )

    def validate_control_access(self, control_id: str, user_id: str) -> Control:
        """Validate that user has access to the control and return it."""
        try:
            control = Control.get(control_id)
            assessment = SecurityAssessment.get(control.assessment_id)
            if not assessment.is_owner(user_id):
                raise HTTPException(status_code=403, detail="Access denied to control")
            return control
        except Control.DoesNotExist:
            raise HTTPException(status_code=404, detail="Control not found")
        except SecurityAssessment.DoesNotExist:
            raise HTTPException(status_code=404, detail="Assessment not found")

    def create_evidence(
        self, control_id: str, user_id: str, data: EvidenceRequest
    ) -> EvidenceResponse:
        """Create new evidence."""
        # Validate control access
        self.validate_control_access(control_id, user_id)

        # If automated collection, validate template access
        if data.evidence_type == "automated_collection":
            self._validate_scan_template_access(data.job_template_id, user_id)

        try:
            evidence = Evidence.create_evidence(
                control_id=control_id,
                title=data.title,
                description=data.description,
                evidence_type=data.evidence_type,
                job_template_id=data.job_template_id,
                aws_account_id=data.aws_account_id,
            )

            # Create scan job execution for automated collection
            if data.evidence_type == "automated_collection":
                # Send SQS message for processing
                self.sqs_service.send_evidence_processing_message(
                    control_id=control_id,
                    evidence_id=evidence.evidence_id,
                )

            return self._to_response(evidence)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to create evidence: {str(e)}"
            )

    def get_evidence(self, evidence_id: str, user_id: str) -> EvidenceResponse:
        """Get a specific evidence by ID."""
        evidence = self.get_entity_or_404(evidence_id, user_id)
        return self._to_response(evidence)

    def list_evidence_by_control(
        self, control_id: str, user_id: str
    ) -> List[EvidenceResponse]:
        """List all evidence for a specific control."""
        # Validate control access
        self.validate_control_access(control_id, user_id)

        try:
            evidence_list = Evidence.get_by_control(control_id)
            return [self._to_response(evidence) for evidence in evidence_list]
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve evidence: {str(e)}"
            )

    def update_evidence(
        self, evidence_id: str, user_id: str, data: EvidenceRequest
    ) -> EvidenceResponse:
        """Update existing evidence."""
        evidence = self.get_entity_or_404(evidence_id, user_id)

        # Track if evidence type is changing to automated_collection
        becoming_automated = (
            data.evidence_type == "automated_collection"
            and evidence.evidence_type != "automated_collection"
        )

        try:
            # Update only provided fields
            if data.title is not None:
                evidence.title = data.title

            if data.description is not None:
                evidence.description = data.description

            if data.evidence_type is not None:
                evidence.evidence_type = data.evidence_type

            if data.aws_account_id is not None:
                evidence.aws_account_id = data.aws_account_id

            evidence.save()

            # Send SQS message if evidence type changed to automated_collection
            if becoming_automated:
                self.sqs_service.send_evidence_processing_message(
                    control_id=evidence.control_id,
                    evidence_id=evidence.evidence_id,
                )

            return self._to_response(evidence)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to update evidence: {str(e)}"
            )

    def delete_evidence(self, evidence_id: str, user_id: str) -> None:
        """Delete evidence."""
        evidence = self.get_entity_or_404(evidence_id, user_id)

        try:
            # TODO: If evidence has a file, delete it from S3 storage
            JobExecutionService.delete_executions_by_evidence(evidence_id, user_id)
            evidence.delete()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete evidence: {str(e)}"
            )

    def get_control_and_assessment_info(self, control_id: str, user_id: str) -> tuple:
        """Get control and assessment information for context."""
        control = self.validate_control_access(control_id, user_id)
        try:
            assessment = SecurityAssessment.get(control.assessment_id)
            return control, assessment
        except SecurityAssessment.DoesNotExist:
            raise HTTPException(status_code=404, detail="Assessment not found")

    def _validate_scan_template_access(
        self, template_id: Optional[str], user_id: str
    ) -> None:
        """Validate that the scan job template exists and is active."""
        if not template_id:
            raise HTTPException(
                status_code=400,
                detail="Scan job template ID is required for automated collection",
            )

        try:
            template = JobTemplate.get(template_id)
            if template.is_active != "true":
                raise HTTPException(
                    status_code=400, detail="Scan job template is not active"
                )
        except JobTemplate.DoesNotExist:
            raise HTTPException(status_code=404, detail="Scan job template not found")

    def _to_response(self, evidence: Evidence) -> EvidenceResponse:
        """Convert evidence model to response schema."""
        return EvidenceResponse(
            evidence_id=evidence.evidence_id,
            control_id=evidence.control_id,
            title=evidence.title,
            description=evidence.description,
            evidence_type=evidence.evidence_type,
            aws_account_id=evidence.aws_account_id if evidence.aws_account_id else "",
            file_url=evidence.file_url,
            has_file=evidence.has_file(),
            job_template_id=evidence.job_template_id
            if evidence.job_template_id
            else "",
            scan_execution_id=evidence.scan_execution_id,
            is_automated_collection=evidence.is_automated_collection(),
            created_at=evidence.created_at,
            updated_at=evidence.updated_at,
        )


class SQSService:
    """Service for sending SQS messages for evidence processing."""

    def __init__(self) -> None:
        """Initialize SQS service."""
        self.region = os.getenv("AWS_REGION", "ca-central-1")
        self.queue_url = os.getenv("SQS_QUEUE_URL")
        self.endpoint_url = os.getenv("SQS_ENDPOINT_URL")

        # Create SQS client
        session = boto3.Session()
        if self.endpoint_url:
            self.sqs_client = session.client(
                "sqs",
                region_name=self.region,
                endpoint_url=self.endpoint_url,
            )
        else:
            self.sqs_client = session.client("sqs", region_name=self.region)

    def send_evidence_processing_message(
        self, control_id: str, evidence_id: str
    ) -> Optional[str]:
        """
        Send a message to SQS for evidence processing.

        Args:
            control_id: The control ID
            evidence_id: The evidence ID

        Returns:
            Message ID if successful, None if failed
        """
        if not self.queue_url:
            logger.warning("SQS queue URL not configured, skipping message send")
            return None

        message_body = {
            "control_id": control_id,
            "evidence_id": evidence_id,
        }

        try:
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body),
            )

            message_id = response.get("MessageId")
            logger.info(
                f"Sent evidence processing message for evidence {evidence_id} "
                f"with message ID {message_id}"
            )
            return message_id

        except (BotoCoreError, ClientError) as e:
            logger.error(
                f"Failed to send evidence processing message for evidence {evidence_id}: {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error sending evidence processing message for evidence {evidence_id}: {e}"
            )
            return None
