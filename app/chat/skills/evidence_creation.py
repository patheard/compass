"""Skill for creating custom evidence through conversation."""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from openai import AsyncAzureOpenAI

from app.chat.skills.base import Action, AgentSkill, SkillContext, SkillResult
from app.evidence.validation import EvidenceRequest

logger = logging.getLogger(__name__)


class EvidenceCreationSkill(AgentSkill):
    """Multi-step skill for creating custom evidence."""

    name = "evidence_creation"
    description = "Create custom evidence through conversation"
    action_types = ["add_custom_evidence", "confirm_add_evidence", "refine_evidence"]

    def __init__(self) -> None:
        """Initialize evidence creation skill."""
        self.azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.azure_api_version = os.environ.get("AZURE_OPENAI_API_VERSION")
        self.azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.completions_model_name = os.environ.get(
            "AZURE_OPENAI_COMPLETIONS_MODEL_NAME"
        )

    async def can_execute(
        self, action_type: str, params: Dict[str, Any], context: SkillContext
    ) -> bool:
        """Check if this skill can handle the action."""
        return action_type in self.action_types

    async def execute(
        self, action_type: str, params: Dict[str, Any], context: SkillContext
    ) -> SkillResult:
        """Execute the evidence creation action."""
        if action_type == "add_custom_evidence":
            return await self._start_conversation(params, context)
        elif action_type == "confirm_add_evidence":
            return await self._confirm_evidence(params, context)
        elif action_type == "refine_evidence":
            return await self._refine_evidence(params, context)

        return SkillResult(success=False, message="Unknown action")

    async def get_available_actions(self, context: SkillContext) -> List[Action]:
        """Return add_custom_evidence action if on control page."""
        actions: List[Action] = []

        # Check if on control page
        control_match = re.search(
            r"/assessments/([a-f0-9-]+)/controls/([a-f0-9-]+)$",
            context.current_url or "",
        )

        if control_match:
            control_id = control_match.group(2)
            actions.append(
                Action(
                    action_type="add_custom_evidence",
                    label="Add evidence",
                    description="Describe the evidence you want to attach to this control",
                    params={"control_id": control_id},
                )
            )

        return actions

    async def get_context_description(
        self, actions: List[Action], context: SkillContext
    ) -> Optional[str]:
        """Return context description for evidence creation capability."""
        if actions:
            return "- **Add evidence** by describing it in natural language"
        return None

    async def handle_conversation(
        self, user_message: str, state: Dict[str, Any], context: SkillContext
    ) -> SkillResult:
        """Handle multi-step evidence creation conversation."""
        step = state.get("step")
        control_id = state.get("control_id")

        if step == "awaiting_description":
            return await self._parse_and_confirm(user_message, control_id, context)
        elif step == "awaiting_confirmation":
            # User is requesting changes to the proposed evidence
            return await self._refine_evidence_from_feedback(
                user_message, control_id, state, context
            )

        return SkillResult(
            success=False,
            message="Invalid conversation state",
        )

    async def _start_conversation(
        self, params: Dict[str, Any], context: SkillContext
    ) -> SkillResult:
        """Initiate evidence conversation."""
        control_id = params.get("control_id")
        if not control_id:
            return SkillResult(success=False, message="Missing control_id")

        message = "Describe the evidence you want to attach to this control in a few sentences."

        # Create state marker
        state = {
            "skill": self.name,
            "step": "awaiting_description",
            "control_id": control_id,
        }

        return SkillResult(
            success=True,
            message=message,
            conversation_state=state,
        )

    async def _parse_and_confirm(
        self, user_message: str, control_id: str, context: SkillContext
    ) -> SkillResult:
        """Parse user description and present confirmation."""
        # Get control info for context
        control = context.control_service.get_control(control_id, context.user_id)
        if not control:
            return SkillResult(success=False, message="Control not found")

        control_info = f"{control.nist_control_id}: {control.control_title}\n{control.control_description}"

        # Parse evidence description
        try:
            parsed_evidence = await self._parse_evidence_description(
                user_message, control_info
            )
        except Exception as e:
            logger.exception(f"Error parsing evidence description: {e}")
            return SkillResult(
                success=False,
                message="Failed to parse evidence description. Please try again.",
            )

        # Create confirmation message
        message = (
            f"Here are the suggested evidence details:\n\n"
            f"**Title:** {parsed_evidence['title']}\n\n"
            f"**Type:** {parsed_evidence['evidence_type']}\n\n"
            f"**Description:** {parsed_evidence['description']}\n\n"
        )

        # Create confirmation action
        confirm_action = Action(
            action_type="confirm_add_evidence",
            label="Yes, add evidence",
            description="Add the evidence with these details",
            params={
                "control_id": control_id,
                "parsed_evidence": parsed_evidence,
            },
        )

        # Maintain conversation state to allow for refinement
        state = {
            "skill": self.name,
            "step": "awaiting_confirmation",
            "control_id": control_id,
            "parsed_evidence": parsed_evidence,
        }

        return SkillResult(
            success=True,
            message=message,
            actions=[confirm_action],
            conversation_state=state,
        )

    async def _confirm_evidence(
        self, params: Dict[str, Any], context: SkillContext
    ) -> SkillResult:
        """Create evidence from parsed data."""
        control_id = params.get("control_id")
        parsed = params.get("parsed_evidence")

        if not control_id or not parsed:
            return SkillResult(
                success=False, message="Missing control_id or parsed_evidence"
            )

        evidence_data = EvidenceRequest(
            title=parsed["title"],
            description=parsed["description"],
            evidence_type=parsed["evidence_type"],
            status="unknown",
        )

        try:
            evidence = context.evidence_service.create_evidence(
                control_id, context.user_id, evidence_data
            )
        except Exception as e:
            logger.exception(f"Error creating evidence: {e}")
            return SkillResult(success=False, message="Failed to create evidence")

        return SkillResult(
            success=True,
            message=f"Added **{parsed['title']}** evidence to the control.",
            data={"evidence_id": evidence.evidence_id},
            reload_page=True,
            conversation_state=None,
        )

    async def _refine_evidence(
        self, params: Dict[str, Any], context: SkillContext
    ) -> SkillResult:
        """Handle evidence refinement (future enhancement)."""
        return SkillResult(
            success=False,
            message="Evidence refinement not yet implemented",
        )

    async def _refine_evidence_from_feedback(
        self,
        user_message: str,
        control_id: str,
        state: Dict[str, Any],
        context: SkillContext,
    ) -> SkillResult:
        """Refine evidence based on user feedback."""
        previous_evidence = state.get("parsed_evidence")
        if not previous_evidence:
            return SkillResult(
                success=False,
                message="Previous evidence data not found. Please start over.",
            )

        # Get control info for context
        control = context.control_service.get_control(control_id, context.user_id)
        if not control:
            return SkillResult(success=False, message="Control not found")

        control_info = f"{control.nist_control_id}: {control.control_title}\n{control.control_description}"

        # Build context for refinement
        refinement_context = (
            f"Previous evidence details:\n"
            f"Title: {previous_evidence['title']}\n"
            f"Type: {previous_evidence['evidence_type']}\n"
            f"Description: {previous_evidence['description']}\n\n"
            f"User feedback: {user_message}\n\n"
            f"Control context: {control_info}"
        )

        # Parse refined evidence description
        try:
            parsed_evidence = await self._parse_evidence_description(
                refinement_context, control_info
            )
        except Exception as e:
            logger.exception(f"Error parsing refined evidence description: {e}")
            return SkillResult(
                success=False,
                message="Failed to parse refined evidence. Please try again.",
            )

        # Create confirmation message
        message = (
            f"Here are the updated evidence details:\n\n"
            f"**Title:** {parsed_evidence['title']}\n\n"
            f"**Type:** {parsed_evidence['evidence_type']}\n\n"
            f"**Description:** {parsed_evidence['description']}\n\n"
        )

        # Create confirmation action
        confirm_action = Action(
            action_type="confirm_add_evidence",
            label="Yes, add evidence",
            description="Add the evidence with these details",
            params={
                "control_id": control_id,
                "parsed_evidence": parsed_evidence,
            },
        )

        # Maintain conversation state for further refinement if needed
        state = {
            "skill": self.name,
            "step": "awaiting_confirmation",
            "control_id": control_id,
            "parsed_evidence": parsed_evidence,
        }

        return SkillResult(
            success=True,
            message=message,
            actions=[confirm_action],
            conversation_state=state,
        )

    def _build_client(self) -> Optional[AsyncAzureOpenAI]:
        """Build Azure OpenAI client."""
        if not all(
            [
                self.azure_api_key,
                self.azure_endpoint,
                self.azure_api_version,
                self.completions_model_name,
            ]
        ):
            return None

        return AsyncAzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=self.azure_api_key,
            api_version=self.azure_api_version,
        )

    async def _parse_evidence_description(
        self, user_description: str, control_info: Optional[str] = None
    ) -> Dict[str, str]:
        """Parse natural language evidence description into structured data.

        Args:
            user_description: User's natural language description of evidence
            control_info: Optional context about the control

        Returns:
            Dictionary with title, evidence_type, and description
        """
        client = self._build_client()
        if client is None:
            raise RuntimeError("Azure OpenAI client not configured")

        system_prompt = (
            "You are an assistant that extracts structured evidence information from natural language descriptions. "
            "Given a user's description of evidence for a security control, extract:\n"
            "1. A concise title (max 200 characters)\n"
            "2. An evidence type (one of: document, screenshot, other)\n"
            "3. A detailed description (max 10000 characters)\n\n"
            "Valid evidence types:\n"
            "- document: Written documentation, policies, procedures\n"
            "- screenshot: Visual evidence from systems or interfaces\n"
            "- other: Any other type of evidence\n\n"
            "Respond with a JSON object containing 'title', 'evidence_type', and 'description' fields.\n"
            "The title should be brief and descriptive. The description should expand on the user's input with relevant details.\n"
            "Do not include any markdown formatting or code blocks in your response, just the JSON object."
        )

        user_prompt = f"Evidence description: {user_description}"
        if control_info:
            user_prompt += f"\n\nControl context: {control_info}"

        try:
            response = await client.chat.completions.create(
                model=self.completions_model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from Azure OpenAI")

            parsed = json.loads(content.strip())

            # Validate required fields
            if not all(k in parsed for k in ["title", "evidence_type", "description"]):
                raise ValueError("Missing required fields in parsed evidence")

            # Validate evidence type
            valid_types = {"document", "screenshot", "automated_collection", "other"}
            if parsed["evidence_type"] not in valid_types:
                parsed["evidence_type"] = "other"

            return {
                "title": parsed["title"][:200],
                "evidence_type": parsed["evidence_type"],
                "description": parsed["description"][:10000],
            }

        except json.JSONDecodeError as e:
            logger.exception(f"Failed to parse JSON from Azure OpenAI: {e}")
            # Fallback to user's description
            return {
                "title": user_description[:200],
                "evidence_type": "other",
                "description": user_description[:10000],
            }
        except Exception as e:
            logger.exception(f"Error parsing evidence description: {e}")
            raise
