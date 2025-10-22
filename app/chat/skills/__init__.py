"""Agent skills system for composable chat actions."""

from app.chat.skills.automated_evidence import AutomatedEvidenceSkill
from app.chat.skills.aws_scanner import AWSResourceScannerSkill
from app.chat.skills.base import Action, AgentSkill, SkillContext, SkillResult
from app.chat.skills.context import SkillContextFactory
from app.chat.skills.evidence_creation import EvidenceCreationSkill
from app.chat.skills.registry import SkillRegistry
from app.chat.skills.state import ConversationState
from app.chat.skills.url_content import URLContentSkill

__all__ = [
    "Action",
    "AgentSkill",
    "SkillContext",
    "SkillResult",
    "SkillRegistry",
    "ConversationState",
    "SkillContextFactory",
    "AutomatedEvidenceSkill",
    "AWSResourceScannerSkill",
    "EvidenceCreationSkill",
    "URLContentSkill",
    "create_skill_registry",
]


def create_skill_registry() -> SkillRegistry:
    """Create and initialize skill registry with all available skills.

    Returns:
        Configured SkillRegistry with all skills registered
    """
    registry = SkillRegistry()

    # Register all skills
    registry.register(AutomatedEvidenceSkill())
    registry.register(AWSResourceScannerSkill())
    registry.register(EvidenceCreationSkill())
    registry.register(URLContentSkill())

    return registry
