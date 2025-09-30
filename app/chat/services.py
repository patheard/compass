"""Chat streaming service for WebSocket and REST API responses."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from fastapi import WebSocket
from openai import AsyncAzureOpenAI

from app.chat.repository import ChatHistoryRepository
from app.database.models.chat_sessions import ChatSessionMessage
from app.database.models.users import User

logger = logging.getLogger(__name__)


class ChatStreamingService:
    """Service for handling streaming chat responses."""

    DEFAULT_SYSTEM_PROMPT = (
        "You are a helpful assistant for guiding teams through a Security Assessment and "
        "Authorization process. This process involves evaluating NIST 800-53 revision 5 "
        "controls and documenting how the system meets each control. Use concise language "
        "and provide accurate information. When unsure, say 'I don't know' or suggest "
        "consulting a professional. Never make up answers. Always respond using markdown."
        "To help with context here is the current page content:\n"
    )

    def __init__(self, repository: Optional[ChatHistoryRepository] = None) -> None:
        """Initialize the chat streaming service."""
        self.azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.azure_api_version = os.environ.get("AZURE_OPENAI_API_VERSION")
        self.model_name = os.environ.get("AZURE_OPENAI_MODEL")
        self.repository = repository or ChatHistoryRepository()
        self.max_history_tokens = int(os.environ.get("CHAT_HISTORY_MAX_TOKENS", "2500"))
        self.max_history_messages = int(
            os.environ.get("CHAT_HISTORY_MAX_MESSAGES", "40")
        )

    async def stream_response(
        self,
        user_message: str,
        user: User,
        session_id: Optional[str] = None,
        current_page: Optional[str] = None,
    ) -> Tuple[str, AsyncGenerator[str, None]]:
        """Stream a chat response based on user input."""

        session_id, messages = await self._prepare_session_messages(
            user=user,
            session_id=session_id,
            user_message=user_message,
            current_page=current_page,
        )

        client = self._build_client()

        async def _generator() -> AsyncGenerator[str, None]:
            assistant_chunks: List[str] = []
            if client is None:
                logger.error(
                    "Azure OpenAI client is not configured; no response will be streamed."
                )
                return

            try:
                stream = await client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    stream=True,
                )

                async for chunk in stream:
                    content = self._extract_chunk_content(chunk)
                    if content:
                        assistant_chunks.append(content)
                        yield content
            except Exception as exc:
                logger.exception("Azure OpenAI streaming failed: %s", exc)
            finally:
                assistant_text = "".join(assistant_chunks).strip()
                if assistant_text:
                    try:
                        await self.repository.append_message(
                            user_id=user.user_id,
                            session_id=session_id,
                            role="assistant",
                            content=assistant_text,
                        )
                    except Exception as exc:
                        logger.exception(
                            "Failed to persist assistant response: %s", exc
                        )

        return session_id, _generator()

    async def stream_to_websocket(
        self,
        user_message: str,
        user: User,
        websocket: WebSocket,
        session_id: Optional[str] = None,
        current_page: Optional[str] = None,
    ) -> None:
        """Stream response directly to WebSocket connection."""
        stream_session_id, response_stream = await self.stream_response(
            user_message,
            user,
            session_id,
            current_page,
        )

        try:
            await websocket.send_text(
                json.dumps(
                    {"type": "start", "content": "", "session_id": stream_session_id}
                )
            )

            async for chunk in response_stream:
                if not chunk:
                    continue
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "chunk",
                            "content": chunk,
                            "session_id": stream_session_id,
                        }
                    )
                )

            await websocket.send_text(
                json.dumps(
                    {"type": "end", "content": "", "session_id": stream_session_id}
                )
            )

        except Exception as exc:  # noqa: BLE001
            logger.exception("Error in WebSocket streaming: %s", exc)
            try:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "content": "Sorry, I encountered an error while processing your request. Please try again.",
                            "session_id": stream_session_id,
                        }
                    )
                )
            except Exception:  # noqa: BLE001
                logger.debug(
                    "Failed to send error message over websocket", exc_info=True
                )
        finally:
            if hasattr(response_stream, "aclose"):
                await response_stream.aclose()

    async def get_full_response(
        self,
        user_message: str,
        user: User,
        session_id: Optional[str] = None,
        current_page: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get complete response for REST API (non-streaming)."""

        resolved_session_id, response_stream = await self.stream_response(
            user_message,
            user,
            session_id,
            current_page,
        )

        chunks: List[str] = []
        async for chunk in response_stream:
            if chunk:
                chunks.append(chunk)

        if hasattr(response_stream, "aclose"):
            await response_stream.aclose()

        return {"session_id": resolved_session_id, "message": "".join(chunks)}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_client(self) -> Optional[AsyncAzureOpenAI]:
        if not all(
            [
                self.azure_api_key,
                self.azure_endpoint,
                self.azure_api_version,
                self.model_name,
            ]
        ):
            return None

        return AsyncAzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=self.azure_api_key,
            api_version=self.azure_api_version,
        )

    async def _prepare_session_messages(
        self,
        *,
        user: User,
        session_id: Optional[str],
        user_message: str,
        current_page: Optional[str],
    ) -> tuple[str, List[Dict[str, Any]]]:
        session_id, _ = await self.repository.ensure_session(
            user_id=user.user_id,
            session_id=session_id,
        )

        window = await self.repository.load_recent_history(
            user_id=user.user_id,
            session_id=session_id,
            max_tokens=self.max_history_tokens,
            max_messages=self.max_history_messages,
        )

        history_messages = ChatSessionMessage.serialize_history(window.messages)

        persisted_user_message = await self.repository.append_message(
            user_id=user.user_id,
            session_id=session_id,
            role="user",
            content=user_message,
        )
        history_messages.append(
            {"role": "user", "content": persisted_user_message.content}
        )

        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": self.DEFAULT_SYSTEM_PROMPT + (current_page or ""),
            },
        ]
        messages.extend(history_messages)

        return session_id, messages

    @staticmethod
    def _extract_chunk_content(chunk: Any) -> Optional[str]:
        try:
            choice = chunk.choices[0]
            delta = getattr(choice, "delta", None)
            content = None
            if delta is not None:
                content = getattr(delta, "content", None)
            if content is None and isinstance(chunk, dict):
                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
            return content
        except Exception:  # noqa: BLE001
            return None
