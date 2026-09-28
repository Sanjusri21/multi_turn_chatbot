import json
import pytest
from app.services.intent_service import IntentService
from app.services.source_service import SourceService
from app.services.web_search_service import WebSearchService, SearchResult, MockSearchProvider
from app.services.realtime_service import RealtimeService
from app.services.chat_service import ChatService
from app.schemas.chat_schema import ChatRequest

# Test 1: Normal question does not trigger web search
def test_normal_question_no_web_search():
    intent_service = IntentService()
    questions = [
        "What is Python?",
        "Explain CNN.",
        "How does a neural network work?",
        "Define polymorphism in OOP.",
        "Hello Zara",
        "Hi, how are you today?"
    ]
    for q in questions:
        intent = intent_service.detect_intent(q)
        assert intent.requires_realtime is False, f"Query '{q}' should not trigger web search"

# Test 2: Current-information question triggers web search
def test_current_information_triggers_web_search():
    intent_service = IntentService()
    freshness_queries = [
        "Who is the current Chief Minister of Tamil Nadu?",
        "What are today's headlines?",
        "What is the latest version of Python?",
        "What's the weather today?",
        "Latest OpenAI model?",
        "Who is the current Prime Minister of the UK?",
        "Who is the CM of Tamil Nadu?"
    ]
    for q in freshness_queries:
        intent = intent_service.detect_intent(q)
        assert intent.requires_realtime is True, f"Query '{q}' should trigger web search"

# Test 3: Search failure is handled gracefully
def test_search_failure_handled_gracefully(test_db, test_user):
    class FailingSearchProvider(MockSearchProvider):
        async def search(self, query: str, max_results: int = 5):
            raise ConnectionError("DNS failure / search engine down")

    chat_service = ChatService(test_db)
    chat_service.search_service = WebSearchService(provider=FailingSearchProvider())
    chat_service.realtime_service = RealtimeService(chat_service.search_service)

    response = chat_service.process_chat_message(
        user_id=test_user.id,
        message="Who is the current Chief Minister of Tamil Nadu?"
    )

    assert response is not None
    assert response.response is not None
    assert "couldn't retrieve current web information" in response.response.lower() or "outdated" in response.response.lower()

# Test 4: Empty search results are handled without hallucinating
def test_empty_search_results_handled(test_db, test_user):
    class EmptySearchProvider(MockSearchProvider):
        async def search(self, query: str, max_results: int = 5):
            return []

    chat_service = ChatService(test_db)
    chat_service.search_service = WebSearchService(provider=EmptySearchProvider())
    chat_service.realtime_service = RealtimeService(chat_service.search_service)

    response = chat_service.process_chat_message(
        user_id=test_user.id,
        message="Who is the current Chief Minister of Tamil Nadu?"
    )

    assert response is not None
    assert "could not find reliable recent sources" in response.response or "outdated" in response.response or "sources" not in response.response

# Test 5: Duplicate results are removed
def test_duplicate_results_removed():
    raw_results = [
        SearchResult(
            title="Chief Minister Profile",
            url="https://assembly.tn.gov.in/cm.php?utm_source=feed",
            snippet="Official profile of Chief Minister M. K. Stalin.",
            source_name="assembly.tn.gov.in"
        ),
        SearchResult(
            title="Chief Minister Profile",
            url="https://assembly.tn.gov.in/cm.php?utm_medium=email",
            snippet="Duplicate URL with tracking parameters.",
            source_name="assembly.tn.gov.in"
        ),
        SearchResult(
            title="Chief Minister Profile",
            url="https://assembly.tn.gov.in/cm.php",
            snippet="Exact duplicate URL.",
            source_name="assembly.tn.gov.in"
        ),
        SearchResult(
            title="Tamil Nadu Government Portal",
            url="https://www.tn.gov.in/ministers",
            snippet="Council of Ministers under Chief Minister M. K. Stalin.",
            source_name="tn.gov.in"
        )
    ]
    normalized = SourceService.normalize_sources(raw_results, max_results=5)
    assert len(normalized) == 2, f"Expected 2 unique sources, got {len(normalized)}"
    urls = [s.url for s in normalized]
    assert "https://assembly.tn.gov.in/cm.php" in urls
    assert "https://www.tn.gov.in/ministers" in urls

# Test 6: Source URLs are preserved
def test_source_urls_preserved():
    raw_results = [
        SearchResult(
            title="Tamil Nadu Assembly",
            url="https://assembly.tn.gov.in/members",
            snippet="Legislative Assembly information.",
            source_name="assembly.tn.gov.in"
        )
    ]
    normalized = SourceService.normalize_sources(raw_results)
    assert len(normalized) == 1
    assert normalized[0].url == "https://assembly.tn.gov.in/members"

# Test 7: API keys are never returned
def test_api_keys_never_returned(test_db, test_user):
    chat_service = ChatService(test_db)
    response = chat_service.process_chat_message(
        user_id=test_user.id,
        message="Who is the current Chief Minister of Tamil Nadu?"
    )
    resp_dict = response.model_dump(mode="json")
    resp_str = json.dumps(resp_dict).lower()
    assert "api_key" not in resp_str
    assert "secret" not in resp_str
    assert "gemini_api_key" not in resp_str
    assert "web_search_api_key" not in resp_str

# Test 8: Memory remains separate from web results
def test_memory_remains_separate_from_web_results(test_db, test_user):
    chat_service = ChatService(test_db)
    # Asking a real-time question should not pollute persistent user memory
    res_realtime = chat_service.process_chat_message(
        user_id=test_user.id,
        message="Who is the current Chief Minister of Tamil Nadu?"
    )
    user_memories = chat_service.mem_service.memory_repo.list_by_user(test_user.id)
    # None of the memories should contain "Stalin" or government facts
    for mem in user_memories:
        assert "stalin" not in mem.value.lower()
        assert "chief minister" not in mem.key.lower()

# Test 9: Conversation history still works
def test_conversation_history_works(test_db, test_user):
    chat_service = ChatService(test_db)
    # Turn 1
    res1 = chat_service.process_chat_message(
        user_id=test_user.id,
        message="Hello Zara, my name is Sanju."
    )
    conv_id = res1.conversation_id
    assert conv_id is not None

    # Turn 2
    res2 = chat_service.process_chat_message(
        user_id=test_user.id,
        message="What is Python?",
        conversation_id=conv_id
    )
    assert res2.conversation_id == conv_id

    # Turn 3: Real-time query in same conversation
    res3 = chat_service.process_chat_message(
        user_id=test_user.id,
        message="Who is the current Chief Minister of Tamil Nadu?",
        conversation_id=conv_id
    )
    assert res3.conversation_id == conv_id
    assert res3.is_realtime is True

    # Verify message thread length
    messages = chat_service.msg_repo.list_by_conversation(conv_id)
    assert len(messages) >= 6

# Test 10: Streaming still works (yields status and done events)
def test_streaming_with_status_events(test_db, test_user):
    chat_service = ChatService(test_db)
    stream_gen = chat_service.process_chat_message_stream(
        user_id=test_user.id,
        message="Who is the current Chief Minister of Tamil Nadu?"
    )

    events = []
    for sse_block in stream_gen:
        for line in sse_block.strip().split("\n"):
            if line.startswith("data: "):
                data = json.loads(line[6:])
                events.append(data)

    event_types = [e.get("type") for e in events]
    assert "init" in event_types
    assert "status" in event_types
    assert "done" in event_types

    # Verify status stages
    status_stages = [e.get("stage") for e in events if e.get("type") == "status"]
    assert "searching" in status_stages
    assert "reading_sources" in status_stages
    assert "generating" in status_stages

    # Verify done event contains sources
    done_event = next(e for e in events if e.get("type") == "done")
    assert done_event.get("is_realtime") is True
    assert done_event.get("sources") is not None
    assert len(done_event.get("sources")) > 0

# Test 11: Tamil language response works with real-time search
def test_tamil_realtime_search(test_db, test_user):
    chat_service = ChatService(test_db)
    res = chat_service.process_chat_message(
        user_id=test_user.id,
        message="தமிழ்நாட்டின் தற்போதைய முதலமைச்சர் யார்?",
        language="ta"
    )
    assert res.is_realtime is True
    assert res.language == "ta"
    assert res.sources is not None
    assert len(res.sources) > 0
    # Response contains Tamil text
    assert any('\u0b80' <= c <= '\u0bff' for c in res.response)

# Test 12: Hindi language response works with real-time search
def test_hindi_realtime_search(test_db, test_user):
    chat_service = ChatService(test_db)
    res = chat_service.process_chat_message(
        user_id=test_user.id,
        message="तमिलनाडु के वर्तमान मुख्यमंत्री कौन हैं?",
        language="hi"
    )
    assert res.is_realtime is True
    assert res.language == "hi"
    assert res.sources is not None
    assert len(res.sources) > 0
    # Response contains Hindi Devanagari text
    assert any('\u0900' <= c <= '\u097f' for c in res.response)

# Test 13: English language response works with real-time search
def test_english_realtime_search(test_db, test_user):
    chat_service = ChatService(test_db)
    res = chat_service.process_chat_message(
        user_id=test_user.id,
        message="Who is the current Chief Minister of Tamil Nadu?",
        language="en"
    )
    assert res.is_realtime is True
    assert res.language == "en"
    assert res.sources is not None
    assert len(res.sources) > 0
    assert "Stalin" in res.response or "M. K. Stalin" in res.response
    assert "Sources:" in res.response or "**Sources:**" in res.response
