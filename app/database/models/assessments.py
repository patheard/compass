"""SecurityAssessments table model for PynamoDB."""

import uuid
from typing import List, Optional, Set

from pynamodb.attributes import (
    UnicodeAttribute,
    UnicodeSetAttribute,
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
    collaborator_ids = UnicodeSetAttribute()  # Set of all user IDs with access
    product_name = UnicodeAttribute()
    product_description = UnicodeAttribute()
    status = UnicodeAttribute()  # draft/in_progress/completed

    def __init__(
        self,
        assessment_id: Optional[str] = None,
        collaborator_ids: Optional[Set[str]] = None,
        product_name: str = "",
        product_description: str = "",
        status: str = "draft",
        **kwargs,
    ) -> None:
        """Initialize SecurityAssessment model."""
        if assessment_id is None:
            assessment_id = str(uuid.uuid4())
        if collaborator_ids is None:
            collaborator_ids = set()

        super().__init__(
            assessment_id=assessment_id,
            collaborator_ids=collaborator_ids,
            product_name=product_name,
            product_description=product_description,
            status=status,
            **kwargs,
        )

    def add_collaborator(self, user_id: str) -> None:
        """Add a collaborator to the assessment."""
        if not self.collaborator_ids:
            self.collaborator_ids = set()
        self.collaborator_ids.add(user_id)
        self.save()

    def remove_collaborator(self, user_id: str) -> None:
        """Remove a collaborator from the assessment."""
        if self.collaborator_ids and user_id in self.collaborator_ids:
            self.collaborator_ids.remove(user_id)
            self.save()

    def has_access(self, user_id: str) -> bool:
        """Check if a user has access to this assessment."""
        return bool(self.collaborator_ids and user_id in self.collaborator_ids)

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
    def get_by_collaborator(cls, user_id: str) -> List["SecurityAssessment"]:
        """
        Get all assessments accessible to a user.

        Note: Currently uses scan with filter since DynamoDB GSI doesn't support
        set attributes as keys. For better performance with large datasets,
        consider implementing a separate CollaboratorAssessment table with
        individual records for each user-assessment relationship.
        """
        # Use scan with filter since GSI with set attributes is not supported
        return [
            assessment for assessment in cls.scan() if assessment.has_access(user_id)
        ]

    @classmethod
    def create_assessment(
        cls,
        creator_id: str,
        product_name: str,
        product_description: str,
        collaborator_ids: Optional[Set[str]] = None,
    ) -> "SecurityAssessment":
        """Create a new security assessment."""
        if collaborator_ids is None:
            collaborator_ids = set()

        # Always include the creator as a collaborator
        collaborator_ids.add(creator_id)

        assessment = cls(
            collaborator_ids=collaborator_ids,
            product_name=product_name,
            product_description=product_description,
            status="draft",
        )
        assessment.save()
        return assessment
