"""Chat session models for storing conversation history."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from pynamodb.attributes import NumberAttribute, UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.indexes import AllProjection, GlobalSecondaryIndex

from app.database.base import BaseModel
from app.database.config import db_config

_DEFAULT_TTL_DAYS = 7


class SessionIndex(GlobalSecondaryIndex):
    """GSI for fetching messages by session ID in chronological order."""

    class Meta:
        index_name = "session-id-created-at-index"
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5

    session_id = UnicodeAttribute(hash_key=True)
    created_at = UTCDateTimeAttribute(range_key=True)


class ChatSessionMessage(BaseModel):
    """DynamoDB model representing a single chat message."""

    class Meta:
        table_name = db_config.chat_sessions_table_name
        region = db_config.region
        if db_config.endpoint_url:
            host = db_config.endpoint_url

    user_id = UnicodeAttribute(hash_key=True)
    message_key = UnicodeAttribute(range_key=True)

    session_id = UnicodeAttribute()
    message_id = UnicodeAttribute()
    role = UnicodeAttribute()
    content = UnicodeAttribute()
    summary_chunk = UnicodeAttribute(null=True)
    actions = UnicodeAttribute(null=True)
    ttl = NumberAttribute(null=True)
    token_count = NumberAttribute(null=True)
    sequence = NumberAttribute(null=True)

    session_index = SessionIndex()

    @classmethod
    def build_message_key(
        cls, session_id: str, created_at: Optional[datetime] = None, sequence: int = 0
    ) -> str:
        """Construct a unique sort key for storing messages in chronological order."""
        timestamp = (created_at or datetime.now(timezone.utc)).isoformat()
        return f"{session_id}#{timestamp}#{sequence:04d}"

    @classmethod
    def ttl_timestamp(cls, days: int = _DEFAULT_TTL_DAYS) -> int:
        """Generate a TTL timestamp in epoch seconds."""
        expiry = datetime.now(timezone.utc) + timedelta(days=days)
        return int(expiry.timestamp())

    @classmethod
    def new_message(
        cls,
        *,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        created_at: Optional[datetime] = None,
        sequence: int = 0,
        token_count: Optional[int] = None,
        summary_chunk: Optional[str] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        ttl_days: int = _DEFAULT_TTL_DAYS,
    ) -> "ChatSessionMessage":
        """Factory helper for building a message instance with sensible defaults."""
        created_at = created_at or datetime.now(timezone.utc)
        message_id = str(uuid4())
        message_key = cls.build_message_key(session_id, created_at, sequence)
        ttl_value = cls.ttl_timestamp(ttl_days)

        # Serialize actions to JSON if provided
        actions_json = json.dumps(actions) if actions else None

        instance = cls(
            user_id=user_id,
            message_key=message_key,
            session_id=session_id,
            message_id=message_id,
            role=role,
            content=content,
            summary_chunk=summary_chunk,
            actions=actions_json,
            ttl=ttl_value,
            token_count=token_count,
            sequence=sequence or None,
        )
        instance.created_at = created_at
        instance.updated_at = created_at
        return instance

    @classmethod
    def serialize_history(
        cls, messages: Iterable["ChatSessionMessage"]
    ) -> List[Dict[str, Any]]:
        """Convert message models into OpenAI-compatible chat message payload."""
        history: List[Dict[str, Any]] = []
        for item in messages:
            history.append({"role": item.role, "content": item.content})
        return history

    def get_actions(self) -> Optional[List[Dict[str, Any]]]:
        """Parse and return the actions list from JSON."""
        if not self.actions:
            return None
        try:
            return json.loads(self.actions)
        except (json.JSONDecodeError, TypeError):
            return None
