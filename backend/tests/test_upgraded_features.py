import pytest
import json
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.context_service import ContextService
from app.services.memory_service import MemoryService
from app.repositories.settings_repository import SettingsRepository
from app.repositories.feedback_repository import FeedbackRepository

def test_conversation_search(test_db, test_user, mock_llm_service):
    conv_service = ConversationService(test_db)
    chat_service = ChatService(test_db, llm_service=mock_llm_service)

    # Thread 1: Python Decorators
    conv1 = conv_service.create_conversation(user_id=test_user.id, title="Python Decorators")
    chat_service.process_chat_message(
        user_id=test_user.id,
        message="Can you explain how decorators work?",
        conversation_id=conv1.id
    )

    # Thread 2: FastAPI Project
    conv2 = conv_service.create_conversation(user_id=test_user.id, title="FastAPI Web Service")
    chat_service.process_chat_message(
        user_id=test_user.id,
        message="Building endpoints with Pydantic",
        conversation_id=conv2.id
    )

    # Search for "Decorators" (by title)
    results = conv_service.search_conversations(user_id=test_user.id, query="Decorators")
    assert any(c.id == conv1.id for c in results)

    # Search for "Pydantic" (by message content)
    results_msg = conv_service.search_conversations(user_id=test_user.id, query="Pydantic")
    assert any(c.id == conv2.id for c in results_msg)

    # Isolation: Another user cannot see these results
    results_other = conv_service.search_conversations(user_id="another-user-id", query="Decorators")
    assert len(results_other) == 0

def test_regenerate_response(test_db, test_user, mock_llm_service):
    chat_service = ChatService(test_db, llm_service=mock_llm_service)

    # User sends a prompt
    resp = chat_service.process_chat_message(
        user_id=test_user.id,
        message="What is machine learning?"
    )
    original_reply_id = resp.assistant_message.id
    original_content = resp.assistant_message.content

    # Regenerate response
    regen_resp = chat_service.regenerate_response(
        user_id=test_user.id,
        conversation_id=resp.conversation_id,
        message_id=original_reply_id
    )

    # Message ID is preserved in place without duplicate user messages
    assert regen_resp.assistant_message.id == original_reply_id
    assert regen_resp.assistant_message.content is not None
    assert regen_resp.user_message.content == "What is machine learning?"

    # Check conversation message count remains exactly 2 (1 user + 1 assistant)
    from app.repositories.message_repository import MessageRepository
    msg_repo = MessageRepository(test_db)
    msgs = msg_repo.list_by_conversation(resp.conversation_id)
    assert len(msgs) == 2

def test_message_feedback(test_db, test_user, mock_llm_service):
    chat_service = ChatService(test_db, llm_service=mock_llm_service)

    resp = chat_service.process_chat_message(
        user_id=test_user.id,
        message="Hello AI"
    )
    asst_msg_id = resp.assistant_message.id

    # Give like feedback
    res1 = chat_service.record_feedback(
        user_id=test_user.id,
        message_id=asst_msg_id,
        feedback="like"
    )
    assert res1["feedback"] == "like"
    assert res1["message"] == "Thanks for your feedback."

    # Toggle to dislike
    res2 = chat_service.record_feedback(
        user_id=test_user.id,
        message_id=asst_msg_id,
        feedback="dislike"
    )
    assert res2["feedback"] == "dislike"

    # Clear feedback
    res3 = chat_service.record_feedback(
        user_id=test_user.id,
        message_id=asst_msg_id,
        feedback=None
    )
    assert res3["feedback"] is None

def test_response_preference_in_context(test_db, test_user):
    context_service = ContextService(test_db)
    settings_repo = SettingsRepository(test_db)

    # Update style to beginner-friendly
    settings_repo.update(test_user.id, response_style="beginner-friendly")

    messages = context_service.build_llm_messages(
        conversation_id="conv-1",
        user_id=test_user.id,
        current_user_message="Explain recursion"
    )

    system_content = messages[0]["content"]
    assert "beginner-friendly" in system_content.lower()
    assert "simple language" in system_content.lower()

    # Update style to concise
    settings_repo.update(test_user.id, response_style="concise")
    messages_concise = context_service.build_llm_messages(
        conversation_id="conv-1",
        user_id=test_user.id,
        current_user_message="Explain recursion"
    )
    assert "succinctly" in messages_concise[0]["content"].lower()

def test_streaming_chat_flow(test_db, test_user, mock_llm_service):
    chat_service = ChatService(test_db, llm_service=mock_llm_service)

    generator = chat_service.process_chat_message_stream(
        user_id=test_user.id,
        message="Explain Python",
        conversation_id=None
    )

    events = []
    for item in generator:
        if item.startswith("data: "):
            payload = json.loads(item[6:].strip())
            events.append(payload)

    # Verify SSE lifecycle: init -> chunk(s) -> done
    assert any(e["type"] == "init" for e in events)
    assert any(e["type"] == "chunk" for e in events)
    done_event = next(e for e in events if e["type"] == "done")
    assert done_event is not None
    assert "assistant_message" in done_event
    assert done_event["assistant_message"]["content"] != ""

def test_memory_debugger_context(test_db, test_user):
    context_service = ContextService(test_db)
    debug_info = context_service.get_debug_context(
        conversation_id=None,
        user_id=test_user.id
    )

    assert "llm_provider" in debug_info
    assert "model_name" in debug_info
    assert "context_usage" in debug_info
    assert debug_info["system_prompt_loaded"] is True
    assert "final_context" in debug_info
    assert "user_preferences" in debug_info

def test_what_do_you_remember_about_me(test_db, test_user, mock_llm_service):
    mem_service = MemoryService(test_db, mock_llm_service)
    chat_service = ChatService(test_db, llm_service=mock_llm_service)

    # Store persistent facts
    mem_service.create_memory(user_id=test_user.id, key="name", value="Sanju", category="personal")
    mem_service.create_memory(user_id=test_user.id, key="field_of_study", value="AI and Data Science", category="education")
    mem_service.create_memory(user_id=test_user.id, key="technologies", value="Python and FastAPI", category="technology")

    # Ask in a fresh conversation
    conv_service = ConversationService(test_db)
    fresh_conv = conv_service.create_conversation(user_id=test_user.id, title="Memory Inquiry")

    resp = chat_service.process_chat_message(
        user_id=test_user.id,
        message="What do you remember about me?",
        conversation_id=fresh_conv.id
    )

    content = resp.assistant_message.content.lower()
    assert "sanju" in content
    assert "ai and data science" in content or "data science" in content

def test_memory_extraction_rejects_questions(mock_llm_service):
    # Questions and generic queries should never be extracted as user facts
    extracted1 = mock_llm_service.extract_memories("Explain Python", "Python is a language...")
    assert len(extracted1) == 0

    extracted2 = mock_llm_service.extract_memories("What is FastAPI?", "FastAPI is a framework...")
    assert len(extracted2) == 0

    extracted3 = mock_llm_service.extract_memories("Give me a Python example", "Here is an example...")
    assert len(extracted3) == 0

    # Explicit user declaration SHOULD be extracted
    extracted4 = mock_llm_service.extract_memories("My name is Sanju and I am studying AI and Data Science.", "Nice to meet you!")
    assert any(m["key"] == "name" and m["value"] == "Sanju" for m in extracted4)
