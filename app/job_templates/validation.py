"""Validation schemas for job template operations."""

from typing import List, Optional, Any
import ast
import html
import json

from pydantic import Field, validator

from app.assessments.base import BaseInputValidator
from app.constants import AWS_RESOURCES


class JobTemplateRequest(BaseInputValidator):
    """Validation schema for updating a job template."""

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Name of the job template",
    )
    description: Optional[str] = Field(
        None,
        min_length=1,
        max_length=2000,
        description="Description of the job template",
    )
    scan_type: Optional[str] = Field(
        None,
        description="Type of scan to be performed",
    )
    config: Optional[Any] = Field(
        None,
        description="Configuration object for the job template",
    )
    aws_resources: Optional[List[str]] = Field(
        None,
        description="List of AWS resource names associated with this job template",
    )

    @validator("name")
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        """Validate job template name format if provided."""
        if value is not None:
            if not value.strip():
                raise ValueError("Job template name cannot be empty")

        return value

    @validator("description")
    def validate_description(cls, value: Optional[str]) -> Optional[str]:
        """Validate job template description format if provided."""
        if value is not None:
            if not value.strip():
                raise ValueError("Job template description cannot be empty")

        return value

    @validator("scan_type")
    def validate_scan_type(cls, value: Optional[str]) -> Optional[str]:
        """Validate scan type value if provided."""
        if value is not None:
            valid_scan_types = {"aws_config"}
            if value not in valid_scan_types:
                raise ValueError(
                    f"Scan type must be one of: {', '.join(valid_scan_types)}"
                )

        return value

    @validator("config")
    def validate_config(cls, value: Optional[Any]) -> Optional[dict]:
        """Ensure config is a valid JSON-serializable mapping when provided."""
        if value is None:
            return None

        if isinstance(value, dict):
            try:
                json.dumps(value)
            except Exception:
                raise ValueError("Config must be valid JSON")
            return value

        if isinstance(value, str):
            raw = html.unescape(value).strip()
            if not raw:
                raise ValueError("Config cannot be an empty")

            try:
                parsed = ast.literal_eval(raw)
            except (ValueError, SyntaxError):
                raise ValueError("Config is not valid JSON")

            try:
                json.dumps(parsed)
            except Exception:
                raise ValueError("Config is not valid JSON")

            return parsed

    @validator("aws_resources")
    def validate_aws_resources(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        """Ensure AWS resources contains only valid entries when provided."""
        if value is not None:
            valid_resources = {resource for resource in AWS_RESOURCES}
            if not set(value).issubset(valid_resources):
                raise ValueError("AWS resources contains invalid entries.")

        return value
