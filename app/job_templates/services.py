"""Service layer for job template operations."""

from typing import Dict, List, Optional, Any

from app.database.models.job_templates import JobTemplate


class JobTemplateService:
    """Service for managing job templates."""

    @staticmethod
    def create_template(
        name: str,
        description: str,
        scan_type: str,
        config: Dict[str, Any],
    ) -> JobTemplate:
        """Create a new job template."""
        return JobTemplate.create_template(
            name=name,
            description=description,
            scan_type=scan_type,
            config=config,
        )

    @staticmethod
    def get_template(template_id: str) -> Optional[JobTemplate]:
        """Get a template by ID."""
        try:
            return JobTemplate.get(template_id)
        except JobTemplate.DoesNotExist:
            return None

    @staticmethod
    def get_all_templates(active_only: bool = True) -> List[JobTemplate]:
        """Get all templates in the system."""
        return JobTemplate.get_all_templates(active_only)

    @staticmethod
    def get_templates_by_type(
        scan_type: str, active_only: bool = True
    ) -> List[JobTemplate]:
        """Get templates by scan type."""
        return JobTemplate.get_by_type(scan_type, active_only)

    @staticmethod
    def update_template(
        template_id: str,
        name: str,
        description: str,
        scan_type: str,
        config: Dict[str, Any],
    ) -> Optional[JobTemplate]:
        """Update a job template."""
        template = JobTemplateService.get_template(template_id)
        if not template:
            return None

        template.name = name
        template.description = description
        template.scan_type = scan_type
        template.update_config(config)
        return template

    @staticmethod
    def delete_template(template_id: str) -> bool:
        """Delete (deactivate) a job template."""
        template = JobTemplateService.get_template(template_id)
        if not template:
            return False

        template.deactivate()
        return True

    @staticmethod
    def activate_template(template_id: str) -> bool:
        """Activate a job template."""
        template = JobTemplateService.get_template(template_id)
        if not template:
            return False

        template.activate()
        return True

    @staticmethod
    def get_active_templates() -> List[JobTemplate]:
        """Get all active templates."""
        return JobTemplate.get_active_templates()
