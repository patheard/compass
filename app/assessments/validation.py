"""Validation schemas for assessment operations."""

from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, Field, validator
from app.assessments.base import BaseInputValidator
from app.constants import ASSESSMENT_STATUSES, AWS_RESOURCES


class AssessmentRequest(BaseInputValidator):
    """Validation schema for updating an assessment."""

    product_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Name of the product being assessed",
    )
    product_description: Optional[str] = Field(
        None,
        min_length=1,
        max_length=2000,
        description="Description of the product being assessed",
    )
    status: Optional[str] = Field(None, description="Assessment status")
    aws_account_id: Optional[str] = Field(
        None,
        max_length=12,
        description="AWS account ID associated with this assessment",
    )
    github_repo_controls: Optional[str] = Field(
        None,
        max_length=1000,
        description="GitHub repository for controls",
    )
    aws_resources: Optional[List[str]] = Field(
        None,
        description="List of AWS resource names associated with this assessment",
    )

    @validator("product_name")
    def validate_product_name(cls, value: Optional[str]) -> Optional[str]:
        """Validate product name format if provided."""
        if value is not None:
            if not value.strip():
                raise ValueError("Product name cannot be empty")

        return value

    @validator("product_description")
    def validate_product_description(cls, value: Optional[str]) -> Optional[str]:
        """Validate product description format if provided."""
        if value is not None:
            if not value.strip():
                raise ValueError("Product description cannot be empty")

        return value

    @validator("status")
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        """Validate status value if provided."""
        if value is not None:
            if value not in ASSESSMENT_STATUSES:
                raise ValueError(
                    f"Status must be one of: {', '.join(ASSESSMENT_STATUSES)}"
                )

        return value

    @validator("aws_account_id")
    def validate_aws_account_id(cls, value: Optional[str]) -> Optional[str]:
        """Ensure AWS account ID is exactly 12 numeric digits when provided."""
        if value is not None:
            if not value.isdigit() or len(value) != 12:
                raise ValueError("AWS account ID must be 12 digits")

        return value

    @validator("aws_resources")
    def validate_aws_resources(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        """Ensure AWS resources contains only valid entries when provided."""
        if value is not None:
            valid_resources = {resource for resource in AWS_RESOURCES}
            if not set(value).issubset(valid_resources):
                raise ValueError("AWS resources contains invalid entries.")

        return value


class AssessmentResponse(BaseModel):
    """Response schema for assessment data."""

    assessment_id: str
    owner_id: str
    product_name: str
    product_description: str
    status: str
    aws_account_id: Optional[str] = None
    github_repo_controls: Optional[str] = None
    aws_resources: Optional[List[str]] = None
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
