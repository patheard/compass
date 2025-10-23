"""Chat streaming service for WebSocket and REST API responses."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import boto3
from fastapi import WebSocket
from openai import AsyncAzureOpenAI

from app.chat.repository import ChatHistoryRepository
from app.chat.skills import (
    SkillContextFactory,
    SkillRegistry,
    ConversationState,
    create_skill_registry,
)
from app.database.models.chat_sessions import ChatSessionMessage
from app.database.models.users import User

logger = logging.getLogger(__name__)


def filter_internal_actions(
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


class StreamWithActions:
    """Wrapper for async generator that also holds actions."""

    def __init__(
        self,
        generator: AsyncGenerator[str, None],
        actions_container: Dict[str, Optional[List[Dict[str, Any]]]],
    ):
        self.generator = generator
        self.actions_container = actions_container

    @property
    def actions(self) -> Optional[List[Dict[str, Any]]]:
        """Get actions from the container."""
        return self.actions_container.get("actions")

    def __aiter__(self):
        return self.generator.__aiter__()

    async def __anext__(self):
        return await self.generator.__anext__()

    async def aclose(self):
        if hasattr(self.generator, "aclose"):
            await self.generator.aclose()


class ChatStreamingService:
    """Service for handling streaming chat responses."""

    DEFAULT_SYSTEM_PROMPT = (
        "You are a security assistant for guiding teams through a Security Assessment and "
        "Authorization process. This process involves evaluating NIST 800-53 revision 5 "
        "controls and documenting how the system meets each control. Use concise language "
        "and provide accurate information.\n\n"
        "When a URL is provided, the contents of the page will be retrieved and provided as "
        "context to help answer questions more accurately.\n\n"
        "When unsure, suggest consulting a professional. Never make up answers. "
        "Always respond using markdown.\n\n"
    )

    VECTOR_CONTEXT_PROMPT = "Use the following context from embeddings search to assist with the user's query:\n"

    def __init__(
        self,
        repository: Optional[ChatHistoryRepository] = None,
        skill_registry: Optional[SkillRegistry] = None,
        skill_context_factory: Optional[SkillContextFactory] = None,
    ) -> None:
        """Initialize the chat streaming service."""
        self.azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.azure_api_version = os.environ.get("AZURE_OPENAI_API_VERSION")
        self.azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.completions_model_name = os.environ.get(
            "AZURE_OPENAI_COMPLETIONS_MODEL_NAME"
        )
        self.embeddings_model_name = os.environ.get(
            "AZURE_OPENAI_EMBEDDINGS_MODEL_NAME"
        )
        self.s3_vector_bucket = os.environ.get("S3_VECTOR_BUCKET_NAME")
        self.s3_vector_index = os.environ.get("S3_VECTOR_INDEX_NAME")
        self.s3_vector_region = os.environ.get("S3_VECTOR_REGION")
        self.s3_vector_top_k = int(os.environ.get("S3_VECTOR_TOP_K", "3"))
        self.repository = repository or ChatHistoryRepository()
        self.skill_registry = skill_registry or create_skill_registry()
        self.skill_context_factory = skill_context_factory or SkillContextFactory(
            repository=self.repository
        )
        self.max_history_tokens = int(os.environ.get("CHAT_HISTORY_MAX_TOKENS", "2500"))
        self.max_history_messages = int(
            os.environ.get("CHAT_HISTORY_MAX_MESSAGES", "20")
        )
        self.s3_vectors_client = boto3.client(
            "s3vectors", region_name=self.s3_vector_region
        )

    async def stream_response(
        self,
        user: User,
        user_message: str,
        session_id: Optional[str] = None,
        current_page: Optional[str] = None,
        current_url: Optional[str] = None,
    ) -> Tuple[str, AsyncGenerator[str, None]]:
        """Stream a chat response based on user input.

        Returns:
            Tuple of (session_id, response_generator)
        """

        session_id, messages, actions = await self._prepare_session_messages(
            user=user,
            session_id=session_id,
            user_message=user_message,
            current_page=current_page,
            current_url=current_url,
        )

        client = self._build_client()
        if client is None:
            raise RuntimeError("Azure OpenAI client not configured")

        # Use a mutable container to store actions that can be updated from within the generator
        actions_container: Dict[str, Optional[List[Dict[str, Any]]]] = {"actions": None}

        async def _generator() -> AsyncGenerator[str, None]:
            assistant_chunks: List[str] = []
            if client is None:
                logger.error(
                    "Azure OpenAI client is not configured; no response will be streamed."
                )
                return

            # If messages is empty, the conversation was handled by a special handler
            # (e.g., evidence conversation) and response is already persisted
            # We need to retrieve the last assistant message and stream it
            if not messages:
                # Get the last assistant message from history
                window = await self.repository.load_recent_history(
                    user_id=user.user_id,
                    session_id=session_id,
                    max_tokens=1000,
                    max_messages=1,
                )
                if window.messages:
                    last_message = window.messages[-1]
                    if last_message.role == "assistant":
                        # Stream the already-persisted response
                        yield last_message.content
                        # Store actions for later retrieval (filter out internal actions)
                        actions_container["actions"] = filter_internal_actions(
                            last_message.get_actions()
                        )
                        logger.info(
                            f"Retrieved actions from last message: {actions_container['actions']}"
                        )
                return

            try:
                stream = await client.chat.completions.create(
                    model=self.completions_model_name,
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
                        # Persist the message
                        await self.repository.append_message(
                            user_id=user.user_id,
                            session_id=session_id,
                            role="assistant",
                            content=assistant_text,
                            actions=None,
                        )
                    except Exception as exc:
                        logger.exception(
                            "Failed to persist assistant response: %s", exc
                        )

        # Wrap the generator with actions container reference
        wrapped_generator = StreamWithActions(_generator(), actions_container)
        return session_id, wrapped_generator

    async def stream_to_websocket(
        self,
        user_message: str,
        user: User,
        websocket: WebSocket,
        session_id: Optional[str] = None,
        current_page: Optional[str] = None,
        current_url: Optional[str] = None,
    ) -> None:
        """Stream response directly to WebSocket connection."""
        stream_session_id, response_stream = await self.stream_response(
            user,
            user_message,
            session_id,
            current_page,
            current_url,
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

            # Get actions from generator if available
            actions = None
            if isinstance(response_stream, StreamWithActions):
                actions = filter_internal_actions(response_stream.actions)
                logger.info(f"Actions to send in WebSocket end message: {actions}")

            # Send `end` message with actions
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "end",
                        "content": "",
                        "session_id": stream_session_id,
                        "actions": actions,
                    }
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
        user: User,
        message: str,
        session_id: Optional[str] = None,
        current_page: Optional[str] = None,
        current_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get complete response for REST API (non-streaming)."""

        resolved_session_id, response_stream = await self.stream_response(
            user,
            message,
            session_id,
            current_page,
            current_url,
        )

        chunks: List[str] = []
        async for chunk in response_stream:
            if chunk:
                chunks.append(chunk)

        if hasattr(response_stream, "aclose"):
            await response_stream.aclose()

        full_response = "".join(chunks)

        # Get actions from generator if available
        actions = None
        if isinstance(response_stream, StreamWithActions):
            actions = filter_internal_actions(response_stream.actions)

        return {
            "session_id": resolved_session_id,
            "message": full_response,
            "actions": actions,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def build_system_prompt(
        self, context: str, current_page: str, actions: List[Dict[str, Any]]
    ) -> str:
        """Build system prompt with context and available actions.

        Args:
            context: Context information about current page
            current_page: Current page content
            actions: Available actions for the current context

        Returns:
            System prompt text
        """
        prompt = self.DEFAULT_SYSTEM_PROMPT

        if context:
            prompt += f"Current page context:\n{context}\n\n"

        if current_page:
            prompt += f"Current page content:\n{current_page}\n\n"

        return prompt

    async def _generate_embeddings(self, text: str) -> Optional[List[float]]:
        """Generate embeddings from text using Azure OpenAI embeddings model."""
        if not self.embeddings_model_name:
            logger.warning("Embeddings model not configured; skipping vector search")
            return None

        client = self._build_client()
        if client is None:
            return None

        try:
            response = await client.embeddings.create(
                model=self.embeddings_model_name,
                input=text,
            )
            return response.data[0].embedding
        except Exception as exc:
            logger.exception("Failed to generate embeddings: %s", exc)
            return None

    def _query_s3_vectors(self, embeddings: List[float]) -> Optional[Dict[str, Any]]:
        """Query S3 vector index for matching vectors."""
        try:
            response = self.s3_vectors_client.query_vectors(
                vectorBucketName=self.s3_vector_bucket,
                indexName=self.s3_vector_index,
                queryVector={"float32": embeddings},
                topK=self.s3_vector_top_k,
                returnDistance=True,
                returnMetadata=True,
            )

            return response["vectors"]
        except Exception as exc:
            logger.exception("Failed to query S3 vectors: %s", exc)
            return None

    def _build_client(self) -> Optional[AsyncAzureOpenAI]:
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

    async def _prepare_session_messages(
        self,
        *,
        user: User,
        session_id: Optional[str],
        user_message: str,
        current_page: Optional[str],
        current_url: Optional[str] = None,
    ) -> tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Prepare session messages with context and actions.

        Returns:
            Tuple of (session_id, messages, actions)
        """
        session_id, _ = await self.repository.ensure_session(
            user_id=user.user_id,
            session_id=session_id,
        )

        # Check for conversation state in recent history
        window = await self.repository.load_recent_history(
            user_id=user.user_id,
            session_id=session_id,
            max_tokens=500,
            max_messages=5,
        )

        conversation_state = ConversationState.from_history(window.messages)

        if conversation_state:
            # Handle skill-based conversation
            skill_name = conversation_state.get("skill")
            skill = self.skill_registry.get_skill_by_name(skill_name)

            if skill:
                # Build context for skill
                context = await self.skill_context_factory.create(
                    user=user,
                    session_id=session_id,
                    current_url=current_url,
                    conversation_history=window.messages,
                )

                # Persist user message
                await self.repository.append_message(
                    user_id=user.user_id,
                    session_id=session_id,
                    role="user",
                    content=user_message,
                )

                # Let skill handle the conversation
                result = await skill.handle_conversation(
                    user_message=user_message,
                    state=conversation_state,
                    context=context,
                )

                # Persist response with actions
                actions_dict = None
                if result.actions:
                    actions_dict = [action.to_dict() for action in result.actions]

                # Handle conversation state
                # If conversation_state is present in result (even if None/empty), handle it
                if hasattr(result, "conversation_state") and result.conversation_state:
                    # Create state marker action to continue conversation
                    state_action = ConversationState.create_state_action(
                        result.conversation_state
                    )
                    # Append state marker to actions
                    if actions_dict is None:
                        actions_dict = []
                    actions_dict.append(state_action.to_dict())

                await self.repository.append_message(
                    user_id=user.user_id,
                    session_id=session_id,
                    role="assistant",
                    content=result.message,
                    actions=actions_dict,
                )

                # Return empty messages to bypass OpenAI
                return session_id, [], []

        # Build context for skill discovery
        context = await self.skill_context_factory.create(
            user=user,
            session_id=session_id,
            current_url=current_url,
        )

        # Get available actions from skills
        actions = await self.skill_registry.get_all_available_actions(context)
        actions_dict = [action.to_dict() for action in actions]

        # Build system prompt with context and actions
        context_text = ""
        if actions_dict:
            context_text = "Available actions for user"

        system_prompt = self.build_system_prompt(
            context_text, current_page, actions_dict
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

        # Generate embeddings and query S3 vectors for additional context
        vector_context = ""
        embeddings = await self._generate_embeddings(user_message)
        if embeddings:
            vectors = self._query_s3_vectors(embeddings)
            if vectors:
                vector_context = "\n\n".join(
                    v.get("metadata", {}).get("chunk_text", "") for v in vectors
                )

        # Get prompt enhancements from skills based on user message
        skill_enhancements = await self.skill_registry.get_prompt_enhancements(
            user_message, context
        )

        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": system_prompt,
            },
        ]

        if vector_context:
            messages.append(
                {
                    "role": "system",
                    "content": self.VECTOR_CONTEXT_PROMPT + vector_context,
                }
            )

        # Add skill enhancements as system messages
        for enhancement in skill_enhancements:
            messages.append(
                {
                    "role": "system",
                    "content": enhancement,
                }
            )

        messages.extend(history_messages)

        return session_id, messages, actions_dict

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
