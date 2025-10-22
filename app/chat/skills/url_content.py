"""Skill for fetching and providing URL content as context."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from app.chat.skills.base import Action, AgentSkill, SkillContext, SkillResult

logger = logging.getLogger(__name__)


class URLContentSkill(AgentSkill):
    """Skill that detects URLs in messages and fetches their content.

    This skill does not provide user-facing actions. Instead, it enriches
    the conversation context by fetching content from URLs mentioned in
    user messages.
    """

    name = "url_content"
    description = "Fetch content from URLs mentioned in messages"
    action_types: List[str] = []  # No user actions

    URL_PATTERN = re.compile(r"https://[^\s]+")

    def __init__(
        self,
        enabled: bool = True,
        max_content_length: int = 10000,
        timeout: int = 3,
        max_urls: int = 5,
    ) -> None:
        """Initialize the URL content skill.

        Args:
            enabled: Whether this skill is enabled
            max_content_length: Maximum characters to extract from URL
            timeout: HTTP request timeout in seconds
            max_urls: Maximum number of URLs to fetch content from
        """
        self.enabled = enabled
        self.max_content_length = max_content_length
        self.timeout = timeout
        self.max_urls = max_urls

    async def can_execute(
        self, action_type: str, params: Dict[str, Any], context: SkillContext
    ) -> bool:
        """This skill does not handle actions."""
        return False

    async def execute(
        self, action_type: str, params: Dict[str, Any], context: SkillContext
    ) -> SkillResult:
        """This skill does not execute actions."""
        return SkillResult(success=False, message="No actions available")

    async def get_available_actions(self, context: SkillContext) -> List[Action]:
        """This skill provides no user actions."""
        return []

    async def fetch_url_content_from_message(self, user_message: str) -> Optional[str]:
        """Extract URLs from message and fetch their content.

        Args:
            user_message: The user's message text

        Returns:
            Combined content from all URLs, or None if no URLs found
        """
        if not self.enabled:
            return None

        urls = self._extract_urls(user_message)
        if not urls:
            return None

        # Limit to max_urls
        urls_to_fetch = urls[: self.max_urls]
        logger.info(
            f"Fetching content from {len(urls_to_fetch)} URL(s): {urls_to_fetch}"
        )

        # Fetch content from all URLs
        contents = []
        for url in urls_to_fetch:
            content = await self._fetch_url_content(url)
            if content:
                contents.append(f"Content from {url}:\n{content}")

        if not contents:
            return None

        # Combine all fetched content
        return "\n\n---\n\n".join(contents)

    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text.

        Args:
            text: Text to search for URLs

        Returns:
            List of URLs found
        """
        return self.URL_PATTERN.findall(text)

    async def _fetch_url_content(self, url: str) -> Optional[str]:
        """Fetch and extract text content from a URL.

        Args:
            url: URL to fetch

        Returns:
            Extracted text content or None on failure
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()

                # Parse HTML and extract text
                soup = BeautifulSoup(response.content, "html.parser")

                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()

                # Get text
                text = soup.get_text(separator="\n", strip=True)

                # Truncate if too long
                if len(text) > self.max_content_length:
                    text = text[: self.max_content_length] + "...[truncated]"

                return text

        except httpx.HTTPError as exc:
            logger.warning(f"HTTP error fetching URL {url}: {exc}")
            return None
        except Exception as exc:
            logger.exception(f"Error fetching URL {url}: {exc}")
            return None
