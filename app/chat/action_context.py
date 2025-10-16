"""Context-aware action suggestion system for chat interface."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.assessments.services import AssessmentService
from app.controls.services import ControlService
from app.evidence.services import EvidenceService
from app.job_templates.services import JobTemplateService

logger = logging.getLogger(__name__)


class ActionContext:
    """Determines available actions based on current URL and context."""

    # URL patterns for different page types
    ASSESSMENT_PATTERN = r"/assessments/([a-f0-9-]+)$"
    CONTROL_PATTERN = r"/assessments/([a-f0-9-]+)/controls/([a-f0-9-]+)$"
    EVIDENCE_PATTERN = (
        r"/assessments/([a-f0-9-]+)/controls/([a-f0-9-]+)/evidence/([a-f0-9-]+)$"
    )

    def __init__(self) -> None:
        """Initialize action context service."""
        self.assessment_service = AssessmentService()
        self.control_service = ControlService()
        self.evidence_service = EvidenceService()
        self.job_template_service = JobTemplateService()

    async def get_context_and_actions(
        self, current_url: Optional[str], user_id: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Get context information and available actions based on current URL.

        Args:
            current_url: Current page URL
            user_id: Current user ID for authorization

        Returns:
            Tuple of (context_text, available_actions)
        """
        if not current_url:
            return "", []

        # Try to match control page
        control_match = re.search(self.CONTROL_PATTERN, current_url)
        if control_match:
            return await self._get_control_context(
                control_match.group(1), control_match.group(2), user_id
            )

        # Try to match evidence page
        evidence_match = re.search(self.EVIDENCE_PATTERN, current_url)
        if evidence_match:
            return await self._get_evidence_context(
                evidence_match.group(1), evidence_match.group(2), user_id
            )

        # Try to match assessment page
        assessment_match = re.search(self.ASSESSMENT_PATTERN, current_url)
        if assessment_match:
            return await self._get_assessment_context(
                assessment_match.group(1), user_id
            )

        return "", []

    async def _get_assessment_context(
        self, assessment_id: str, user_id: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Get context for assessment page.

        Actions: Identify AWS services from Terraform files.
        """
        try:
            assessment = self.assessment_service.get_assessment(assessment_id, user_id)
            if not assessment:
                return "", []

            # Build action for identifying AWS resources
            actions = []
            context = ""
            if assessment.aws_account_id:
                context += "The following actions are available:"
                actions.append(
                    {
                        "action_type": "identify_aws_resources",
                        "label": "Identify AWS services",
                        "description": "Scan Terraform files to identify AWS services used in this project",
                        "params": {
                            "assessment_id": assessment_id,
                        },
                    }
                )

            return context, actions
        except Exception as e:
            logger.exception(f"Error getting assessment context: {e}")
            return "", []

    async def _get_control_context(
        self, assessment_id: str, control_id: str, user_id: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Get context for control page.

        Actions: Create automated evidence based on available job templates.
        """
        try:
            # Get control details
            control_response = self.control_service.get_control(control_id, user_id)
            if not control_response:
                return "", []

            # Get assessment details for infrastructure context
            assessment_response = self.assessment_service.get_assessment(
                assessment_id, user_id
            )
            if not assessment_response:
                return "", []

            context = ""

            # Get available job templates and build action suggestions
            actions = await self._build_evidence_actions(
                control_id=control_id,
                user_id=user_id,
                assessment=assessment_response,
            )

            # Add available actions to context
            if actions:
                context += "\nAutomated evidence that can be added:\n"
                for action in actions:
                    template_name = action["params"]["template_name"]
                    template_desc = action["params"]["template_description"]
                    context += f"- **{template_name}**: {template_desc}\n"

            return context, actions
        except Exception as e:
            logger.exception(f"Error getting control context: {e}")
            return "", []

    async def _get_evidence_context(
        self, assessment_id: str, control_id: str, user_id: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Get context for evidence page.

        No actions available on evidence pages.
        """
        try:
            control_response = self.control_service.get_control(control_id, user_id)
            if not control_response:
                return "", []

            context = f"User is viewing evidence for control: {control_response.nist_control_id}: {control_response.control_title}\n"

            return context, []
        except Exception as e:
            logger.exception(f"Error getting evidence context: {e}")
            return "", []

    async def _build_evidence_actions(
        self,
        control_id: str,
        user_id: str,
        assessment: Any,
    ) -> List[Dict[str, Any]]:
        """Build action suggestions for creating automated evidence.

        Args:
            control_id: ID of the control
            assessment: Assessment object containing infrastructure info

        Returns:
            List of action dictionaries
        """
        actions = []

        try:
            # Get all active job templates
            templates = self.job_template_service.get_active_templates()

            # Filter templates based on assessment infrastructure
            relevant_templates = []
            assessment_aws_resources = set(assessment.aws_resources or [])
            for template in templates:
                # For AWS Config templates, require AWS account and filter on resources
                if template.scan_type == "aws_config":
                    if assessment.aws_account_id:
                        template_aws_resource = set(template.aws_resources or [])
                        if (
                            not assessment_aws_resources
                            or assessment_aws_resources.intersection(
                                template_aws_resource
                            )
                        ):
                            relevant_templates.append(template)

            # Remove evidence templates that are already associated with the control
            existing_evidence = self.evidence_service.list_evidence_by_control(
                control_id, user_id
            )
            existing_job_templates = {
                evidence.job_template_id for evidence in existing_evidence
            }
            relevant_templates = [
                template
                for template in relevant_templates
                if template.template_id not in existing_job_templates
            ]

            # Build action for each relevant template
            for template in relevant_templates:
                action = {
                    "action_type": "add_evidence",
                    "label": f"Add evidence: {template.name}",
                    "description": f"Create automated evidence using {template.name}",
                    "params": {
                        "control_id": control_id,
                        "evidence_type": "automated_collection",
                        "title": f"{template.name}",
                        "description": template.description,
                        "job_template_id": template.template_id,
                        "template_name": template.name,
                        "template_description": template.description,
                        "scan_type": template.scan_type,
                    },
                }

                # Add AWS account if available
                if assessment.aws_account_id:
                    action["params"]["aws_account_id"] = assessment.aws_account_id

                actions.append(action)

        except Exception as e:
            logger.exception(f"Error building evidence actions: {e}")

        return actions
