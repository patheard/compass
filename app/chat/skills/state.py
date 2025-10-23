"""Conversation state management for multi-step flows."""

from typing import Any, Dict, List, Optional

from app.chat.skills.base import Action
from app.database.models.chat_sessions import ChatSessionMessage


class ConversationState:
    """Manages multi-step conversation state."""

    STATE_KEY = "conversation_state"

    @staticmethod
    def from_history(
        messages: List[ChatSessionMessage],
    ) -> Optional[Dict[str, Any]]:
        """Extract conversation state from most recent assistant message.

        Only checks the most recent assistant message for state. This ensures
        that any new assistant message without a state marker clears the
        conversation state.

        Args:
            messages: List of recent chat messages

        Returns:
            Conversation state dict if found in most recent assistant message, else None
        """
        # Find the most recent assistant message
        for message in reversed(messages):
            if message.role == "assistant":
                actions = message.get_actions()
                if actions:
                    for action in actions:
                        # Check if this is a state marker action
                        if action.get("action_type") == "_state_marker":
                            params = action.get("params", {})
                            if ConversationState.STATE_KEY in params:
                                state = params[ConversationState.STATE_KEY]
                                # Treat empty dict or None as no state
                                if state:
                                    return state
                # Found most recent assistant message, stop searching
                return None
        return None

    @staticmethod
    def create_state_action(
        state_data: Dict[str, Any], visible_action: Optional[Action] = None
    ) -> Action:
        """Create an action that carries conversation state.

        Args:
            state_data: State data to persist
            visible_action: Optional visible action to show to user

        Returns:
            Action with embedded state
        """
        params = {ConversationState.STATE_KEY: state_data}
        if visible_action:
            params["visible_action"] = visible_action.to_dict()

        return Action(
            action_type="_state_marker",
            label="",
            description="",
            params=params,
        )

    @staticmethod
    def extract_from_action(action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract conversation state from an action dict.

        Args:
            action: Action dictionary

        Returns:
            State data if present, else None
        """
        if isinstance(action, dict):
            params = action.get("params", {})
            return params.get(ConversationState.STATE_KEY)
        return None
