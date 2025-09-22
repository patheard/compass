"""Job execution model for PynamoDB."""

import uuid
from typing import Dict, List, Optional, Any

from pynamodb.attributes import (
    UnicodeAttribute,
    UTCDateTimeAttribute,
    MapAttribute,
    NumberAttribute,
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

from app.database.base import BaseModel
from app.database.config import db_config


class EvidenceIndex(GlobalSecondaryIndex):
    """Global secondary index for evidence lookups."""

    class Meta:
        """Meta configuration for the evidence index."""

        index_name = "evidence-index"
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5

    evidence_id = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class JobExecution(BaseModel):
    """Job execution model for tracking individual scan job runs."""

    class Meta:
        """Meta configuration for the JobExecution table."""

        table_name = db_config.job_executions_table_name
        region = db_config.region
        if db_config.endpoint_url:
            host = db_config.endpoint_url

    # Primary key
    execution_id = UnicodeAttribute(hash_key=True)

    # Execution attributes
    template_id = UnicodeAttribute()
    evidence_id = UnicodeAttribute()
    status = UnicodeAttribute()  # pending/running/completed/failed/cancelled
    started_at = UTCDateTimeAttribute(null=True)
    completed_at = UTCDateTimeAttribute(null=True)
    result_data = MapAttribute(null=True)  # Scan results and metadata
    error_message = UnicodeAttribute(null=True)  # Error details if execution failed
    retry_count = NumberAttribute(default=0)  # Number of retry attempts
    executor_id = UnicodeAttribute(
        null=True
    )  # ID of worker/service that executed the job
    execution_config = MapAttribute(
        null=True
    )  # Runtime configuration used for execution

    # Global secondary index
    evidence_index = EvidenceIndex()

    def __init__(
        self,
        execution_id: Optional[str] = None,
        template_id: str = "",
        evidence_id: str = "",
        status: str = "pending",
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0,
        executor_id: Optional[str] = None,
        execution_config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """Initialize JobExecution model."""
        if execution_id is None:
            execution_id = str(uuid.uuid4())

        super().__init__(
            execution_id=execution_id,
            template_id=template_id,
            evidence_id=evidence_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            result_data=result_data,
            error_message=error_message,
            retry_count=retry_count,
            executor_id=executor_id,
            execution_config=execution_config,
            **kwargs,
        )

    def start_execution(self, executor_id: str) -> None:
        """Mark execution as started."""
        from datetime import datetime

        self.status = "running"
        self.executor_id = executor_id
        self.started_at = datetime.utcnow()
        self.save()

    def complete_execution(self, result_data: Dict[str, Any]) -> None:
        """Mark execution as completed with results."""
        from datetime import datetime

        self.status = "completed"
        self.result_data = result_data
        self.completed_at = datetime.utcnow()
        self.save()

    def fail_execution(self, error_message: str) -> None:
        """Mark execution as failed with error message."""
        from datetime import datetime

        self.status = "failed"
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        self.save()

    def cancel_execution(self) -> None:
        """Mark execution as cancelled."""
        from datetime import datetime

        self.status = "cancelled"
        self.completed_at = datetime.utcnow()
        self.save()

    def increment_retry(self) -> None:
        """Increment retry count and reset status to pending."""
        self.retry_count += 1
        self.status = "pending"
        self.error_message = None
        self.executor_id = None
        self.save()

    @classmethod
    def get_by_evidence(cls, evidence_id: str) -> List["JobExecution"]:
        """Get all executions for an evidence record."""
        return list(cls.evidence_index.query(evidence_id))

    @classmethod
    def get_latest_execution(cls, evidence_id: str) -> Optional["JobExecution"]:
        """Get the latest execution for an evidence record."""
        executions = list(
            cls.evidence_index.query(evidence_id, limit=1, scan_index_forward=False)
        )
        return executions[0] if executions else None

    @classmethod
    def get_pending_executions(cls) -> List["JobExecution"]:
        """Get all pending executions across all evidence."""
        # Note: This requires a scan operation
        return list(cls.scan(filter_condition=cls.status == "pending"))

    @classmethod
    def get_running_executions(cls) -> List["JobExecution"]:
        """Get all running executions across all evidence."""
        # Note: This requires a scan operation
        return list(cls.scan(filter_condition=cls.status == "running"))

    @classmethod
    def create_execution(
        cls,
        template_id: str,
        evidence_id: str,
        execution_config: Optional[Dict[str, Any]] = None,
    ) -> "JobExecution":
        """Create new scan job execution."""
        execution = cls(
            template_id=template_id,
            evidence_id=evidence_id,
            execution_config=execution_config,
        )
        execution.save()
        return execution

    @classmethod
    def get_execution_history(
        cls, evidence_id: str, limit: int = 10
    ) -> List["JobExecution"]:
        """Get execution history for evidence, ordered by creation date."""
        return list(
            cls.evidence_index.query(evidence_id, limit=limit, scan_index_forward=False)
        )

    def is_complete(self) -> bool:
        """Check if execution is in a terminal state."""
        return self.status in ["completed", "failed", "cancelled"]

    def is_active(self) -> bool:
        """Check if execution is currently active."""
        return self.status in ["pending", "running"]

    def get_result_value(self, key: str) -> Optional[Any]:
        """Get a specific result value."""
        return self.result_data.get(key) if self.result_data else None

    def set_aws_config_compliance_results(
        self, compliance_data: Dict[str, Any]
    ) -> None:
        """Set AWS Config compliance results."""
        if not self.result_data:
            self.result_data = {}

        self.result_data["compliance_results"] = compliance_data
        self.result_data["scan_type"] = "aws_config"

    def get_aws_config_compliance_results(self) -> Optional[Dict[str, Any]]:
        """Get AWS Config compliance results."""
        if not self.result_data:
            return None
        return self.result_data.get("compliance_results")
