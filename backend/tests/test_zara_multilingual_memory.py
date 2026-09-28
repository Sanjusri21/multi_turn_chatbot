import pytest
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app.repositories.settings_repository import SettingsRepository
from app.models.user import User
from app.core.security import hash_password

def test_current_and_cross_conversation_memory(test_db, test_user, mock_llm_service):
    """
    TEST 1 & TEST 2:
    Conversation A: User states 'My project is SignAura.'
    Then asks 'What is my project?' -> Retrieves SignAura.
    Conversation B (New conversation): 'What is my project called?' -> Retrieves SignAura from Conversation A.
    """
    chat_service = ChatService(test_db, llm_service=mock_llm_service)
    conv_service = ConversationService(test_db)

    # 1. Conversation A
    conv_a = conv_service.create_conversation(test_user.id, "Conversation A")
    res1 = chat_service.process_chat_message(
        user_id=test_user.id,
        conversation_id=conv_a.id,
        message="My project is SignAura."
    )
    assert res1.extracted_memories is not None
    assert any(m.value == "SignAura" for m in res1.extracted_memories)

    # Same conversation follow-up
    res2 = chat_service.process_chat_message(
        user_id=test_user.id,
        conversation_id=conv_a.id,
        message="What is my project?"
    )
    assert "SignAura" in res2.assistant_message.content
    assert res2.memory_used is True

    # 2. Conversation B (Brand new conversation)
    conv_b = conv_service.create_conversation(test_user.id, "Conversation B")
    res3 = chat_service.process_chat_message(
        user_id=test_user.id,
        conversation_id=conv_b.id,
        message="What is my project called?"
    )
    assert "SignAura" in res3.assistant_message.content
    assert res3.memory_used is True

def test_multilingual_responses_tamil_hindi_english(test_db, test_user, mock_llm_service):
    """
    TEST 3, TEST 4, TEST 5:
    Tamil input -> Tamil response.
    Hindi input -> Hindi response.
    English input -> English response.
    """
    chat_service = ChatService(test_db, llm_service=mock_llm_service)
    conv_service = ConversationService(test_db)

    # Pre-seed project memory
    mem_service = MemoryService(test_db, llm_service=mock_llm_service)
    mem_service.create_memory(test_user.id, "current_project", "SignAura", "project", memory_text="User's project is SignAura")

    # TEST 3: Tamil
    conv_ta = conv_service.create_conversation(test_user.id, "Tamil Chat")
    res_ta = chat_service.process_chat_message(
        user_id=test_user.id,
        conversation_id=conv_ta.id,
        message="என்னுடைய project என்ன?"
    )
    assert res_ta.language == "ta"
    assert "SignAura" in res_ta.assistant_message.content
    assert "உங்கள்" in res_ta.assistant_message.content or "project" in res_ta.assistant_message.content

    # TEST 4: Hindi
    conv_hi = conv_service.create_conversation(test_user.id, "Hindi Chat")
    res_hi = chat_service.process_chat_message(
        user_id=test_user.id,
        conversation_id=conv_hi.id,
        message="मेरा प्रोजेक्ट क्या है?"
    )
    assert res_hi.language == "hi"
    assert "SignAura" in res_hi.assistant_message.content
    assert "प्रोजेक्ट" in res_hi.assistant_message.content

    # TEST 5: English
    conv_en = conv_service.create_conversation(test_user.id, "English Chat")
    res_en = chat_service.process_chat_message(
        user_id=test_user.id,
        conversation_id=conv_en.id,
        message="What is my project?"
    )
    assert res_en.language == "en"
    assert "SignAura" in res_en.assistant_message.content

def test_cross_language_memory(test_db, test_user, mock_llm_service):
    """
    TEST 7: Cross-language memory
    Conversation 1 (Tamil): "என்னுடைய project பெயர் SignAura."
    Conversation 2 (English): "What is my project called?" -> "Your project is SignAura."
    """
    chat_service = ChatService(test_db, llm_service=mock_llm_service)
    conv_service = ConversationService(test_db)

    conv_1 = conv_service.create_conversation(test_user.id, "Tamil Setup")
    chat_service.process_chat_message(
        user_id=test_user.id,
        conversation_id=conv_1.id,
        message="என்னுடைய project பெயர் SignAura."
    )

    conv_2 = conv_service.create_conversation(test_user.id, "English Retrieval")
    res_en = chat_service.process_chat_message(
        user_id=test_user.id,
        conversation_id=conv_2.id,
        message="What is my project called?"
    )
    assert "SignAura" in res_en.assistant_message.content
    assert res_en.memory_used is True

def test_user_memory_isolation(test_db, test_user, mock_llm_service):
    """
    TEST 8: Memory isolation
    User A's memory must NEVER appear in User B's conversation.
    """
    chat_service = ChatService(test_db, llm_service=mock_llm_service)
    conv_service = ConversationService(test_db)

    # Create User B
    user_b = User(
        email="user_b@example.com",
        name="User B",
        hashed_password=hash_password("SecretPassword123!")
    )
    test_db.add(user_b)
    test_db.commit()
    test_db.refresh(user_b)

    # User A records project SignAura
    conv_a = conv_service.create_conversation(test_user.id, "User A Chat")
    chat_service.process_chat_message(
        user_id=test_user.id,
        conversation_id=conv_a.id,
        message="My project is SignAura."
    )

    # User B asks about project in a new conversation
    conv_b = conv_service.create_conversation(user_b.id, "User B Chat")
    res_b = chat_service.process_chat_message(
        user_id=user_b.id,
        conversation_id=conv_b.id,
        message="What is my project called?"
    )

    # User B should NOT have User A's project
    mem_service = MemoryService(test_db, llm_service=mock_llm_service)
    user_b_mems = mem_service.list_all_memories(user_b.id)
    assert not any("SignAura" in m.value for m in user_b_mems)

def test_memory_update_deduplication(test_db, test_user, mock_llm_service):
    """
    Memory update test:
    When user updates their project to 'Alina', existing memory is updated
    rather than duplicate keys accumulating.
    """
    chat_service = ChatService(test_db, llm_service=mock_llm_service)
    conv_service = ConversationService(test_db)
    mem_service = MemoryService(test_db, llm_service=mock_llm_service)

    conv_1 = conv_service.create_conversation(test_user.id, "Chat 1")
    chat_service.process_chat_message(
        user_id=test_user.id,
        conversation_id=conv_1.id,
        message="My project is called SignAura."
    )

    # Update project name in a subsequent message
    chat_service.process_chat_message(
        user_id=test_user.id,
        conversation_id=conv_1.id,
        message="My project is now called Alina."
    )

    all_mems = mem_service.list_all_memories(test_user.id)
    proj_mems = [m for m in all_mems if m.key == "current_project"]
    assert len(proj_mems) == 1
    assert proj_mems[0].value == "Alina"

    # In a brand new conversation:
    conv_2 = conv_service.create_conversation(test_user.id, "Chat 2")
    res = chat_service.process_chat_message(
        user_id=test_user.id,
        conversation_id=conv_2.id,
        message="What is my project?"
    )
    assert "Alina" in res.assistant_message.content

def test_enable_memory_toggle_off(test_db, test_user, mock_llm_service):
    """
    TEST 7: Turn Enable memory OFF.
    Ask the same question in a new conversation.
    Expected: Persistent memory is not retrieved.
    """
    chat_service = ChatService(test_db, llm_service=mock_llm_service)
    conv_service = ConversationService(test_db)
    mem_service = MemoryService(test_db, llm_service=mock_llm_service)
    settings_repo = SettingsRepository(test_db)

    # 1. User records a memory
    conv_1 = conv_service.create_conversation(test_user.id, "Initial Chat")
    chat_service.process_chat_message(
        user_id=test_user.id,
        conversation_id=conv_1.id,
        message="My project is SignAura."
    )
    assert any(m.value == "SignAura" for m in mem_service.list_all_memories(test_user.id))

    # 2. Turn memory_enabled OFF
    settings_repo.update(test_user.id, memory_enabled=False)

    # 3. Create a brand new conversation and ask
    conv_2 = conv_service.create_conversation(test_user.id, "Chat with Memory Disabled")
    res = chat_service.process_chat_message(
        user_id=test_user.id,
        conversation_id=conv_2.id,
        message="What is my project called?"
    )

    # Memory retrieval must be suppressed
    assert res.memory_used is False
    assert "SignAura" not in res.assistant_message.content

def test_auto_save_memory_toggle_off(test_db, test_user, mock_llm_service):
    """
    TEST 8: Turn Automatically save useful info OFF.
    Say: 'My new project is called Alina.'
    Expected: It should NOT automatically create a memory.
    """
    chat_service = ChatService(test_db, llm_service=mock_llm_service)
    conv_service = ConversationService(test_db)
    mem_service = MemoryService(test_db, llm_service=mock_llm_service)
    settings_repo = SettingsRepository(test_db)

    # Clear memories first
    mem_service.clear_all_memories(test_user.id)

    # Turn auto_save_memory OFF
    settings_repo.update(test_user.id, auto_save_memory=False)

    conv = conv_service.create_conversation(test_user.id, "Auto Save Disabled Chat")
    chat_service.process_chat_message(
        user_id=test_user.id,
        conversation_id=conv.id,
        message="My new project is called Alina."
    )

    # No memory should have been created
    user_mems = mem_service.list_all_memories(test_user.id)
    assert len(user_mems) == 0

def test_manual_add_memory_persistence(test_db, test_user, mock_llm_service):
    """
    TEST 9: Use + Add Memory.
    Add: 'My project is Alina.'
    Refresh / re-query: Memory remains.
    """
    mem_service = MemoryService(test_db, llm_service=mock_llm_service)

    # Manually add memory
    saved = mem_service.save_memory(
        user_id=test_user.id,
        memory={
            "key": "current_project",
            "value": "Alina",
            "category": "project",
            "memory_text": "User's project is Alina.",
            "importance": "high"
        }
    )
    assert saved.id is not None

    # Simulate refresh / re-querying SQLite
    mems = mem_service.list_all_memories(test_user.id)
    assert any(m.key == "current_project" and m.value == "Alina" for m in mems)

def test_voice_endpoints(test_db, test_user):
    """
    Tests POST /api/voice/speak and POST /api/voice/transcribe.
    """
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token
    from app.core.database import get_db

    # Override get_db to use test_db
    app.dependency_overrides[get_db] = lambda: test_db
    client = TestClient(app)

    token = create_access_token({"sub": test_user.id, "email": test_user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Test speak endpoint
    res_speak = client.post(
        "/api/voice/speak",
        json={"text": "Hello, I am Zara.", "language": "en"},
        headers=headers
    )
    assert res_speak.status_code == 200
    data_speak = res_speak.json()
    assert data_speak["language"] == "en"
    assert data_speak["ready"] is True

    # Test transcribe endpoint
    res_transcribe = client.post(
        "/api/voice/transcribe",
        data={"language": "ta"},
        headers=headers
    )
    assert res_transcribe.status_code == 200
    data_transcribe = res_transcribe.json()
    assert data_transcribe["language"] == "ta"
    app.dependency_overrides.clear()

