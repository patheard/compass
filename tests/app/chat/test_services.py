"""Unit tests for Chat services."""

from app.chat.services import ChatStreamingService


class TestChatStreamingService:
    """Tests for ChatStreamingService class."""

    def test_chat_streaming_service_initialization(self) -> None:
        """Test ChatStreamingService initialization."""
        service = ChatStreamingService()

        assert service is not None
        assert hasattr(service, "DEFAULT_SYSTEM_PROMPT")

    def test_default_system_prompt_exists(self) -> None:
        """Test that default system prompt is set."""
        service = ChatStreamingService()

        assert len(service.DEFAULT_SYSTEM_PROMPT) > 0
        assert "security" in service.DEFAULT_SYSTEM_PROMPT.lower()

    def test_vector_context_prompt_exists(self) -> None:
        """Test that vector context prompt is set."""
        service = ChatStreamingService()

        assert len(service.VECTOR_CONTEXT_PROMPT) > 0
