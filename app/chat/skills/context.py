"""Factory for creating skill contexts with dependencies."""

import logging
from typing import List, Optional

from app.assessments.services import AssessmentService
from app.chat.repository import ChatHistoryRepository
from app.chat.skills.base import SkillContext
from app.controls.services import ControlService
from app.database.models.chat_sessions import ChatSessionMessage
from app.database.models.users import User
from app.evidence.services import EvidenceService
from app.job_templates.services import JobTemplateService

logger = logging.getLogger(__name__)


class SkillContextFactory:
    """Factory for creating skill contexts with injected dependencies."""

    def __init__(
        self,
        assessment_service: Optional[AssessmentService] = None,
        control_service: Optional[ControlService] = None,
        evidence_service: Optional[EvidenceService] = None,
        job_template_service: Optional[JobTemplateService] = None,
        repository: Optional[ChatHistoryRepository] = None,
    ) -> None:
        """Initialize context factory with optional service overrides."""
        self.assessment_service = assessment_service or AssessmentService()
        self.control_service = control_service or ControlService()
        self.evidence_service = evidence_service or EvidenceService()
        self.job_template_service = job_template_service or JobTemplateService()
        self.repository = repository or ChatHistoryRepository()

    async def create(
        self,
        user: User,
        session_id: Optional[str] = None,
        current_url: Optional[str] = None,
        current_page: Optional[str] = None,
        csrf_token: Optional[str] = None,
        conversation_history: Optional[List[ChatSessionMessage]] = None,
    ) -> SkillContext:
        """Create skill context with user info and services.

        Args:
            user: Authenticated user
            session_id: Chat session ID
            current_url: Current page URL
            current_page: Current page content
            csrf_token: CSRF token for actions
            conversation_history: Optional conversation history

        Returns:
            Configured SkillContext
        """
        # Load conversation history if not provided
        if conversation_history is None and session_id:
            try:
                window = await self.repository.load_recent_history(
                    user_id=user.user_id,
                    session_id=session_id,
                    max_tokens=500,
                    max_messages=5,
                )
                conversation_history = window.messages
            except Exception as e:
                logger.exception(f"Error loading conversation history: {e}")
                conversation_history = []

        return SkillContext(
            user_id=user.user_id,
            session_id=session_id or "",
            current_url=current_url,
            current_page=current_page,
            conversation_history=conversation_history or [],
            csrf_token=csrf_token,
            assessment_service=self.assessment_service,
            control_service=self.control_service,
            evidence_service=self.evidence_service,
            job_template_service=self.job_template_service,
            repository=self.repository,
        )
