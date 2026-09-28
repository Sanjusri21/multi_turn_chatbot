import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.services.llm_service import (
    GeminiLLMProvider,
    LLMProviderError,
    LLMQuotaExhaustedError,
    LLMServiceUnavailableError,
    ConfigurationError
)
from app.services.chat_service import ChatService
from app.main import app

def test_gemini_429_quota_exhausted_no_retry_and_no_fallback():
    """
    Verify that when Gemini returns 429 RESOURCE_EXHAUSTED (or GenerateRequestsPerDayPerProject):
    1. LLMQuotaExhaustedError is raised immediately.
    2. No retry is attempted (called exactly once).
    3. No fallback models (gemini-2.5-flash-lite, etc.) are called.
    """
    provider = GeminiLLMProvider(api_key="mock-key", model_name="gemini-2.5-flash")

    # Simulate google.genai ClientError with 429 code and quota message
    mock_error = Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for quota metric 'GenerateRequestsPerDayPerProject-FreeTier' and limit 'quotaValue: 20'")
    mock_error.code = 429

    with patch.object(provider, "_call_generate", side_effect=mock_error) as mock_call:
        with pytest.raises(LLMQuotaExhaustedError) as exc_info:
            provider.generate(messages=[{"role": "user", "content": "Hello"}])

        assert "Gemini API quota has been exhausted" in str(exc_info.value)
        # CRITICAL: Called exactly once. Never retried, never switched models.
        assert mock_call.call_count == 1
        assert mock_call.call_args[1]["model"] == "gemini-2.5-flash"

def test_gemini_429_quota_exhausted_streaming_no_retry():
    """
    Verify streaming also immediately raises LLMQuotaExhaustedError without retries or model switches.
    """
    provider = GeminiLLMProvider(api_key="mock-key", model_name="gemini-2.5-flash")

    mock_error = Exception("RESOURCE_EXHAUSTED: Quota exceeded")
    mock_error.status_code = 429

    with patch.object(provider, "_call_generate_stream", side_effect=mock_error) as mock_call:
        with pytest.raises(LLMQuotaExhaustedError) as exc_info:
            list(provider.generate_stream(messages=[{"role": "user", "content": "Hello"}]))

        assert "Gemini API quota has been exhausted" in str(exc_info.value)
        assert mock_call.call_count == 1
        assert mock_call.call_args[1]["model"] == "gemini-2.5-flash"

def test_gemini_503_transient_error_controlled_retry_success():
    """
    Verify that a 503 / high demand error performs at most 1 controlled retry and recovers if the 2nd attempt succeeds.
    """
    provider = GeminiLLMProvider(api_key="mock-key", model_name="gemini-2.5-flash")

    mock_error = Exception("503 The model is overloaded. Please try again later.")
    mock_error.code = 503

    # Attempt 1: 503 error, Attempt 2: success
    with patch.object(provider, "_call_generate", side_effect=[mock_error, "Hello, recovered!"]) as mock_call:
        with patch("time.sleep") as mock_sleep:
            result = provider.generate(messages=[{"role": "user", "content": "Hello"}])

            assert result == "Hello, recovered!"
            assert mock_call.call_count == 2
            mock_sleep.assert_called_once_with(1.5)

def test_gemini_503_transient_error_exhausted_raises_service_unavailable():
    """
    Verify that if 503 errors persist past the controlled retry, LLMServiceUnavailableError is raised.
    """
    provider = GeminiLLMProvider(api_key="mock-key", model_name="gemini-2.5-flash")

    mock_error = Exception("503 Service Unavailable")
    mock_error.code = 503

    with patch.object(provider, "_call_generate", side_effect=mock_error):
        with patch("time.sleep"):
            with pytest.raises(LLMServiceUnavailableError) as exc_info:
                provider.generate(messages=[{"role": "user", "content": "Hello"}])

            assert "temporarily unavailable due to high demand" in str(exc_info.value)

def test_gemini_success_normal_response():
    """
    Verify normal successful response passes cleanly with 1 call.
    """
    provider = GeminiLLMProvider(api_key="mock-key", model_name="gemini-2.5-flash")

    with patch.object(provider, "_call_generate", return_value="Normal Zara response") as mock_call:
        result = provider.generate(messages=[{"role": "user", "content": "Hello"}])
        assert result == "Normal Zara response"
        assert mock_call.call_count == 1

def test_gemini_unexpected_exception_raises_llm_provider_error():
    """
    Verify unexpected runtime exception raises standard LLMProviderError.
    """
    provider = GeminiLLMProvider(api_key="mock-key", model_name="gemini-2.5-flash")

    with patch.object(provider, "_call_generate", side_effect=ValueError("Unexpected parsing bug")):
        with pytest.raises(LLMProviderError) as exc_info:
            provider.generate(messages=[{"role": "user", "content": "Hello"}])

        assert "Zara couldn't reach the AI service" in str(exc_info.value)

def test_gemini_auth_error_raises_configuration_error():
    """
    Verify 401 / API_KEY_INVALID raises ConfigurationError immediately without retry.
    """
    provider = GeminiLLMProvider(api_key="invalid-key", model_name="gemini-2.5-flash")

    mock_error = Exception("401 API_KEY_INVALID: User not authorized")
    mock_error.code = 401

    with patch.object(provider, "_call_generate", side_effect=mock_error) as mock_call:
        with pytest.raises(ConfigurationError) as exc_info:
            provider.generate(messages=[{"role": "user", "content": "Hello"}])

        assert "authentication failed" in str(exc_info.value)
        assert mock_call.call_count == 1

@pytest.fixture
def client(test_db):
    from app.core.database import get_db
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
    from app.core.security import create_access_token
    token = create_access_token({"sub": test_user.id, "email": test_user.email})
    return {"Authorization": f"Bearer {token}"}

def test_chat_endpoint_returns_429_on_quota_exhaustion(client, auth_headers):
    """
    Verify POST /api/chat returns HTTP 429 when LLM quota is exhausted.
    """
    with patch.object(
        ChatService,
        "process_chat_message",
        side_effect=LLMQuotaExhaustedError("Zara is temporarily unavailable because the Gemini API quota has been exhausted. Please try again after the quota resets.")
    ):
        response = client.post(
            "/api/chat",
            json={"message": "Hello Zara"},
            headers=auth_headers
        )

        assert response.status_code == 429
        assert "Gemini API quota has been exhausted" in response.json()["detail"]

def test_chat_endpoint_returns_503_on_service_unavailable(client, auth_headers):
    """
    Verify POST /api/chat returns HTTP 503 when service is overloaded.
    """
    with patch.object(
        ChatService,
        "process_chat_message",
        side_effect=LLMServiceUnavailableError("Zara is temporarily unavailable due to high demand on the AI service. Please try again in a moment.")
    ):
        response = client.post(
            "/api/chat",
            json={"message": "Hello Zara"},
            headers=auth_headers
        )

        assert response.status_code == 503
        assert "high demand" in response.json()["detail"]

def test_streaming_emits_429_quota_event(test_db, test_user):
    """
    Verify process_chat_message_stream yields error event with code 429 when quota is exhausted.
    """
    from app.models.conversation import Conversation
    import uuid
    import json

    conv = Conversation(id=str(uuid.uuid4()), user_id=test_user.id, title="Test Thread")
    test_db.add(conv)
    test_db.commit()

    chat_service = ChatService(test_db)

    with patch.object(
        chat_service.llm_service,
        "generate_response_stream",
        side_effect=LLMQuotaExhaustedError("Zara is temporarily unavailable because the Gemini API quota has been exhausted. Please try again after the quota resets.")
    ):
        events = list(chat_service.process_chat_message_stream(
            user_id=test_user.id,
            message="Explain quantum computing",
            conversation_id=conv.id
        ))

        # Check that error event with code 429 was yielded
        error_events = []
        for ev in events:
            if ev.startswith("data: "):
                data = json.loads(ev[6:].strip())
                if data.get("type") == "error":
                    error_events.append(data)

        assert len(error_events) == 1
        assert error_events[0]["code"] == 429
        assert error_events[0]["error_type"] == "quota_exhausted"
        assert "Gemini API quota has been exhausted" in error_events[0]["message"]

