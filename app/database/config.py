"""Database configuration for DynamoDB."""

import os
from typing import Optional


class DatabaseConfig:
    """Configuration for DynamoDB connection."""

    def __init__(self) -> None:
        """Initialize database configuration."""
        self.region: str = os.getenv("AWS_REGION", "ca-central-1")
        self.endpoint_url: Optional[str] = os.getenv("DYNAMODB_ENDPOINT_URL")
        self.table_prefix: str = os.getenv("DYNAMODB_TABLE_PREFIX", "compass")

    @property
    def users_table_name(self) -> str:
        """Get the users table name."""
        return f"{self.table_prefix}-users"

    @property
    def security_assessments_table_name(self) -> str:
        """Get the security assessments table name."""
        return f"{self.table_prefix}-security-assessments"

    @property
    def controls_table_name(self) -> str:
        """Get the controls table name."""
        return f"{self.table_prefix}-controls"

    @property
    def evidence_table_name(self) -> str:
        """Get the evidence table name."""
        return f"{self.table_prefix}-evidence"

    @property
    def job_templates_table_name(self) -> str:
        """Get the job templates table name."""
        return f"{self.table_prefix}-job-templates"

    @property
    def job_executions_table_name(self) -> str:
        """Get the job executions table name."""
        return f"{self.table_prefix}-job-executions"


# Global configuration instance
db_config = DatabaseConfig()
