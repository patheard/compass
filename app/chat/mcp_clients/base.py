"""Base class for MCP (Model Context Protocol) clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class MCPContext:
    """Context data returned by MCP clients."""

    content: str
    metadata: Dict[str, Any]
    client_name: str


class BaseMCPClient(ABC):
    """Base class for MCP clients that enhance chat context.

    MCP clients analyze user messages and optionally add context
    to help the LLM provide better responses.
    """

    def __init__(self, enabled: bool = True) -> None:
        """Initialize the MCP client.

        Args:
            enabled: Whether this client is enabled
        """
        self.enabled = enabled

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this MCP client."""
        pass

    @abstractmethod
    async def process(
        self, user_message: str, user_id: str, **kwargs: Any
    ) -> Optional[MCPContext]:
        """Process a user message and optionally return context.

        Args:
            user_message: The user's message text
            user_id: The user ID
            **kwargs: Additional context (session_id, current_url, etc.)

        Returns:
            MCPContext if this client has relevant context, None otherwise
        """
        pass

    async def __call__(
        self, user_message: str, user_id: str, **kwargs: Any
    ) -> Optional[MCPContext]:
        """Make the client callable."""
        if not self.enabled:
            return None
        return await self.process(user_message, user_id, **kwargs)
