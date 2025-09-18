"""Validation schemas for evidence operations."""

from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, Field, validator
from app.assessments.base import BaseInputValidator


class EvidenceCreateRequest(BaseInputValidator):
    """Validation schema for creating new evidence."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Title of the evidence document",
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Description of the evidence",
    )
    evidence_type: str = Field(
        ..., description="Type of evidence (document, screenshot, policy, etc.)"
    )

    @validator("title")
    def validate_title(cls, value: str) -> str:
        """Validate evidence title format."""
        if not value.strip():
            raise ValueError("Evidence title cannot be empty")

        if len(value.strip()) < 3:
            raise ValueError("Evidence title must be at least 3 characters")

        return value

    @validator("description")
    def validate_description(cls, value: str) -> str:
        """Validate evidence description format."""
        if not value.strip():
            raise ValueError("Evidence description cannot be empty")

        if len(value.strip()) < 10:
            raise ValueError("Evidence description must be at least 10 characters")

        return value

    @validator("evidence_type")
    def validate_evidence_type(cls, value: str) -> str:
        """Validate evidence type."""
        valid_types = {
            "document",
            "screenshot",
            "policy",
            "procedure",
            "log",
            "configuration",
            "certificate",
            "report",
            "other",
        }

        if value not in valid_types:
            raise ValueError(
                f"Evidence type must be one of: {', '.join(sorted(valid_types))}"
            )

        return value


class EvidenceUpdateRequest(BaseInputValidator):
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
        max_length=2000,
        description="Description of the evidence",
    )
    evidence_type: Optional[str] = Field(None, description="Type of evidence")

    @validator("title")
    def validate_title(cls, value: Optional[str]) -> Optional[str]:
        """Validate evidence title format if provided."""
        if value is not None:
            if not value.strip():
                raise ValueError("Evidence title cannot be empty")

            if len(value.strip()) < 3:
                raise ValueError("Evidence title must be at least 3 characters")

        return value

    @validator("description")
    def validate_description(cls, value: Optional[str]) -> Optional[str]:
        """Validate evidence description format if provided."""
        if value is not None:
            if not value.strip():
                raise ValueError("Evidence description cannot be empty")

            if len(value.strip()) < 10:
                raise ValueError("Evidence description must be at least 10 characters")

        return value

    @validator("evidence_type")
    def validate_evidence_type(cls, value: Optional[str]) -> Optional[str]:
        """Validate evidence type if provided."""
        if value is not None:
            valid_types = {
                "document",
                "screenshot",
                "policy",
                "procedure",
                "log",
                "configuration",
                "certificate",
                "report",
                "other",
            }

            if value not in valid_types:
                raise ValueError(
                    f"Evidence type must be one of: {', '.join(sorted(valid_types))}"
                )

        return value


class EvidenceResponse(BaseModel):
    """Response schema for evidence data."""

    evidence_id: str
    control_id: str
    title: str
    description: str
    evidence_type: str
    file_url: Optional[str] = None
    has_file: bool = False
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
