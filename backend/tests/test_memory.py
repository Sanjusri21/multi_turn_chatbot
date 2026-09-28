import pytest
from app.services.memory_service import MemoryService
from app.services.auth_service import AuthService
from app.schemas.auth_schema import UserSignupRequest

def test_memory_crud_and_user_isolation(test_db, test_user):
    mem_service = MemoryService(test_db)

    # 1. Create for test_user
    mem = mem_service.create_memory(user_id=test_user.id, key="name", value="Sanju", category="identity")
    assert mem.id is not None
    assert mem.key == "name"
    assert mem.value == "Sanju"
    assert mem.category == "identity"

    # 2. Retrieve
    mems = mem_service.list_all_memories(user_id=test_user.id)
    assert len(mems) == 1
    assert mems[0].key == "name"

    # 3. Another user should NOT see test_user's memories
    auth_service = AuthService(test_db)
    user2 = auth_service.signup(UserSignupRequest(
        name="Alice",
        email="alice@example.com",
        password="AlicePassword123!"
    )).user

    user2_mems = mem_service.list_all_memories(user_id=user2.id)
    assert len(user2_mems) == 0

    # User 2 creates their own memory with same key "name"
    mem_u2 = mem_service.create_memory(user_id=user2.id, key="name", value="Alice", category="identity")
    assert mem_u2.value == "Alice"

    # Verify test_user still has "Sanju"
    assert mem_service.list_all_memories(user_id=test_user.id)[0].value == "Sanju"

    # 4. Update
    updated = mem_service.update_memory(mem.id, user_id=test_user.id, value="Sanju V", category="identity")
    assert updated is not None
    assert updated.value == "Sanju V"

    # 5. Delete single
    deleted = mem_service.delete_memory(mem.id, user_id=test_user.id)
    assert deleted is True
    assert len(mem_service.list_all_memories(user_id=test_user.id)) == 0

def test_clear_all_memories(test_db, test_user):
    mem_service = MemoryService(test_db)
    mem_service.create_memory(test_user.id, "major", "AI & Data Science", "education")
    mem_service.create_memory(test_user.id, "hobby", "Robotics", "interest")
    assert len(mem_service.list_all_memories(test_user.id)) == 2

    count = mem_service.clear_all_memories(test_user.id)
    assert count == 2
    assert len(mem_service.list_all_memories(test_user.id)) == 0

def test_memory_extraction(test_db, test_user, mock_llm_service):
    mem_service = MemoryService(test_db, llm_service=mock_llm_service)
    user_msg = "My name is Sanju and I am studying AI & Data Science"
    assistant_reply = "Nice to meet you, Sanju!"

    saved = mem_service.extract_and_store_memories(test_user.id, user_msg, assistant_reply)
    assert len(saved) >= 1

    keys = [m.key for m in mem_service.list_all_memories(test_user.id)]
    assert "name" in keys
