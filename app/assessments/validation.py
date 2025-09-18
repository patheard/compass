"""Validation schemas for assessment operations."""

from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, Field, validator
from app.assessments.base import BaseInputValidator


class AssessmentCreateRequest(BaseInputValidator):
    """Validation schema for creating a new assessment."""

    product_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Name of the product being assessed",
    )
    product_description: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Description of the product being assessed",
    )

    @validator("product_name")
    def validate_product_name(cls, value: str) -> str:
        """Validate product name format."""
        if not value.strip():
            raise ValueError("Product name cannot be empty")

        # Check for minimum meaningful content
        if len(value.strip()) < 2:
            raise ValueError("Product name must be at least 2 characters")

        return value

    @validator("product_description")
    def validate_product_description(cls, value: str) -> str:
        """Validate product description format."""
        if not value.strip():
            raise ValueError("Product description cannot be empty")

        # Check for minimum meaningful content
        if len(value.strip()) < 10:
            raise ValueError("Product description must be at least 10 characters")

        return value


class AssessmentUpdateRequest(BaseInputValidator):
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

    @validator("product_name")
    def validate_product_name(cls, value: Optional[str]) -> Optional[str]:
        """Validate product name format if provided."""
        if value is not None:
            if not value.strip():
                raise ValueError("Product name cannot be empty")

            if len(value.strip()) < 2:
                raise ValueError("Product name must be at least 2 characters")

        return value

    @validator("product_description")
    def validate_product_description(cls, value: Optional[str]) -> Optional[str]:
        """Validate product description format if provided."""
        if value is not None:
            if not value.strip():
                raise ValueError("Product description cannot be empty")

            if len(value.strip()) < 10:
                raise ValueError("Product description must be at least 10 characters")

        return value

    @validator("status")
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        """Validate status value if provided."""
        if value is not None:
            valid_statuses = {"draft", "in_progress", "completed"}
            if value not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")

        return value


class AssessmentResponse(BaseModel):
    """Response schema for assessment data."""

    assessment_id: str
    owner_id: str
    product_name: str
    product_description: str
    status: str
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
