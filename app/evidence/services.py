"""Evidence service layer for business logic and data operations."""

import json
import logging
import os
import re
from typing import List, Optional
from pathlib import Path
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
    ) -> Evidence:
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
                status=data.status,
                job_template_id=data.job_template_id,
                aws_account_id=data.aws_account_id,
            )

            # Create scan job execution for automated collection
            if data.evidence_type == "automated_collection":
                self.sqs_service.send_evidence_processing_message(
                    control_id=control_id,
                    evidence_id=evidence.evidence_id,
                )

            return evidence
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
    ) -> Evidence:
        """Update existing evidence."""
        evidence = self.get_entity_or_404(evidence_id, user_id)

        try:
            # Update only provided fields
            if data.title is not None:
                evidence.title = data.title

            if data.description is not None:
                evidence.description = data.description

            if data.evidence_type is not None:
                evidence.evidence_type = data.evidence_type

            if data.status is not None:
                evidence.update_status(data.status)

            if data.aws_account_id is not None:
                evidence.aws_account_id = data.aws_account_id

            if data.job_template_id is not None:
                if data.evidence_type == "automated_collection":
                    self._validate_scan_template_access(data.job_template_id, user_id)
                evidence.job_template_id = data.job_template_id

            evidence.save()

            if data.evidence_type == "automated_collection":
                self.sqs_service.send_evidence_processing_message(
                    control_id=evidence.control_id,
                    evidence_id=evidence.evidence_id,
                )

            return evidence
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to update evidence: {str(e)}"
            )

    def delete_evidence(self, evidence_id: str, user_id: str) -> None:
        """Delete evidence."""
        evidence = self.get_entity_or_404(evidence_id, user_id)

        try:
            # Delete files from S3 if they exist
            if evidence.file_keys:
                s3_service = S3Service()
                for file_key in evidence.get_file_keys():
                    try:
                        s3_service.delete_file(file_key)
                    except Exception as e:
                        logger.error(f"Failed to delete file {file_key}: {str(e)}")

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
            status=evidence.status,
            aws_account_id=evidence.aws_account_id if evidence.aws_account_id else "",
            has_file=evidence.has_file(),
            file_keys=evidence.get_file_keys(),
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


class S3Service:
    """Service for uploading and downloading evidence files from S3."""

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".md", ".pdf"}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes

    def __init__(self) -> None:
        """Initialize S3 service."""
        self.region = os.getenv("AWS_REGION", "ca-central-1")
        self.bucket_name = os.getenv("S3_EVIDENCE_BUCKET_NAME")
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL")

        if not self.bucket_name:
            raise ValueError("S3_EVIDENCE_BUCKET_NAME environment variable not set")

        # Create S3 client
        session = boto3.Session()
        if self.endpoint_url:
            self.s3_client = session.client(
                "s3", region_name=self.region, endpoint_url=self.endpoint_url
            )
        else:
            self.s3_client = session.client("s3", region_name=self.region)

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to only include alphanumeric characters, underscores, hyphens and dots.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename with spaces replaced by underscores
        """
        # Get file extension
        file_path = Path(filename)
        name = file_path.stem
        ext = file_path.suffix.lower()

        # Replace spaces with underscores and remove non-alphanumeric characters (except - and _)
        sanitized_name = re.sub(r"[^\w\-]", "_", name)
        # Remove multiple consecutive underscores
        sanitized_name = re.sub(r"_+", "_", sanitized_name)
        # Remove leading/trailing underscores
        sanitized_name = sanitized_name.strip("_")

        return f"{sanitized_name}{ext}"

    def validate_file(self, filename: str, file_size: int) -> None:
        """
        Validate file extension and size.

        Args:
            filename: Name of the file
            file_size: Size of the file in bytes

        Raises:
            HTTPException: If file is invalid
        """
        ext = Path(filename).suffix.lower()

        if ext not in self.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type {ext} not allowed. Allowed types: {', '.join(self.ALLOWED_EXTENSIONS)}",
            )

        if file_size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size {file_size} bytes exceeds maximum allowed size of {self.MAX_FILE_SIZE} bytes (10MB)",
            )

    def upload_file(
        self,
        file_content: bytes,
        filename: str,
        assessment_id: str,
        control_id: str,
        evidence_id: str,
    ) -> str:
        """
        Upload file to S3.

        Args:
            file_content: File content as bytes
            filename: Original filename
            assessment_id: Assessment ID
            control_id: Control ID
            evidence_id: Evidence ID

        Returns:
            S3 key of uploaded file

        Raises:
            HTTPException: If upload fails
        """
        # Validate file
        self.validate_file(filename, len(file_content))

        # Sanitize filename
        sanitized_filename = self.sanitize_filename(filename)

        # Construct S3 key with path structure
        s3_key = f"{assessment_id}/{control_id}/{evidence_id}/{sanitized_filename}"

        try:
            # Determine content type
            ext = Path(filename).suffix.lower()
            content_type_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".pdf": "application/pdf",
                ".md": "text/markdown",
            }
            content_type = content_type_map.get(ext, "application/octet-stream")

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
            )

            logger.info(f"Successfully uploaded file to S3: {s3_key}")
            return s3_key

        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to upload file to S3: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to upload file: {str(e)}"
            )

    def delete_file(self, s3_key: str) -> None:
        """
        Delete file from S3.

        Args:
            s3_key: S3 key of file to delete

        Raises:
            HTTPException: If deletion fails
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Successfully deleted file from S3: {s3_key}")
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to delete file from S3: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to delete file: {str(e)}"
            )

    def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate presigned URL for file download.

        Args:
            s3_key: S3 key of file
            expiration: URL expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL

        Raises:
            HTTPException: If URL generation fails
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expiration,
            )
            return url
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to generate download URL: {str(e)}"
            )

    def get_file_content(self, s3_key: str) -> tuple[bytes, str]:
        """
        Get file content from S3.

        Args:
            s3_key: S3 key of file

        Returns:
            Tuple of (file_content, content_type)

        Raises:
            HTTPException: If file retrieval fails
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response["Body"].read()
            content_type = response.get("ContentType", "application/octet-stream")
            return content, content_type
        except self.s3_client.exceptions.NoSuchKey:
            raise HTTPException(status_code=404, detail="File not found")
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to retrieve file from S3: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve file: {str(e)}"
            )

    def get_file_metadata(self, s3_key: str) -> dict[str, any]:
        """
        Get metadata for a file in S3.

        Args:
            s3_key: S3 key of file

        Returns:
            Dictionary with file metadata including size and content_type

        Raises:
            HTTPException: If metadata retrieval fails
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            filename = s3_key.split("/")[-1]
            return {
                "key": s3_key,
                "filename": filename,
                "size": response.get("ContentLength", 0),
                "content_type": response.get("ContentType", "application/octet-stream"),
            }
        except self.s3_client.exceptions.NoSuchKey:
            raise HTTPException(status_code=404, detail="File not found")
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to get file metadata from S3: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get file metadata: {str(e)}"
            )

    def list_files(
        self, assessment_id: str, control_id: str, evidence_id: str
    ) -> list[str]:
        """
        List all files for a specific evidence.

        Args:
            assessment_id: Assessment ID
            control_id: Control ID
            evidence_id: Evidence ID

        Returns:
            List of S3 keys

        Raises:
            HTTPException: If listing fails
        """
        prefix = f"{assessment_id}/{control_id}/{evidence_id}/"

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=prefix
            )

            if "Contents" not in response:
                return []

            return [obj["Key"] for obj in response["Contents"]]
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to list files from S3: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to list files: {str(e)}"
            )
