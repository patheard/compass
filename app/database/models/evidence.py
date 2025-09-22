"""Evidence table model for PynamoDB."""

import uuid
from typing import List, Optional

from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

from app.database.base import BaseModel
from app.database.config import db_config

from app.database.models.scan_job_templates import ScanJobTemplate
from app.database.models.scan_job_executions import ScanJobExecution


class ControlIndex(GlobalSecondaryIndex):
    """Global secondary index for control lookups."""

    class Meta:
        """Meta configuration for the control index."""

        index_name = "control-index"
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5

    control_id = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class Evidence(BaseModel):
    """Evidence model for storing evidence documents for controls."""

    class Meta:
        """Meta configuration for the Evidence table."""

        table_name = db_config.evidence_table_name
        region = db_config.region
        if db_config.endpoint_url:
            host = db_config.endpoint_url

    # Primary key
    evidence_id = UnicodeAttribute(hash_key=True)

    # Evidence attributes
    control_id = UnicodeAttribute()
    title = UnicodeAttribute()
    description = UnicodeAttribute()
    evidence_type = (
        UnicodeAttribute()
    )  # document/screenshot/policy/automated_collection/etc
    file_url = UnicodeAttribute(null=True)  # S3 URL if file upload
    scan_job_template_id = UnicodeAttribute(
        null=True
    )  # Reference to scan job template (for automated_collection)
    scan_execution_id = UnicodeAttribute(
        null=True
    )  # Reference to current/latest scan execution

    # Global secondary index
    control_index = ControlIndex()

    def __init__(
        self,
        evidence_id: Optional[str] = None,
        control_id: str = "",
        title: str = "",
        description: str = "",
        evidence_type: str = "document",
        file_url: Optional[str] = None,
        scan_job_template_id: Optional[str] = None,
        scan_execution_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Initialize Evidence model."""
        if evidence_id is None:
            evidence_id = str(uuid.uuid4())

        super().__init__(
            evidence_id=evidence_id,
            control_id=control_id,
            title=title,
            description=description,
            evidence_type=evidence_type,
            file_url=file_url,
            scan_job_template_id=scan_job_template_id,
            scan_execution_id=scan_execution_id,
            **kwargs,
        )

    def update_file_url(self, file_url: str) -> None:
        """Update the file URL for this evidence."""
        self.file_url = file_url
        self.save()

    @classmethod
    def get_by_control(cls, control_id: str) -> List["Evidence"]:
        """Get all evidence for a control."""
        return list(cls.control_index.query(control_id))

    @classmethod
    def get_by_control_and_type(
        cls, control_id: str, evidence_type: str
    ) -> List["Evidence"]:
        """Get evidence by control and type."""
        all_evidence = cls.get_by_control(control_id)
        return [
            evidence
            for evidence in all_evidence
            if evidence.evidence_type == evidence_type
        ]

    @classmethod
    def create_evidence(
        cls,
        control_id: str,
        title: str,
        description: str,
        evidence_type: str = "document",
        file_url: Optional[str] = None,
        scan_job_template_id: Optional[str] = None,
        scan_execution_id: Optional[str] = None,
    ) -> "Evidence":
        """Create new evidence."""
        evidence = cls(
            control_id=control_id,
            title=title,
            description=description,
            evidence_type=evidence_type,
            file_url=file_url,
            scan_job_template_id=scan_job_template_id,
            scan_execution_id=scan_execution_id,
        )
        evidence.save()
        return evidence

    @classmethod
    def get_recent_evidence(cls, control_id: str, limit: int = 10) -> List["Evidence"]:
        """Get recent evidence for a control, ordered by creation date."""
        return list(
            cls.control_index.query(control_id, limit=limit, scan_index_forward=False)
        )

    def has_file(self) -> bool:
        """Check if this evidence has an associated file."""
        return self.file_url is not None and self.file_url.strip() != ""

    def is_automated_collection(self) -> bool:
        """Check if this evidence uses automated collection."""
        return self.evidence_type == "automated_collection"

    def update_scan_execution_id(self, execution_id: str) -> None:
        """Update the scan execution ID for this evidence."""
        self.scan_execution_id = execution_id
        self.save()

    def get_scan_job_template(self) -> Optional["ScanJobTemplate"]:
        """Get the scan job template associated with this evidence."""
        if not self.scan_job_template_id:
            return None

        from app.database.models.scan_job_templates import ScanJobTemplate

        try:
            return ScanJobTemplate.get(self.scan_job_template_id)
        except ScanJobTemplate.DoesNotExist:
            return None

    def get_latest_scan_execution(self) -> Optional["ScanJobExecution"]:
        """Get the latest scan execution for this evidence."""
        if not self.is_automated_collection():
            return None
        return ScanJobExecution.get_latest_execution(self.evidence_id)
