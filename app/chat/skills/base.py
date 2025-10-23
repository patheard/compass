"""Base classes for agent skills system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.assessments.services import AssessmentService
from app.chat.repository import ChatHistoryRepository
from app.controls.services import ControlService
from app.database.models.chat_sessions import ChatSessionMessage
from app.evidence.services import EvidenceService
from app.job_templates.services import JobTemplateService


@dataclass
class Action:
    """Represents an action button shown to user."""

    action_type: str
    label: str
    description: str
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary for JSON serialization."""
        return {
            "action_type": self.action_type,
            "label": self.label,
            "description": self.description,
            "params": self.params,
        }

    @staticmethod
    def filter_internal(
        actions: Optional[List[Dict[str, Any]]],
    ) -> Optional[List[Dict[str, Any]]]:
        """Filter out internal actions like state markers from user-facing action lists.

        Args:
            actions: List of action dictionaries

        Returns:
            Filtered list without internal actions, or None if no visible actions remain
        """
        if not actions:
            return None

        visible_actions = [
            action for action in actions if action.get("action_type") != "_state_marker"
        ]

        return visible_actions if visible_actions else None


@dataclass
class SkillContext:
    """Context available to all skills during execution."""

    user_id: str
    session_id: str
    assessment_service: AssessmentService
    control_service: ControlService
    evidence_service: EvidenceService
    job_template_service: JobTemplateService
    repository: ChatHistoryRepository
    current_url: Optional[str] = None
    current_page: Optional[str] = None
    conversation_history: List[ChatSessionMessage] = field(default_factory=list)
    csrf_token: Optional[str] = None


@dataclass
class SkillResult:
    """Result from skill execution."""

    success: bool
    message: str
    actions: Optional[List[Action]] = None
    data: Optional[Dict[str, Any]] = None
    conversation_state: Optional[Dict[str, Any]] = None
    reload_page: bool = False


class AgentSkill(ABC):
    """Base class for all agent skills."""

    # Skill metadata (to be set by subclasses)
    name: str = ""
    description: str = ""
    action_types: List[str] = []

    @abstractmethod
    async def can_execute(
        self, action_type: str, params: Dict[str, Any], context: SkillContext
    ) -> bool:
        """Check if this skill can handle the action.

        Args:
            action_type: Type of action to execute
            params: Action parameters
            context: Skill context with user info and services

        Returns:
            True if this skill can handle the action
        """
        pass

    @abstractmethod
    async def execute(
        self, action_type: str, params: Dict[str, Any], context: SkillContext
    ) -> SkillResult:
        """Execute the action and return result with optional next actions.

        Args:
            action_type: Type of action to execute
            params: Action parameters
            context: Skill context with user info and services

        Returns:
            SkillResult with success status, message, and optional actions
        """
        pass

    @abstractmethod
    async def get_available_actions(self, context: SkillContext) -> List[Action]:
        """Return actions this skill can provide in current context.

        Args:
            context: Skill context with user info and services

        Returns:
            List of available actions for current context
        """
        pass

    async def get_context_description(
        self, actions: List[Action], context: SkillContext
    ) -> Optional[str]:
        """Return optional context description for this skill's capabilities.

        This description will be shown to the user when this skill has available actions.
        Should be a concise bullet point describing what the user can do.

        Args:
            actions: List of available actions from this skill
            context: Skill context with user info and services

        Returns:
            Context description string or None if no description needed
        """
        return None

    async def handle_conversation(
        self, user_message: str, state: Dict[str, Any], context: SkillContext
    ) -> SkillResult:
        """Handle multi-step conversation flow (optional).

        Args:
            user_message: User's message in the conversation
            state: Current conversation state
            context: Skill context with user info and services

        Returns:
            SkillResult with response and optional next actions
        """
        return SkillResult(
            success=False,
            message="This skill does not support conversation handling",
        )

    async def should_enhance_prompt(
        self, user_message: str, context: SkillContext
    ) -> bool:
        """Determine if this skill should enhance the system prompt.

        Args:
            user_message: User's message
            context: Skill context

        Returns:
            True if this skill can enhance the prompt for this message
        """
        return False

    async def get_prompt_enhancement(
        self, user_message: str, context: SkillContext
    ) -> Optional[str]:
        """Get content to add to system prompt.

        Args:
            user_message: User's message
            context: Skill context

        Returns:
            Content to add to system prompt, or None
        """
        return None
