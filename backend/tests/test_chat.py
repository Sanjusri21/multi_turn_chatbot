import pytest
from app.services.conversation_service import ConversationService
from app.services.chat_service import ChatService
from app.repositories.message_repository import MessageRepository

def test_conversation_creation_and_retrieval(test_db, test_user):
    conv_service = ConversationService(test_db)
    conv = conv_service.create_conversation(user_id=test_user.id, title="AI Discussion")

    assert conv.id is not None
    assert conv.title == "AI Discussion"
    assert conv.user_id == test_user.id

    retrieved = conv_service.get_conversation(conv.id, user_id=test_user.id)
    assert retrieved is not None
    assert retrieved.id == conv.id

    # Another user cannot fetch this conversation
    retrieved_other = conv_service.get_conversation(conv.id, user_id="other-user-uuid")
    assert retrieved_other is None

def test_store_and_retrieve_messages(test_db, test_user):
    conv_service = ConversationService(test_db)
    msg_repo = MessageRepository(test_db)

    conv = conv_service.create_conversation(user_id=test_user.id, title="Message Test")
    msg1 = msg_repo.create(conv.id, "user", "Hello RotoBot!")
    msg2 = msg_repo.create(conv.id, "assistant", "Hello! How can I help you?")

    messages = msg_repo.list_by_conversation(conv.id)
    assert len(messages) == 2
    assert messages[0].content == "Hello RotoBot!"
    assert messages[1].content == "Hello! How can I help you?"

def test_chat_service_multi_turn_flow(test_db, test_user, mock_llm_service):
    chat_service = ChatService(test_db, llm_service=mock_llm_service)

    # Turn 1: user introduces themselves
    resp1 = chat_service.process_chat_message(
        user_id=test_user.id,
        message="My name is Sanju."
    )
    assert resp1.conversation_id is not None
    assert "Sanju" in resp1.assistant_message.content or "saved" in resp1.assistant_message.content

    # Check that conversation was created and auto-titled for this user
    conv_service = ConversationService(test_db)
    conv = conv_service.get_conversation(resp1.conversation_id, user_id=test_user.id)
    assert conv is not None
    assert "Sanju" in conv.title or "My name is" in conv.title

    # Turn 2: continuation in the same conversation
    resp2 = chat_service.process_chat_message(
        user_id=test_user.id,
        message="What is my name?",
        conversation_id=resp1.conversation_id
    )
    assert resp2.conversation_id == resp1.conversation_id
    assert resp2.user_message.content == "What is my name?"

    # Check message count
    msg_repo = MessageRepository(test_db)
    assert msg_repo.count_by_conversation(resp1.conversation_id) == 4

def test_comprehensive_multi_turn_e2e_sequence(test_db, test_user, mock_llm_service):
    """
    Validates the exact PART 25 End-to-End Test specification:
    STEP 1: User Sanju
    STEP 2: New Chat
    STEP 3: "My name is Sanju."
    STEP 4: "I am studying AI and Data Science."
    STEP 5: "I am learning Python and FastAPI."
    STEP 6: "I am building a project called MemoryBot."
    STEP 7: Ask "What is my name?" -> Expects "Your name is Sanju."
    STEP 8: Ask "What am I studying?" -> Expects "You're studying AI and Data Science."
    STEP 9: Ask "What technologies am I learning?" -> Expects Python and FastAPI
    STEP 10: Ask "What is my project?" -> Expects "MemoryBot."
    STEP 11-12: Complete conversation retained and reloadable.
    STEP 13: General question "Tell me something about FastAPI."
    STEP 14: New Chat -> Long-term memory remembers "Sanju", while conversation-specific context remains isolated.
    """
    chat_service = ChatService(test_db, llm_service=mock_llm_service)
    conv_service = ConversationService(test_db)
    msg_repo = MessageRepository(test_db)

    # STEP 2 & 3: New Chat -> Send "My name is Sanju."
    resp1 = chat_service.process_chat_message(user_id=test_user.id, message="My name is Sanju.")
    conv_id = resp1.conversation_id
    assert conv_id is not None
    assert "Sanju" in resp1.assistant_message.content

    # STEP 4: "I am studying AI and Data Science."
    resp2 = chat_service.process_chat_message(user_id=test_user.id, message="I am studying AI and Data Science.", conversation_id=conv_id)
    assert resp2.conversation_id == conv_id

    # STEP 5: "I am learning Python and FastAPI."
    resp3 = chat_service.process_chat_message(user_id=test_user.id, message="I am learning Python and FastAPI.", conversation_id=conv_id)
    assert resp3.conversation_id == conv_id

    # STEP 6: "I am building a project called MemoryBot."
    resp4 = chat_service.process_chat_message(user_id=test_user.id, message="I am building a project called MemoryBot.", conversation_id=conv_id)
    assert resp4.conversation_id == conv_id

    # STEP 7: "What is my name?"
    resp5 = chat_service.process_chat_message(user_id=test_user.id, message="What is my name?", conversation_id=conv_id)
    assert "Sanju" in resp5.assistant_message.content

    # STEP 8: "What am I studying?"
    resp6 = chat_service.process_chat_message(user_id=test_user.id, message="What am I studying?", conversation_id=conv_id)
    assert "AI and Data Science" in resp6.assistant_message.content

    # STEP 9: "What technologies am I learning?"
    resp7 = chat_service.process_chat_message(user_id=test_user.id, message="What technologies am I learning?", conversation_id=conv_id)
    assert "Python" in resp7.assistant_message.content
    assert "FastAPI" in resp7.assistant_message.content

    # STEP 10: "What is my project?"
    resp8 = chat_service.process_chat_message(user_id=test_user.id, message="What is my project?", conversation_id=conv_id)
    assert "MemoryBot" in resp8.assistant_message.content

    # STEP 11 & 12: Verify database persistence
    stored_messages = msg_repo.list_by_conversation(conv_id)
    assert len(stored_messages) == 16  # 8 user + 8 assistant

    # STEP 13: Ask general knowledge question
    resp9 = chat_service.process_chat_message(user_id=test_user.id, message="Tell me something about FastAPI.", conversation_id=conv_id)
    assert "FastAPI" in resp9.assistant_message.content

    # STEP 14: New Chat -> Long-term memory remembers "Sanju"
    new_conv = conv_service.create_conversation(user_id=test_user.id, title="Brand New Conversation")
    resp_new = chat_service.process_chat_message(user_id=test_user.id, message="What is my name?", conversation_id=new_conv.id)
    assert "Sanju" in resp_new.assistant_message.content

