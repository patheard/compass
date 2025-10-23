"""Validation schemas for control operations."""

from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, Field, validator
from app.assessments.base import BaseInputValidator
from app.constants import CONTROL_STATUSES


class ControlRequest(BaseInputValidator):
    """Validation schema for updating a control."""

    nist_control_id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=20,
        description="Control ID",
    )
    control_title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Title of the security control",
    )
    control_description: Optional[str] = Field(
        None,
        min_length=1,
        max_length=5000,
        description="Description of the security control",
    )
    status: Optional[str] = Field(None, description="Status of the control")

    @validator("nist_control_id")
    def validate_nist_control_id(cls, value: Optional[str]) -> Optional[str]:
        """Validate NIST control ID format if provided."""
        if value is not None:
            if not value.strip():
                raise ValueError("Control ID cannot be empty")

            import re

            pattern = r"^[A-Z]{2,3}-\d{1,2}([\.\(]\d{1,2}\)?)?$"
            if not re.match(pattern, value.strip().upper()):
                raise ValueError(
                    "Control ID must follow format like AC-1, AU-2, or SC-7.1"
                )

            return value.strip().upper()

        return value

    @validator("control_title")
    def validate_control_title(cls, value: Optional[str]) -> Optional[str]:
        """Validate control title format if provided."""
        if value is not None:
            if not value.strip():
                raise ValueError("Control title cannot be empty")

            if len(value.strip()) < 3:
                raise ValueError("Control title must be at least 3 characters")

        return value

    @validator("control_description")
    def validate_control_description(cls, value: Optional[str]) -> Optional[str]:
        """Validate control description format if provided."""
        if value is not None:
            if not value.strip():
                raise ValueError("Control description cannot be empty")

            if len(value.strip()) < 10:
                raise ValueError("Control description must be at least 10 characters")

        return value

    @validator("status")
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        """Validate status value if provided."""
        if value is not None:
            if value not in CONTROL_STATUSES:
                raise ValueError(
                    f"Status must be one of: {', '.join(CONTROL_STATUSES)}"
                )

        return value


class ControlResponse(BaseModel):
    """Response schema for control data."""

    control_id: str
    assessment_id: str
    nist_control_id: str
    control_title: str
    control_description: str
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
