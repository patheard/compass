"""Skill for creating automated evidence from job templates."""

import logging
import re
from typing import Any, Dict, List

from app.chat.skills.base import Action, AgentSkill, SkillContext, SkillResult
from app.evidence.validation import EvidenceRequest

logger = logging.getLogger(__name__)


class AutomatedEvidenceSkill(AgentSkill):
    """Skill for creating automated evidence using job templates."""

    name = "automated_evidence"
    description = "Create automated evidence using job templates"
    action_types = ["add_evidence"]

    async def can_execute(
        self, action_type: str, params: Dict[str, Any], context: SkillContext
    ) -> bool:
        """Check if this skill can handle the action."""
        return action_type == "add_evidence" and "job_template_id" in params

    async def execute(
        self, action_type: str, params: Dict[str, Any], context: SkillContext
    ) -> SkillResult:
        """Execute the automated evidence creation."""
        control_id = params.get("control_id")
        if not control_id:
            return SkillResult(success=False, message="Missing control_id")

        # Validate required parameters
        required = ["title", "description", "evidence_type"]
        for param in required:
            if param not in params:
                return SkillResult(success=False, message=f"Missing {param}")

        evidence_data = EvidenceRequest(
            title=params["title"],
            description=params["description"],
            evidence_type=params["evidence_type"],
            job_template_id=params.get("job_template_id"),
            aws_account_id=params.get("aws_account_id"),
        )

        try:
            evidence = context.evidence_service.create_evidence(
                control_id, context.user_id, evidence_data
            )
        except Exception as e:
            logger.exception(f"Error creating automated evidence: {e}")
            return SkillResult(success=False, message="Failed to create evidence")

        return SkillResult(
            success=True,
            message=f"Added **{params['title']}** evidence to the control",
            data={"evidence_id": evidence.evidence_id},
            reload_page=True,
        )

    async def get_available_actions(self, context: SkillContext) -> List[Action]:
        """Build automated evidence actions based on available templates."""
        actions: List[Action] = []

        # Parse URL for control context
        control_match = re.search(
            r"/assessments/([a-f0-9-]+)/controls/([a-f0-9-]+)$",
            context.current_url or "",
        )

        if not control_match:
            return actions

        assessment_id = control_match.group(1)
        control_id = control_match.group(2)

        try:
            # Get assessment and control
            assessment = context.assessment_service.get_assessment(
                assessment_id, context.user_id
            )
            control = context.control_service.get_control(control_id, context.user_id)

            if not assessment or not control:
                return actions

            # Find relevant templates
            templates = self._find_relevant_templates(assessment, control, context)

            # Create action for each template
            for template in templates:
                action = Action(
                    action_type="add_evidence",
                    label=f"Add evidence: {template.name}",
                    description=f"Create automated evidence using {template.name}",
                    params={
                        "control_id": control_id,
                        "evidence_type": "automated_collection",
                        "title": template.name,
                        "description": template.description,
                        "job_template_id": template.template_id,
                        "aws_account_id": assessment.aws_account_id,
                    },
                )
                actions.append(action)

        except Exception as e:
            logger.exception(f"Error building automated evidence actions: {e}")

        return actions

    def _find_relevant_templates(
        self, assessment: Any, control: Any, context: SkillContext
    ) -> List[Any]:
        """Find templates matching assessment and control."""
        templates = context.job_template_service.get_active_templates()
        assessment_resources = set(assessment.aws_resources or [])

        relevant = []
        for template in templates:
            if template.scan_type == "aws_config":
                if assessment.aws_account_id:
                    template_resources = set(template.aws_resources or [])
                    if (
                        control.nist_control_id in template.nist_control_ids
                        and assessment_resources.intersection(template_resources)
                    ):
                        relevant.append(template)

        # Filter out existing evidence
        existing = context.evidence_service.list_evidence_by_control(
            control.control_id, context.user_id
        )
        existing_ids = {e.job_template_id for e in existing if e.job_template_id}

        return [t for t in relevant if t.template_id not in existing_ids]
