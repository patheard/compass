"""Controls table model for PynamoDB."""

import uuid
from typing import List, Optional

from pynamodb.attributes import UnicodeAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

from app.database.base import BaseModel
from app.database.config import db_config


class AssessmentIndex(GlobalSecondaryIndex):
    """Global secondary index for assessment lookups."""

    class Meta:
        """Meta configuration for the assessment index."""

        index_name = "assessment-index"
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5

    assessment_id = UnicodeAttribute(hash_key=True)
    nist_control_id = UnicodeAttribute(range_key=True)


class Control(BaseModel):
    """Control model for storing NIST 800-53 controls within assessments."""

    class Meta:
        """Meta configuration for the Controls table."""

        table_name = db_config.controls_table_name
        region = db_config.region
        if db_config.endpoint_url:
            host = db_config.endpoint_url

    # Primary key
    control_id = UnicodeAttribute(hash_key=True)

    # Control attributes
    assessment_id = UnicodeAttribute()
    nist_control_id = UnicodeAttribute()  # e.g., AC-1, AU-2
    control_title = UnicodeAttribute()
    control_description = UnicodeAttribute()
    implementation_status = UnicodeAttribute()  # not_started/partial/implemented

    # Global secondary index
    assessment_index = AssessmentIndex()

    def __init__(
        self,
        control_id: Optional[str] = None,
        assessment_id: str = "",
        nist_control_id: str = "",
        control_title: str = "",
        control_description: str = "",
        implementation_status: str = "not_started",
        **kwargs,
    ) -> None:
        """Initialize Control model."""
        if control_id is None:
            control_id = str(uuid.uuid4())

        super().__init__(
            control_id=control_id,
            assessment_id=assessment_id,
            nist_control_id=nist_control_id,
            control_title=control_title,
            control_description=control_description,
            implementation_status=implementation_status,
            **kwargs,
        )

    def update_implementation_status(self, status: str) -> None:
        """Update the implementation status."""
        valid_statuses = {"not_started", "partial", "implemented"}
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid status: {status}. Must be one of {valid_statuses}"
            )
        self.implementation_status = status
        self.save()

    @classmethod
    def get_by_assessment(cls, assessment_id: str) -> List["Control"]:
        """Get all controls for an assessment."""
        return list(cls.assessment_index.query(assessment_id))

    @classmethod
    def get_by_assessment_and_nist_id(
        cls, assessment_id: str, nist_control_id: str
    ) -> Optional["Control"]:
        """Get a specific control by assessment and NIST control ID."""
        try:
            return next(
                iter(
                    cls.assessment_index.query(
                        assessment_id, cls.nist_control_id == nist_control_id
                    )
                )
            )
        except StopIteration:
            return None

    @classmethod
    def create_control(
        cls,
        assessment_id: str,
        nist_control_id: str,
        control_title: str,
        control_description: str,
    ) -> "Control":
        """Create a new control."""
        control = cls(
            assessment_id=assessment_id,
            nist_control_id=nist_control_id,
            control_title=control_title,
            control_description=control_description,
            implementation_status="not_started",
        )
        control.save()
        return control

    @classmethod
    def get_controls_by_status(cls, assessment_id: str, status: str) -> List["Control"]:
        """Get controls by implementation status for an assessment."""
        all_controls = cls.get_by_assessment(assessment_id)
        return [
            control
            for control in all_controls
            if control.implementation_status == status
        ]
