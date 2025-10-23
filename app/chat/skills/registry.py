"""Skill registry for managing and discovering agent skills."""

import logging
from typing import Any, Dict, List, Optional

from app.chat.skills.base import Action, AgentSkill, SkillContext

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Central registry for all agent skills."""

    def __init__(self) -> None:
        """Initialize skill registry."""
        self._skills: List[AgentSkill] = []
        self._skills_by_name: Dict[str, AgentSkill] = {}

    def register(self, skill: AgentSkill) -> None:
        """Register a skill.

        Args:
            skill: Skill to register
        """
        self._skills.append(skill)
        if skill.name:
            self._skills_by_name[skill.name] = skill
        logger.info(f"Registered skill: {skill.name}")

    async def find_skill(
        self, action_type: str, params: Dict[str, Any], context: SkillContext
    ) -> Optional[AgentSkill]:
        """Find skill that can handle this action.

        Args:
            action_type: Type of action to find skill for
            params: Action parameters
            context: Skill context

        Returns:
            Skill that can handle the action, or None
        """
        for skill in self._skills:
            try:
                if await skill.can_execute(action_type, params, context):
                    logger.debug(
                        f"Found skill '{skill.name}' for action '{action_type}'"
                    )
                    return skill
            except Exception as e:
                logger.exception(
                    f"Error checking if skill '{skill.name}' can execute action '{action_type}': {e}"
                )
                continue
        return None

    async def get_all_available_actions(self, context: SkillContext) -> List[Action]:
        """Collect all available actions from all skills.

        Args:
            context: Skill context

        Returns:
            List of all available actions
        """
        actions: List[Action] = []
        for skill in self._skills:
            try:
                skill_actions = await skill.get_available_actions(context)
                actions.extend(skill_actions)
                logger.debug(
                    f"Skill '{skill.name}' provided {len(skill_actions)} actions"
                )
            except Exception as e:
                logger.exception(
                    f"Error getting available actions from skill '{skill.name}': {e}"
                )
                continue
        return actions

    def get_skill_by_name(self, name: str) -> Optional[AgentSkill]:
        """Get skill by name.

        Args:
            name: Skill name

        Returns:
            Skill with given name, or None
        """
        return self._skills_by_name.get(name)

    def get_all_skills(self) -> List[AgentSkill]:
        """Get all registered skills.

        Returns:
            List of all registered skills
        """
        return self._skills.copy()

    async def get_prompt_enhancements(
        self, user_message: str, context: SkillContext
    ) -> List[str]:
        """Get prompt enhancements from all relevant skills.

        Args:
            user_message: User's message
            context: Skill context

        Returns:
            List of prompt enhancement strings
        """
        enhancements: List[str] = []
        for skill in self._skills:
            try:
                if await skill.should_enhance_prompt(user_message, context):
                    enhancement = await skill.get_prompt_enhancement(
                        user_message, context
                    )
                    if enhancement:
                        enhancements.append(enhancement)
                        logger.debug(
                            f"Skill '{skill.name}' provided prompt enhancement"
                        )
            except Exception as e:
                logger.exception(
                    f"Error getting prompt enhancement from skill '{skill.name}': {e}"
                )
                continue
        return enhancements
