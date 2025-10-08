"""SecurityAssessments table model for PynamoDB."""

import uuid
from typing import List, Optional

from pynamodb.attributes import (
    ListAttribute,
    UnicodeAttribute,
)

from app.database.base import BaseModel
from app.database.config import db_config
from app.constants import ASSESSMENT_STATUSES


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
    aws_account_id = UnicodeAttribute(null=True)  # Optional AWS account ID
    github_repo_controls = UnicodeAttribute(null=True)  # Optional GitHub repo controls
    aws_resources = ListAttribute(null=True)  # Optional list of AWS resource names

    def __init__(
        self,
        assessment_id: Optional[str] = None,
        owner_id: str = "",
        product_name: str = "",
        product_description: str = "",
        status: str = ASSESSMENT_STATUSES[0],
        aws_account_id: Optional[str] = None,
        github_repo_controls: Optional[str] = None,
        aws_resources: Optional[List[str]] = None,
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
            aws_account_id=aws_account_id,
            github_repo_controls=github_repo_controls,
            aws_resources=aws_resources,
            **kwargs,
        )

    def is_owner(self, user_id: str) -> bool:
        """Check if a user is the owner of this assessment."""
        return self.owner_id == user_id

    def update_status(self, status: str) -> None:
        """Update the assessment status."""
        if status not in ASSESSMENT_STATUSES:
            raise ValueError(
                f"Invalid status: {status}. Must be one of {ASSESSMENT_STATUSES}"
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
        aws_account_id: Optional[str] = None,
        github_repo_controls: Optional[str] = None,
        aws_resources: Optional[List[str]] = None,
    ) -> "SecurityAssessment":
        """Create a new security assessment."""
        assessment = cls(
            owner_id=creator_id,
            product_name=product_name,
            product_description=product_description,
            status="draft",
            aws_account_id=aws_account_id,
            github_repo_controls=github_repo_controls,
            aws_resources=aws_resources,
        )
        assessment.save()
        return assessment
