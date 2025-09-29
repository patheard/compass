"""Chat streaming service for WebSocket and REST API responses."""

import json
import logging
import os
from typing import AsyncGenerator, List, Dict, Any
from fastapi import WebSocket
from openai import AsyncAzureOpenAI
from app.database.models.users import User

logger = logging.getLogger(__name__)

class ChatStreamingService:
    """Service for handling streaming chat responses."""

    def __init__(self):
        """Initialize the chat streaming service."""
        self.azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.azure_api_version = os.environ.get("AZURE_OPENAI_API_VERSION")
        self.model_name = os.environ.get("AZURE_OPENAI_MODEL")

    async def stream_response(
        self, user_message: str, user: User
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat response based on user input.

        For now, returns a random response in chunks to simulate streaming.
        In the future, this would integrate with an actual AI service.
        """
        # If AsyncAzureOpenAI is available and environment is configured, stream from the LLM


        try:
            client = AsyncAzureOpenAI(
                azure_endpoint=self.azure_endpoint,
                api_key=self.azure_api_key,
                api_version=self.azure_api_version,
            )

            # Prepare simple chat messages; you may want to expand system/context later
            messages: List[Dict[str, Any]] = [
                {
                    "role": "system",
                    "content": """
                        You are a helpful assistant for guiding teams through a Security Assessment and Authorization process.
                        This process involves evaluating NIST 800-53 revision 5 controls and documenting how the system meets each control.
                        Use concise language and provide accurate information. 
                        When unsure, say "I don't know" or suggest consulting a professional. Never make up answers.
                        Always respond using markdown.
                    """,
                },
                {"role": "user", "content": user_message},
            ]

            stream = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True,
            )

            async for chunk in stream:
                try:
                    choice = chunk.choices[0]
                    delta = getattr(choice, "delta", None)
                    content = None
                    if delta is not None:
                        content = getattr(delta, "content", None)
                    if content is None and isinstance(chunk, dict):
                        content = (
                            chunk.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content")
                        )
                    if content:
                        yield content
                except Exception:
                    # If an unexpected chunk shape is received, ignore and continue
                    continue

            return
        except Exception as e:
            logger.exception(
                "Azure OpenAI streaming failed, falling back to static responses: %s",
                e,
            )

    async def stream_to_websocket(
        self, user_message: str, user: User, websocket: WebSocket
    ) -> None:
        """Stream response directly to WebSocket connection."""
        try:
            # Send start message
            await websocket.send_text(json.dumps({"type": "start", "content": ""}))

            # Stream response chunks
            async for chunk in self.stream_response(user_message, user):
                await websocket.send_text(
                    json.dumps({"type": "chunk", "content": chunk})
                )

            # Send end message
            await websocket.send_text(json.dumps({"type": "end", "content": ""}))

        except Exception as e:
            logger.error(f"Error in WebSocket streaming: {str(e)}")

            # Send error message if websocket is still open
            try:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "content": "Sorry, I encountered an error while processing your request. Please try again.",
                        }
                    )
                )
            except Exception as _e:
                logger.debug(
                    f"Failed to send error message over websocket: {_e}"
                )

    async def get_full_response(self, user_message: str, user: User) -> str:
        """Get complete response for REST API (non-streaming)."""
        chunks = []
        async for chunk in self.stream_response(user_message, user):
            chunks.append(chunk)
        return "".join(chunks)


chat_service = ChatStreamingService()
