"""
Tests for Grok/xAI Fallback LLM Provider and LLMRouter.

Validates all 15 required scenarios:
1. Gemini success -> Grok not called.
2. Gemini 429 -> Grok called once.
3. Gemini 503 -> Grok fallback after existing controlled Gemini retry behavior.
4. Gemini timeout -> Grok fallback.
5. Grok success -> response returned.
6. Gemini 429 + Grok 429 -> clear final provider-unavailable error.
7. Both providers unavailable -> correct HTTP error.
8. Streaming Gemini success -> Grok not called.
9. Streaming Gemini fails before output -> Grok streaming begins.
10. Streaming Gemini fails after meaningful output -> no duplicate Grok response.
11. Real-time search + Gemini -> sources passed to Gemini.
12. Real-time search + Gemini failure + Grok fallback -> SAME sources passed to Grok.
13. Memory + Gemini fallback -> memory context preserved.
14. Tamil + Grok -> Tamil prompt preserved.
15. Hindi + Grok -> Hindi prompt preserved.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.services.llm_service import (
    BaseLLMProvider,
    GeminiLLMProvider,
    LLMQuotaExhaustedError,
    LLMServiceUnavailableError,
    LLMProviderError,
    LLMService,
)
from app.services.grok_llm_provider import GrokLLMProvider
from app.services.llm_router import LLMRouter
from app.services.chat_service import ChatService
from app.services.intent_service import IntentResult
from app.main import app
from app.core.database import get_db
from app.core.security import create_access_token


class DummyProvider(BaseLLMProvider):
    def __init__(self, name="dummy", responses=None, stream_chunks=None, error=None):
        self.name = name
        self.responses = responses or ["Default response"]
        self.stream_chunks = stream_chunks or ["Chunk 1", " Chunk 2"]
        self.error = error
        self.call_count = 0
        self.stream_call_count = 0
        self.last_messages = None

    def generate(self, messages, temperature=0.7, images=None, **kwargs):
        self.call_count += 1
        self.last_messages = messages
        if self.error:
            raise self.error
        return self.responses[0]

    def generate_stream(self, messages, temperature=0.7, images=None, **kwargs):
        self.stream_call_count += 1
        self.last_messages = messages
        if self.error:
            raise self.error
        for c in self.stream_chunks:
            yield c


# 1. Gemini success -> Grok not called
def test_1_gemini_success_grok_not_called():
    primary = DummyProvider(name="gemini", responses=["Gemini answer"])
    fallback = DummyProvider(name="grok", responses=["Grok answer"])
    router = LLMRouter(primary=primary, fallback=fallback)

    result = router.generate([{"role": "user", "content": "Hi"}])

    assert result == "Gemini answer"
    assert primary.call_count == 1
    assert fallback.call_count == 0
    assert router.last_provider_used == "gemini"


# 2. Gemini 429 -> Grok called once
def test_2_gemini_429_grok_called_once():
    primary = DummyProvider(
        name="gemini",
        error=LLMQuotaExhaustedError("Gemini API quota has been exhausted")
    )
    fallback = DummyProvider(name="grok", responses=["Grok recovered answer"])
    router = LLMRouter(primary=primary, fallback=fallback)

    result = router.generate([{"role": "user", "content": "Hi"}])

    assert result == "Grok recovered answer"
    assert primary.call_count == 1
    assert fallback.call_count == 1
    assert router.last_provider_used == "grok"


# 3. Gemini 503 -> Grok fallback after existing controlled Gemini retry behavior
def test_3_gemini_503_grok_fallback():
    gemini_provider = GeminiLLMProvider(api_key="mock-key", model_name="gemini-2.5-flash")
    fallback = DummyProvider(name="grok", responses=["Grok answer after 503"])
    router = LLMRouter(primary=gemini_provider, fallback=fallback)

    mock_error = Exception("503 Service Unavailable")
    mock_error.code = 503

    with patch.object(gemini_provider, "_call_generate", side_effect=mock_error) as mock_gemini_call:
        with patch("time.sleep"):
            result = router.generate([{"role": "user", "content": "Hi"}])

            assert result == "Grok answer after 503"
            # Gemini provider executed controlled retry behavior across its candidates
            assert mock_gemini_call.call_count >= 2
            assert fallback.call_count == 1
            assert router.last_provider_used == "grok"


# 4. Gemini timeout -> Grok fallback
def test_4_gemini_timeout_grok_fallback():
    primary = DummyProvider(
        name="gemini",
        error=LLMProviderError("Request timed out after 30 seconds")
    )
    fallback = DummyProvider(name="grok", responses=["Grok answer after timeout"])
    router = LLMRouter(primary=primary, fallback=fallback)

    result = router.generate([{"role": "user", "content": "Hi"}])

    assert result == "Grok answer after timeout"
    assert primary.call_count == 1
    assert fallback.call_count == 1
    assert router.last_provider_used == "grok"


# 5. Grok success -> response returned
def test_5_grok_success_response_returned():
    grok_provider = GrokLLMProvider(api_key="mock-xai-key", model_name="grok-4.1-fast")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Grok direct answer"

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response

        result = grok_provider.generate([{"role": "user", "content": "Hello"}])
        assert result == "Grok direct answer"


# 6. Gemini 429 + Grok 429 -> clear final provider-unavailable error
def test_6_gemini_429_and_grok_429_raises_quota_exhausted():
    primary = DummyProvider(
        name="gemini",
        error=LLMQuotaExhaustedError("Gemini quota exhausted")
    )
    fallback = DummyProvider(
        name="grok",
        error=LLMQuotaExhaustedError("xAI rate limit / quota exceeded")
    )
    router = LLMRouter(primary=primary, fallback=fallback)

    with pytest.raises(LLMQuotaExhaustedError) as exc_info:
        router.generate([{"role": "user", "content": "Hi"}])

    assert "quota" in str(exc_info.value).lower()
    assert primary.call_count == 1
    assert fallback.call_count == 1


# 7. Both providers unavailable -> correct HTTP error
def test_7_both_providers_unavailable_http_error(test_db, test_user):
    primary = DummyProvider(
        name="gemini",
        error=LLMServiceUnavailableError("Gemini unavailable")
    )
    fallback = DummyProvider(
        name="grok",
        error=LLMServiceUnavailableError("Grok unavailable")
    )
    router = LLMRouter(primary=primary, fallback=fallback)
    llm_service = LLMService(provider=router)
    chat_service = ChatService(db=test_db, llm_service=llm_service)

    with pytest.raises(LLMServiceUnavailableError) as exc_info:
        chat_service.process_chat_message(
            user_id=test_user.id,
            message="Hello"
        )

    assert "Both AI providers are currently unavailable" in str(exc_info.value)

    # Also verify HTTP 503 translation via FastAPI route layer
    def override_get_db():
        yield test_db

    token = create_access_token({"sub": test_user.id, "email": test_user.email})
    auth_headers = {"Authorization": f"Bearer {token}"}

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.api.chat_routes.ChatService", return_value=chat_service):
        with TestClient(app) as client:
            resp = client.post("/api/chat", json={"message": "Hello"}, headers=auth_headers)
            assert resp.status_code == 503
            assert "Both AI providers are currently unavailable" in resp.json()["detail"]
    app.dependency_overrides.clear()


# 8. Streaming Gemini success -> Grok not called
def test_8_streaming_gemini_success_grok_not_called():
    primary = DummyProvider(name="gemini", stream_chunks=["Hello", " from", " Gemini"])
    fallback = DummyProvider(name="grok", stream_chunks=["Grok chunk"])
    router = LLMRouter(primary=primary, fallback=fallback)

    chunks = list(router.generate_stream([{"role": "user", "content": "Hi"}]))

    assert "".join(chunks) == "Hello from Gemini"
    assert primary.stream_call_count == 1
    assert fallback.stream_call_count == 0
    assert router.last_provider_used == "gemini"


# 9. Streaming Gemini fails before output -> Grok streaming begins
def test_9_streaming_gemini_fails_before_output_grok_streams():
    primary = DummyProvider(
        name="gemini",
        error=LLMQuotaExhaustedError("Gemini quota exhausted")
    )
    fallback = DummyProvider(name="grok", stream_chunks=["Hello", " from", " Grok"])
    router = LLMRouter(primary=primary, fallback=fallback)

    fallback_triggered = []
    def on_fallback_cb(info):
        fallback_triggered.append(info)

    chunks = list(router.generate_stream(
        [{"role": "user", "content": "Hi"}],
        on_fallback=on_fallback_cb
    ))

    assert "".join(chunks) == "Hello from Grok"
    assert primary.stream_call_count == 1
    assert fallback.stream_call_count == 1
    assert len(fallback_triggered) == 1
    assert fallback_triggered[0]["from"] == "gemini"
    assert fallback_triggered[0]["to"] == "grok"
    assert router.last_provider_used == "grok"


# 10. Streaming Gemini fails after meaningful output -> no duplicate Grok response
def test_10_streaming_gemini_fails_after_output_no_duplicate_grok():
    class MidFailProvider(BaseLLMProvider):
        def generate(self, messages, temperature=0.7, images=None, **kwargs):
            return "ok"
        def generate_stream(self, messages, temperature=0.7, images=None, **kwargs):
            yield "Initial Gemini output"
            raise LLMServiceUnavailableError("Mid-stream connection drop")

    primary = MidFailProvider()
    fallback = DummyProvider(name="grok", stream_chunks=["Grok should not be called!"])
    router = LLMRouter(primary=primary, fallback=fallback)

    collected = []
    with pytest.raises(LLMServiceUnavailableError):
        for chunk in router.generate_stream([{"role": "user", "content": "Hi"}]):
            collected.append(chunk)

    assert collected == ["Initial Gemini output"]
    assert fallback.stream_call_count == 0


# 11. Real-time search + Gemini -> sources passed to Gemini
def test_11_realtime_search_gemini_sources_passed(test_db, test_user):
    primary = DummyProvider(name="gemini", responses=["Python latest is 3.13 according to search."])
    fallback = DummyProvider(name="grok", responses=["Grok fallback answer"])
    router = LLMRouter(primary=primary, fallback=fallback)
    llm_service = LLMService(provider=router)
    chat_service = ChatService(db=test_db, llm_service=llm_service)

    with patch.object(chat_service.intent_service, "detect_intent", return_value=IntentResult(
        intent_type="REAL_TIME",
        requires_realtime=True,
        category="general",
        search_query="What is the latest version of Python?"
    )):
        with patch.object(chat_service.realtime_service, "get_realtime_data", return_value=[
            {"title": "Python 3.13 Release", "url": "https://python.org", "snippet": "Python 3.13 is out now."}
        ]):
            resp = chat_service.process_chat_message(
                user_id=test_user.id,
                message="What is the latest version of Python?"
            )

            assert primary.call_count == 1
            assert fallback.call_count == 0
            prompt_str = str(primary.last_messages)
            assert "Python 3.13 is out now." in prompt_str
            assert "REAL-TIME INFORMATION RULE:" in prompt_str
            assert resp.sources is not None
            assert len(resp.sources) > 0


# 12. Real-time search + Gemini failure + Grok fallback -> SAME sources passed to Grok
def test_12_realtime_search_gemini_fail_grok_fallback_same_sources(test_db, test_user):
    primary = DummyProvider(
        name="gemini",
        error=LLMQuotaExhaustedError("Gemini quota exhausted")
    )
    fallback = DummyProvider(name="grok", responses=["Grok answered using same web sources."])
    router = LLMRouter(primary=primary, fallback=fallback)
    llm_service = LLMService(provider=router)
    chat_service = ChatService(db=test_db, llm_service=llm_service)

    with patch.object(chat_service.intent_service, "detect_intent", return_value=IntentResult(
        intent_type="REAL_TIME",
        requires_realtime=True,
        category="general",
        search_query="What is the latest version of Python?"
    )):
        with patch.object(chat_service.realtime_service, "get_realtime_data", return_value=[
            {"title": "Python 3.13 Release", "url": "https://python.org", "snippet": "Python 3.13 is out now."}
        ]):
            resp = chat_service.process_chat_message(
                user_id=test_user.id,
                message="What is the latest version of Python?"
            )

            assert primary.call_count == 1
            assert fallback.call_count == 1
            assert fallback.last_messages == primary.last_messages
            prompt_str = str(fallback.last_messages)
            assert "Python 3.13 is out now." in prompt_str
            assert "REAL-TIME INFORMATION RULE:" in prompt_str
            assert resp.provider == "grok"


# 13. Memory + Gemini fallback -> memory context preserved
def test_13_memory_gemini_fallback_context_preserved(test_db, test_user):
    from app.services.memory_service import MemoryService
    mem_service = MemoryService(test_db)
    mem_service.create_memory(user_id=test_user.id, key="name", value="Sanju")

    primary = DummyProvider(
        name="gemini",
        error=LLMQuotaExhaustedError("Gemini quota exhausted")
    )
    fallback = DummyProvider(name="grok", responses=["Your name is Sanju."])
    router = LLMRouter(primary=primary, fallback=fallback)
    llm_service = LLMService(provider=router)
    chat_service = ChatService(db=test_db, llm_service=llm_service)

    resp = chat_service.process_chat_message(
        user_id=test_user.id,
        message="What is my name?"
    )

    assert primary.call_count == 1
    assert fallback.call_count == 1
    prompt_str = str(fallback.last_messages)
    assert "Sanju" in prompt_str
    assert "[LONG-TERM USER MEMORY]" in prompt_str
    assert resp.provider == "grok"


# 14. Tamil + Grok -> Tamil prompt preserved
def test_14_tamil_grok_prompt_preserved(test_db, test_user):
    primary = DummyProvider(
        name="gemini",
        error=LLMQuotaExhaustedError("Gemini quota exhausted")
    )
    fallback = DummyProvider(name="grok", responses=["வணக்கம்! நான் சாரா."])
    router = LLMRouter(primary=primary, fallback=fallback)
    llm_service = LLMService(provider=router)
    chat_service = ChatService(db=test_db, llm_service=llm_service)

    resp = chat_service.process_chat_message(
        user_id=test_user.id,
        message="வணக்கம்",
        language="ta"
    )

    assert primary.call_count == 1
    assert fallback.call_count == 1
    prompt_str = str(fallback.last_messages)
    assert "Respond in Tamil. Use natural Tamil script." in prompt_str
    assert resp.provider == "grok"


# 15. Hindi + Grok -> Hindi prompt preserved
def test_15_hindi_grok_prompt_preserved(test_db, test_user):
    primary = DummyProvider(
        name="gemini",
        error=LLMQuotaExhaustedError("Gemini quota exhausted")
    )
    fallback = DummyProvider(name="grok", responses=["नमस्ते! मैं ज़ारा हूँ."])
    router = LLMRouter(primary=primary, fallback=fallback)
    llm_service = LLMService(provider=router)
    chat_service = ChatService(db=test_db, llm_service=llm_service)

    resp = chat_service.process_chat_message(
        user_id=test_user.id,
        message="नमस्ते",
        language="hi"
    )

    assert primary.call_count == 1
    assert fallback.call_count == 1
    prompt_str = str(fallback.last_messages)
    assert "Respond in Hindi. Use natural Devanagari script." in prompt_str
    assert resp.provider == "grok"
