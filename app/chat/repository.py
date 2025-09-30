"""Persistence layer for chat sessions backed by DynamoDB."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional, Sequence, Tuple
from uuid import uuid4

from app.database.models.chat_sessions import ChatSessionMessage


@dataclass
class ChatMessageRecord:
    """Transport object representing a chat message history entry."""

    role: str
    content: str
    created_at: datetime


@dataclass
class HistoryWindow:
    """Container describing a bounded history fetch."""

    messages: List[ChatSessionMessage]
    truncated: bool
    token_estimate: int


class ChatHistoryRepository:
    """Repository for reading and writing chat history to DynamoDB."""

    def __init__(self, ttl_days: int = 7) -> None:
        self.ttl_days = ttl_days

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def ensure_session(
        self,
        *,
        user_id: str,
        session_id: Optional[str],
    ) -> Tuple[str, bool]:
        """Resolve the session identifier for a conversation.

        Returns the (possibly new) session_id and a flag indicating whether
        the session was newly created.
        """

        if session_id:
            belongs_to_user = await self._session_belongs_to_user(
                session_id=session_id,
                user_id=user_id,
            )
            if not belongs_to_user:
                raise PermissionError("Session does not belong to user")
            return session_id, False

        new_session_id = str(uuid4())
        return new_session_id, True

    async def load_recent_history(
        self,
        *,
        user_id: str,
        session_id: str,
        max_tokens: int = 2500,
        max_messages: int = 40,
    ) -> HistoryWindow:
        """Fetch the most recent messages for the session capped by token budget."""

        def _load() -> HistoryWindow:
            messages: List[ChatSessionMessage] = []
            token_budget = 0
            truncated = False

            query = ChatSessionMessage.session_index.query(
                session_id,
                scan_index_forward=False,
                limit=max_messages,
            )

            for message in query:
                if message.user_id != user_id:
                    continue

                estimated_tokens = message.token_count or self.estimate_token_count(
                    message.content
                )
                if token_budget + estimated_tokens > max_tokens and messages:
                    truncated = True
                    break

                token_budget += estimated_tokens
                messages.append(message)
                if len(messages) >= max_messages:
                    truncated = True
                    break

            messages.reverse()
            return HistoryWindow(
                messages=messages,
                truncated=truncated,
                token_estimate=token_budget,
            )

        return await asyncio.to_thread(_load)

    async def append_message(
        self,
        *,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        created_at: Optional[datetime] = None,
    ) -> ChatSessionMessage:
        """Persist a single message for the session."""

        created_at = created_at or datetime.now(timezone.utc)

        token_count = self.estimate_token_count(content)

        def _save() -> ChatSessionMessage:
            sequence = self._next_sequence_value(session_id)
            message = ChatSessionMessage.new_message(
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=content,
                created_at=created_at,
                sequence=sequence,
                token_count=token_count,
                ttl_days=self.ttl_days,
            )
            message.save()
            return message

        return await asyncio.to_thread(_save)

    async def append_transcript(
        self,
        *,
        user_id: str,
        session_id: str,
        messages: Iterable[Tuple[str, str]],
    ) -> List[ChatSessionMessage]:
        """Persist a batch of messages for the session."""

        created_at = datetime.now(timezone.utc)

        def _save_batch() -> List[ChatSessionMessage]:
            persisted: List[ChatSessionMessage] = []
            sequence = self._next_sequence_value(session_id)
            for role, content in messages:
                message = ChatSessionMessage.new_message(
                    user_id=user_id,
                    session_id=session_id,
                    role=role,
                    content=content,
                    created_at=created_at,
                    sequence=sequence,
                    token_count=self.estimate_token_count(content),
                    ttl_days=self.ttl_days,
                )
                message.save()
                persisted.append(message)
                sequence += 1

            return persisted

        return await asyncio.to_thread(_save_batch)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _session_belongs_to_user(self, session_id: str, user_id: str) -> bool:
        def _check() -> bool:
            query = ChatSessionMessage.session_index.query(
                session_id,
                limit=1,
                scan_index_forward=True,
            )
            for message in query:
                return message.user_id == user_id
            return True

        return await asyncio.to_thread(_check)

    def _next_sequence_value(self, session_id: str) -> int:
        query = ChatSessionMessage.session_index.query(
            session_id,
            scan_index_forward=False,
            limit=1,
        )
        for message in query:
            if message.sequence is not None:
                return int(message.sequence) + 1
            return 1
        return 0

    @staticmethod
    def estimate_token_count(content: str) -> int:
        """Cheap heuristic for token estimation based on message length."""
        if not content:
            return 0
        # Rough heuristic assuming ~4 characters per token
        return max(1, len(content) // 4)

    @staticmethod
    def to_records(
        messages: Sequence[ChatSessionMessage],
    ) -> List[ChatMessageRecord]:
        """Convert database models into lightweight records."""
        records: List[ChatMessageRecord] = []
        for message in messages:
            records.append(
                ChatMessageRecord(
                    role=message.role,
                    content=message.content,
                    created_at=message.created_at,
                )
            )
        return records
