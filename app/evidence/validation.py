"""Validation schemas for evidence operations."""

from datetime import datetime
from typing import Optional, Union, Dict, Any
from pydantic import BaseModel, Field, validator
from app.assessments.base import BaseInputValidator
from app.constants import EVIDENCE_STATUSES


class EvidenceRequest(BaseInputValidator):
    """Validation schema for updating evidence."""

    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Title of the evidence document",
    )
    description: Optional[str] = Field(
        None,
        min_length=1,
        max_length=10000,
        description="Description of the evidence",
    )
    evidence_type: Optional[str] = Field(None, description="Type of evidence")
    status: Optional[str] = Field(None, description="Status of the evidence")
    aws_account_id: Optional[str] = Field(
        None, description="AWS account ID associated with this evidence (12 digits)"
    )
    job_template_id: Optional[str] = Field(
        None, description="ID of the job template that collected this evidence"
    )

    @validator("title")
    def validate_title(cls, value: Optional[str]) -> Optional[str]:
        """Validate evidence title format if provided."""
        if value is not None:
            if not value.strip():
                raise ValueError("Evidence title cannot be empty")
        return value

    @validator("description")
    def validate_description(cls, value: Optional[str]) -> Optional[str]:
        """Validate evidence description format if provided."""
        if value is not None:
            if not value.strip():
                raise ValueError("Evidence description cannot be empty")
        return value

    @validator("evidence_type")
    def validate_evidence_type(cls, value: Optional[str]) -> Optional[str]:
        """Validate evidence type if provided."""
        if value is not None:
            valid_types = {
                "document",
                "screenshot",
                "automated_collection",
                "other",
            }

            if value not in valid_types:
                raise ValueError(
                    f"Evidence type must be one of: {', '.join(sorted(valid_types))}"
                )

        return value

    @validator("status")
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        """Validate status if provided."""
        if value is not None and value != "":
            if value not in EVIDENCE_STATUSES:
                raise ValueError(
                    f"Status must be one of: {', '.join(sorted(EVIDENCE_STATUSES))}"
                )
        return value if value != "" else None

    @validator("aws_account_id")
    def validate_aws_account_id(cls, value: Optional[str]) -> Optional[str]:
        """Validate AWS account ID format if provided (12 numeric digits)."""
        if value is None or value == "None":
            return None
        acct = value.strip()
        if acct == "":
            return None
        if not acct.isdigit() or len(acct) != 12:
            raise ValueError("aws_account_id must be a 12-digit numeric AWS account id")
        return acct


class EvidenceResponse(BaseModel):
    """Response schema for evidence data."""

    evidence_id: str
    control_id: str
    title: str
    description: str
    evidence_type: str
    status: Optional[str] = None
    has_file: bool = False
    file_keys: Optional[list[str]] = None
    aws_account_id: Optional[str] = None
    job_template_id: Optional[str] = None
    scan_execution_id: Optional[str] = None
    is_automated_collection: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @validator("created_at", "updated_at", pre=True)
    def format_datetime(cls, value: Union[datetime, str, None]) -> Optional[str]:
        """Convert datetime objects to ISO format strings."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class JobTemplateCreateRequest(BaseInputValidator):
    """Validation schema for creating scan job templates."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the scan job template",
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Description of the scan job template",
    )
    scan_type: str = Field(
        ...,
        description="Type of scan (aws_config, nessus, qualys, custom_script, etc.)",
    )
    config: Dict[str, Any] = Field(
        ..., description="Scan-specific configuration parameters"
    )

    @validator("name")
    def validate_name(cls, value: str) -> str:
        """Validate template name format."""
        if not value.strip():
            raise ValueError("Template name cannot be empty")
        return value

    @validator("description")
    def validate_description(cls, value: str) -> str:
        """Validate template description format."""
        if not value.strip():
            raise ValueError("Template description cannot be empty")
        return value

    @validator("scan_type")
    def validate_scan_type(cls, value: str) -> str:
        """Validate scan type."""
        valid_types = {"aws_config"}

        if value not in valid_types:
            raise ValueError(
                f"Scan type must be one of: {', '.join(sorted(valid_types))}"
            )

        return value


class JobTemplateResponse(BaseModel):
    """Response schema for scan job template data."""

    template_id: str
    name: str
    description: str
    scan_type: str
    config: Dict[str, Any]
    is_active: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @validator("created_at", "updated_at", pre=True)
    def format_datetime(cls, value: Union[datetime, str, None]) -> Optional[str]:
        """Convert datetime objects to ISO format strings."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class JobExecutionResponse(BaseModel):
    """Response schema for job execution data."""

    execution_id: str
    template_id: str
    evidence_id: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int
    executor_id: Optional[str] = None
    execution_config: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @validator("started_at", "completed_at", "created_at", "updated_at", pre=True)
    def format_datetime(cls, value: Union[datetime, str, None]) -> Optional[str]:
        """Convert datetime objects to ISO format strings."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    class Config:
        """Pydantic configuration."""

        from_attributes = True
