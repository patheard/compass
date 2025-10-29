"""Unit tests for chat repository."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.chat.repository import (
    ChatHistoryRepository,
    ChatMessageRecord,
    HistoryWindow,
)
from app.database.models.chat_sessions import ChatSessionMessage


@pytest.fixture
def repository() -> ChatHistoryRepository:
    """Create a ChatHistoryRepository instance."""
    return ChatHistoryRepository(ttl_days=7)


@pytest.fixture
def mock_message() -> ChatSessionMessage:
    """Create a mock chat message."""
    message = MagicMock(spec=ChatSessionMessage)
    message.user_id = "test-user-id"
    message.session_id = "test-session-id"
    message.role = "user"
    message.content = "test message"
    message.created_at = datetime.now(timezone.utc)
    message.sequence = 1
    message.token_count = 10
    return message


class TestChatHistoryRepository:
    """Tests for ChatHistoryRepository class."""

    def test_repository_initialization(self) -> None:
        """Test repository initialization with default TTL."""
        repo = ChatHistoryRepository()

        assert repo.ttl_days == 7

    def test_repository_initialization_custom_ttl(self) -> None:
        """Test repository initialization with custom TTL."""
        repo = ChatHistoryRepository(ttl_days=30)

        assert repo.ttl_days == 30

    @pytest.mark.asyncio
    async def test_ensure_session_with_existing_session(
        self, repository: ChatHistoryRepository
    ) -> None:
        """Test ensure_session with an existing session ID."""
        with patch.object(
            repository, "_session_belongs_to_user", return_value=True
        ) as mock_check:
            session_id, is_new = await repository.ensure_session(
                user_id="test-user",
                session_id="existing-session",
            )

            assert session_id == "existing-session"
            assert is_new is False
            mock_check.assert_called_once_with(
                session_id="existing-session", user_id="test-user"
            )

    @pytest.mark.asyncio
    async def test_ensure_session_with_invalid_session(
        self, repository: ChatHistoryRepository
    ) -> None:
        """Test ensure_session with session that doesn't belong to user."""
        with patch.object(repository, "_session_belongs_to_user", return_value=False):
            with pytest.raises(PermissionError, match="Session does not belong"):
                await repository.ensure_session(
                    user_id="test-user",
                    session_id="other-session",
                )

    @pytest.mark.asyncio
    async def test_ensure_session_without_session_id(
        self, repository: ChatHistoryRepository
    ) -> None:
        """Test ensure_session creates new session when no ID provided."""
        session_id, is_new = await repository.ensure_session(
            user_id="test-user",
            session_id=None,
        )

        assert session_id is not None
        assert len(session_id) > 0
        assert is_new is True

    @pytest.mark.asyncio
    async def test_append_message(self, repository: ChatHistoryRepository) -> None:
        """Test appending a message to a session."""
        mock_message = MagicMock(spec=ChatSessionMessage)

        with patch.object(repository, "_next_sequence_value", return_value=5):
            with patch(
                "app.chat.repository.ChatSessionMessage.new_message",
                return_value=mock_message,
            ) as mock_new:
                result = await repository.append_message(
                    user_id="test-user",
                    session_id="test-session",
                    role="user",
                    content="test content",
                )

                assert result == mock_message
                mock_new.assert_called_once()
                call_kwargs = mock_new.call_args.kwargs
                assert call_kwargs["user_id"] == "test-user"
                assert call_kwargs["session_id"] == "test-session"
                assert call_kwargs["role"] == "user"
                assert call_kwargs["content"] == "test content"
                assert call_kwargs["sequence"] == 5
                assert call_kwargs["ttl_days"] == 7
                mock_message.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_append_message_with_actions(
        self, repository: ChatHistoryRepository
    ) -> None:
        """Test appending a message with actions."""
        mock_message = MagicMock(spec=ChatSessionMessage)
        actions = [{"type": "test", "data": "value"}]

        with patch.object(repository, "_next_sequence_value", return_value=1):
            with patch(
                "app.chat.repository.ChatSessionMessage.new_message",
                return_value=mock_message,
            ) as mock_new:
                await repository.append_message(
                    user_id="test-user",
                    session_id="test-session",
                    role="assistant",
                    content="response",
                    actions=actions,
                )

                call_kwargs = mock_new.call_args.kwargs
                assert call_kwargs["actions"] == actions

    @pytest.mark.asyncio
    async def test_append_transcript(self, repository: ChatHistoryRepository) -> None:
        """Test appending multiple messages as a transcript."""
        messages = [("user", "hello"), ("assistant", "hi there")]
        mock_messages = [MagicMock(spec=ChatSessionMessage) for _ in messages]

        with patch.object(repository, "_next_sequence_value", return_value=0):
            with patch(
                "app.chat.repository.ChatSessionMessage.new_message",
                side_effect=mock_messages,
            ) as mock_new:
                result = await repository.append_transcript(
                    user_id="test-user",
                    session_id="test-session",
                    messages=messages,
                )

                assert len(result) == 2
                assert mock_new.call_count == 2

                for mock_msg in mock_messages:
                    mock_msg.save.assert_called_once()

    def test_estimate_token_count(self, repository: ChatHistoryRepository) -> None:
        """Test token count estimation."""
        result = repository.estimate_token_count("test message with some content")

        assert result > 0
        assert isinstance(result, int)

    def test_estimate_token_count_empty(
        self, repository: ChatHistoryRepository
    ) -> None:
        """Test token count estimation for empty string."""
        result = repository.estimate_token_count("")

        assert result == 0

    def test_estimate_token_count_heuristic(
        self, repository: ChatHistoryRepository
    ) -> None:
        """Test token count estimation heuristic."""
        text = "a" * 100
        result = repository.estimate_token_count(text)

        assert result == max(1, 100 // 4)

    def test_to_records(self, repository: ChatHistoryRepository) -> None:
        """Test converting messages to records."""
        messages = []
        for i in range(3):
            msg = MagicMock(spec=ChatSessionMessage)
            msg.role = "user" if i % 2 == 0 else "assistant"
            msg.content = f"message {i}"
            msg.created_at = datetime.now(timezone.utc)
            messages.append(msg)

        records = repository.to_records(messages)

        assert len(records) == 3
        for i, record in enumerate(records):
            assert isinstance(record, ChatMessageRecord)
            assert record.content == f"message {i}"

    def test_to_records_empty(self, repository: ChatHistoryRepository) -> None:
        """Test converting empty list to records."""
        records = repository.to_records([])

        assert records == []


class TestHistoryWindow:
    """Tests for HistoryWindow dataclass."""

    def test_history_window_creation(self) -> None:
        """Test creating a HistoryWindow."""
        messages = [MagicMock(spec=ChatSessionMessage)]
        window = HistoryWindow(
            messages=messages,
            truncated=True,
            token_estimate=100,
        )

        assert window.messages == messages
        assert window.truncated is True
        assert window.token_estimate == 100


class TestChatMessageRecord:
    """Tests for ChatMessageRecord dataclass."""

    def test_chat_message_record_creation(self) -> None:
        """Test creating a ChatMessageRecord."""
        created_at = datetime.now(timezone.utc)
        record = ChatMessageRecord(
            role="user",
            content="test message",
            created_at=created_at,
        )

        assert record.role == "user"
        assert record.content == "test message"
        assert record.created_at == created_at
