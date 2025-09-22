"""Job template model for PynamoDB."""

import uuid
from typing import Dict, List, Optional, Any

from pynamodb.attributes import UnicodeAttribute, MapAttribute

from app.database.base import BaseModel
from app.database.config import db_config


class JobTemplate(BaseModel):
    """Job template model for storing reusable scan configurations."""

    class Meta:
        """Meta configuration for the JobTemplate table."""

        table_name = db_config.job_templates_table_name
        region = db_config.region
        if db_config.endpoint_url:
            host = db_config.endpoint_url

    # Primary key
    template_id = UnicodeAttribute(hash_key=True)

    # Template attributes
    name = UnicodeAttribute()
    description = UnicodeAttribute()
    scan_type = UnicodeAttribute()  # aws_config/nessus/qualys/custom_script/etc
    config = MapAttribute()  # Scan-specific configuration parameters
    is_active = UnicodeAttribute(default="true")  # "true"/"false" for soft delete

    def __init__(
        self,
        template_id: Optional[str] = None,
        name: str = "",
        description: str = "",
        scan_type: str = "",
        config: Optional[Dict[str, Any]] = None,
        is_active: str = "true",
        **kwargs,
    ) -> None:
        """Initialize JobTemplate model."""
        if template_id is None:
            template_id = str(uuid.uuid4())

        if config is None:
            config = {}

        super().__init__(
            template_id=template_id,
            name=name,
            description=description,
            scan_type=scan_type,
            config=config,
            is_active=is_active,
            **kwargs,
        )

    def deactivate(self) -> None:
        """Soft delete the template by setting is_active to false."""
        self.is_active = "false"
        self.save()

    def activate(self) -> None:
        """Activate the template by setting is_active to true."""
        self.is_active = "true"
        self.save()

    @classmethod
    def get_all_templates(cls, active_only: bool = True) -> List["JobTemplate"]:
        """Get all templates in the system."""
        if active_only:
            return list(cls.scan(filter_condition=cls.is_active == "true"))
        return list(cls.scan())

    @classmethod
    def get_by_type(
        cls, scan_type: str, active_only: bool = True
    ) -> List["JobTemplate"]:
        """Get templates by scan type."""
        templates = cls.get_all_templates(active_only)
        return [t for t in templates if t.scan_type == scan_type]

    @classmethod
    def create_template(
        cls,
        name: str,
        description: str,
        scan_type: str,
        config: Dict[str, Any],
    ) -> "JobTemplate":
        """Create new scan job template."""
        template = cls(
            name=name,
            description=description,
            scan_type=scan_type,
            config=config,
        )
        template.save()
        return template

    @classmethod
    def get_active_templates(cls) -> List["JobTemplate"]:
        """Get all active templates, ordered by creation date."""
        return list(
            cls.scan(
                filter_condition=cls.is_active == "true",
            )
        )

    def get_config_value(self, key: str) -> Optional[Any]:
        """Get a specific configuration value."""
        return self.config.get(key) if self.config else None

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update the template configuration."""
        self.config = new_config
        self.save()
