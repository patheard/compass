"""Service layer for scan job template operations."""

from typing import Dict, List, Optional, Any

from app.database.models.scan_job_templates import ScanJobTemplate


class ScanJobTemplateService:
    """Service for managing scan job templates."""

    @staticmethod
    def create_template(
        name: str,
        description: str,
        scan_type: str,
        config: Dict[str, Any],
    ) -> ScanJobTemplate:
        """Create a new scan job template."""
        return ScanJobTemplate.create_template(
            name=name,
            description=description,
            scan_type=scan_type,
            config=config,
        )

    @staticmethod
    def get_template(template_id: str) -> Optional[ScanJobTemplate]:
        """Get a template by ID."""
        try:
            return ScanJobTemplate.get(template_id)
        except ScanJobTemplate.DoesNotExist:
            return None

    @staticmethod
    def get_all_templates(active_only: bool = True) -> List[ScanJobTemplate]:
        """Get all templates in the system."""
        return ScanJobTemplate.get_all_templates(active_only)

    @staticmethod
    def get_templates_by_type(
        scan_type: str, active_only: bool = True
    ) -> List[ScanJobTemplate]:
        """Get templates by scan type."""
        return ScanJobTemplate.get_by_type(scan_type, active_only)

    @staticmethod
    def update_template(
        template_id: str,
        name: str,
        description: str,
        scan_type: str,
        config: Dict[str, Any],
    ) -> Optional[ScanJobTemplate]:
        """Update a scan job template."""
        template = ScanJobTemplateService.get_template(template_id)
        if not template:
            return None

        template.name = name
        template.description = description
        template.scan_type = scan_type
        template.update_config(config)
        return template

    @staticmethod
    def delete_template(template_id: str) -> bool:
        """Delete (deactivate) a scan job template."""
        template = ScanJobTemplateService.get_template(template_id)
        if not template:
            return False

        template.deactivate()
        return True

    @staticmethod
    def activate_template(template_id: str) -> bool:
        """Activate a scan job template."""
        template = ScanJobTemplateService.get_template(template_id)
        if not template:
            return False

        template.activate()
        return True

    @staticmethod
    def get_active_templates() -> List[ScanJobTemplate]:
        """Get all active templates."""
        return ScanJobTemplate.get_active_templates()
