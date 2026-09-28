import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.core.security import create_access_token

@pytest.fixture
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers(test_user):
    token = create_access_token({"sub": test_user.id, "email": test_user.email})
    return {"Authorization": f"Bearer {token}"}

def test_api_stream_chat_endpoint(client, auth_headers):
    # Test POST /api/chat/stream via HTTP TestClient
    response = client.post(
        "/api/chat/stream",
        json={"message": "Explain Python"},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    lines = response.text.split("\n\n")
    events = []
    for line in lines:
        if line.startswith("data: "):
            events.append(json.loads(line[6:].strip()))

    assert any(e.get("type") == "init" for e in events)
    assert any(e.get("type") == "chunk" for e in events)
    assert any(e.get("type") == "done" for e in events)

def test_api_regenerate_endpoint(client, auth_headers):
    # First send a message
    chat_resp = client.post(
        "/api/chat",
        json={"message": "What is Python?"},
        headers=auth_headers
    )
    assert chat_resp.status_code == 200
    data = chat_resp.json()
    conv_id = data["conversation_id"]
    asst_msg_id = data["assistant_message"]["id"]

    # Now call regenerate
    regen_resp = client.post(
        "/api/chat/regenerate",
        json={"conversation_id": conv_id, "message_id": asst_msg_id},
        headers=auth_headers
    )
    assert regen_resp.status_code == 200
    regen_data = regen_resp.json()
    assert regen_data["assistant_message"]["id"] == asst_msg_id
    assert regen_data["conversation_id"] == conv_id

def test_api_feedback_endpoint(client, auth_headers):
    # Send message first
    chat_resp = client.post(
        "/api/chat",
        json={"message": "Give me a Python example"},
        headers=auth_headers
    )
    asst_msg_id = chat_resp.json()["assistant_message"]["id"]

    # Submit feedback like
    fb_resp = client.post(
        "/api/chat/feedback",
        json={"message_id": asst_msg_id, "feedback": "like"},
        headers=auth_headers
    )
    assert fb_resp.status_code == 200
    assert fb_resp.json()["feedback"] == "like"
    assert fb_resp.json()["message"] == "Thanks for your feedback."

def test_api_debug_context_endpoint(client, auth_headers):
    resp = client.get("/api/chat/debug-context", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "llm_provider" in data
    assert "model_name" in data
    assert "system_prompt_loaded" in data
    assert "final_context" in data

def test_api_conversation_search_endpoint(client, auth_headers):
    # Create conversation
    client.post(
        "/api/chat",
        json={"message": "My name is Sanju and I am learning Python."},
        headers=auth_headers
    )

    # Search endpoint
    search_resp = client.get("/api/conversations/search?q=Python", headers=auth_headers)
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert len(results) >= 1
