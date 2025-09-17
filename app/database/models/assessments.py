"""SecurityAssessments table model for PynamoDB."""

import uuid
from typing import List, Optional

from pynamodb.attributes import (
    UnicodeAttribute,
)

from app.database.base import BaseModel
from app.database.config import db_config


class SecurityAssessment(BaseModel):
    """SecurityAssessment model for storing assessment metadata."""

    class Meta:
        """Meta configuration for the SecurityAssessments table."""

        table_name = db_config.security_assessments_table_name
        region = db_config.region
        if db_config.endpoint_url:
            host = db_config.endpoint_url

    # Primary key
    assessment_id = UnicodeAttribute(hash_key=True)

    # Assessment attributes
    owner_id = UnicodeAttribute()  # User ID of the assessment creator
    product_name = UnicodeAttribute()
    product_description = UnicodeAttribute()
    status = UnicodeAttribute()  # draft/in_progress/completed

    def __init__(
        self,
        assessment_id: Optional[str] = None,
        owner_id: str = "",
        product_name: str = "",
        product_description: str = "",
        status: str = "draft",
        **kwargs,
    ) -> None:
        """Initialize SecurityAssessment model."""
        if assessment_id is None:
            assessment_id = str(uuid.uuid4())

        super().__init__(
            assessment_id=assessment_id,
            owner_id=owner_id,
            product_name=product_name,
            product_description=product_description,
            status=status,
            **kwargs,
        )

    def is_owner(self, user_id: str) -> bool:
        """Check if a user is the owner of this assessment."""
        return self.owner_id == user_id

    def update_status(self, status: str) -> None:
        """Update the assessment status."""
        valid_statuses = {"draft", "in_progress", "completed"}
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid status: {status}. Must be one of {valid_statuses}"
            )
        self.status = status
        self.save()

    @classmethod
    def get_by_owner(cls, user_id: str) -> List["SecurityAssessment"]:
        """Get all assessments owned by a user."""
        # Use scan with filter since GSI is not yet implemented
        return [
            assessment for assessment in cls.scan() if assessment.owner_id == user_id
        ]

    @classmethod
    def create_assessment(
        cls,
        creator_id: str,
        product_name: str,
        product_description: str,
    ) -> "SecurityAssessment":
        """Create a new security assessment."""
        assessment = cls(
            owner_id=creator_id,
            product_name=product_name,
            product_description=product_description,
            status="draft",
        )
        assessment.save()
        return assessment
