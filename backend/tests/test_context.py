import pytest
from app.services.conversation_service import ConversationService
from app.services.context_service import ContextService
from app.services.memory_service import MemoryService
from app.services.summarization_service import SummarizationService
from app.repositories.message_repository import MessageRepository
from app.core.config import settings

def test_context_window_limiting(test_db, test_user):
    conv_service = ConversationService(test_db)
    msg_repo = MessageRepository(test_db)
    context_service = ContextService(test_db)

    conv = conv_service.create_conversation(test_user.id, "Context Limit Test")

    # Add messages exceeding MAX_CONTEXT_MESSAGES to test truncation
    for i in range(settings.MAX_CONTEXT_MESSAGES + 6):
        role = "user" if i % 2 == 0 else "assistant"
        msg_repo.create(conv.id, role, f"Message {i}")

    llm_msgs = context_service.build_llm_messages(conv.id, test_user.id, "Current new message")

    # Expected: 1 system message + at most MAX_CONTEXT_MESSAGES history messages + 1 current user message
    non_system_msgs = [m for m in llm_msgs if m["role"] != "system"]

    assert len(non_system_msgs) == settings.MAX_CONTEXT_MESSAGES + 1
    assert non_system_msgs[-1]["content"] == "Current new message"

def test_memory_and_summary_injection_in_context(test_db, test_user, mock_llm_service):
    conv_service = ConversationService(test_db)
    mem_service = MemoryService(test_db)
    msg_repo = MessageRepository(test_db)
    context_service = ContextService(test_db)
    summary_service = SummarizationService(test_db, llm_service=mock_llm_service)

    conv = conv_service.create_conversation(test_user.id, "Summary & Memory Test")
    mem_service.create_memory(test_user.id, "name", "Sanju", "identity")

    # Populate messages exceeding threshold and context window so summarization triggers
    num_msgs = max(settings.SUMMARY_TRIGGER_THRESHOLD, settings.MAX_CONTEXT_MESSAGES) + 6
    for i in range(num_msgs):
        role = "user" if i % 2 == 0 else "assistant"
        msg_repo.create(conv.id, role, f"Turn {i} content")

    summary_service.check_and_summarize(conv.id, user_id=test_user.id)

    llm_msgs = context_service.build_llm_messages(conv.id, test_user.id, "Next question")
    system_prompt = next(m["content"] for m in llm_msgs if m["role"] == "system")

    assert "Sanju" in system_prompt
    assert "[Identity]" in system_prompt or "identity" in system_prompt.lower()
    assert "PREVIOUS CONVERSATION SUMMARY" in system_prompt
