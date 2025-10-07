"""Service layer for job template operations."""

from typing import List, Optional

from app.database.models.job_templates import JobTemplate
from app.job_templates.validation import JobTemplateRequest


class JobTemplateService:
    """Service for managing job templates."""

    @staticmethod
    def create_template(
        data: JobTemplateRequest,
    ) -> JobTemplate:
        """Create a new job template."""
        return JobTemplate.create_template(
            name=data.name,
            description=data.description,
            scan_type=data.scan_type,
            config=data.config,
            aws_resources=data.aws_resources,
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
        data: JobTemplateRequest,
    ) -> Optional[JobTemplate]:
        """Update a job template."""
        template = JobTemplateService.get_template(template_id)
        if not template:
            return None

        template.name = data.name
        template.description = data.description
        template.scan_type = data.scan_type
        template.aws_resources = data.aws_resources
        template.update_config(data.config)
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
