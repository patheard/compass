"""MCP client for fetching content from URLs in user messages."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup

from app.chat.mcp_clients.base import BaseMCPClient, MCPContext

logger = logging.getLogger(__name__)


class URLContentMCPClient(BaseMCPClient):
    """MCP client that detects URLs and fetches their content.

    When a URL is found in the user's message, this client fetches
    the content and provides it as context for the LLM.
    """

    URL_PATTERN = re.compile(r"https://[^\s]+")

    def __init__(
        self,
        enabled: bool = True,
        max_content_length: int = 10000,
        timeout: int = 3,
        max_urls: int = 5,
    ) -> None:
        """Initialize the URL content MCP client.

        Args:
            enabled: Whether this client is enabled
            max_content_length: Maximum characters to extract from URL
            timeout: HTTP request timeout in seconds
            max_urls: Maximum number of URLs to fetch content from
        """
        super().__init__(enabled=enabled)
        self.max_content_length = max_content_length
        self.timeout = timeout
        self.max_urls = max_urls

    @property
    def name(self) -> str:
        """Return the name of this MCP client."""
        return "url_content"

    async def process(
        self, user_message: str, user_id: str, **kwargs: Any
    ) -> Optional[MCPContext]:
        """Process user message and fetch URL content if found.

        Args:
            user_message: The user's message text
            user_id: The user ID
            **kwargs: Additional context

        Returns:
            MCPContext with URL content if URL found, None otherwise
        """
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
        combined_content = "\n\n---\n\n".join(contents)

        return MCPContext(
            content=combined_content,
            metadata={
                "urls_fetched": urls_to_fetch,
                "urls_found": urls,
                "fetch_count": len(contents),
            },
            client_name=self.name,
        )

    def _extract_urls(self, text: str) -> list[str]:
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
