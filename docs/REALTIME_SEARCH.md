# Zara — Real-Time Search & Retrieval Guide

This guide explains how Zara's real-time retrieval layer works, how to configure search providers and API keys, how to extend the provider system, and how to verify the integration.

---

## 1. How Real-Time Search Works

When a user asks a question, Zara follows a selective freshness pipeline:

1. **Intent Analysis**: `IntentService` inspects the query for freshness indicators (e.g., `current`, `today`, `latest`, `price`, `weather`, or political offices like `Chief Minister`, `President`, `Prime Minister`).
2. **Provider Selection**:
   - Queries matching structured domains (e.g., weather or cryptocurrency) are routed to specialized real-time providers first (`RealtimeService`).
   - General current-information questions are routed to the configured web search provider (`WebSearchService`).
3. **Execution & Streaming Status**:
   - The SSE stream pushes an immediate event: `{"stage": "searching"}` to inform the user.
   - The provider performs an asynchronous HTTP lookup.
   - Upon receiving results, the SSE stream pushes `{"stage": "reading_sources"}`.
4. **Source Processing & Normalization**:
   - Results are deduplicated, stripped of invalid URLs, and boosted if originating from authoritative domains (`.gov`, `.nic.in`, official documentation).
5. **Prompt Augmentation**:
   - `ContextService` injects the retrieved sources alongside strict instructions preventing Gemini from relying on its outdated pretrained knowledge or hallucinating.
6. **Streaming & Citations**:
   - Gemini synthesizes the response in the user's selected language (English, Tamil, or Hindi).
   - Clickable source cards are returned and stored in the database alongside the message.

---

## 2. Configuration & API Keys

All configuration resides in `backend/.env`. Real keys must **never** be checked into version control.

### Supported Environment Variables

| Variable | Default | Description |
|---|---|---|
| `WEB_SEARCH_PROVIDER` | `duckduckgo` | Search provider to use: `duckduckgo`, `tavily`, `serpapi`, or `mock` |
| `WEB_SEARCH_API_KEY` | *(empty)* | API key required if using `tavily` or `serpapi` |
| `WEB_SEARCH_MAX_RESULTS` | `5` | Maximum number of search results to retrieve and inject |
| `WEB_SEARCH_TIMEOUT` | `10` | Timeout in seconds for search HTTP requests |
| `GEMINI_API_KEY` | *(your key)* | Google Gemini API key for the primary LLM |

### Example `backend/.env` Configuration

#### Option A: Zero-Credential Default (DuckDuckGo)
```env
WEB_SEARCH_PROVIDER=duckduckgo
WEB_SEARCH_MAX_RESULTS=5
WEB_SEARCH_TIMEOUT=10
```

#### Option B: Tavily AI Search Provider
```env
WEB_SEARCH_PROVIDER=tavily
WEB_SEARCH_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxx
WEB_SEARCH_MAX_RESULTS=5
WEB_SEARCH_TIMEOUT=10
```

#### Option C: SerpApi Google Search Provider
```env
WEB_SEARCH_PROVIDER=serpapi
WEB_SEARCH_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
WEB_SEARCH_MAX_RESULTS=5
WEB_SEARCH_TIMEOUT=10
```

---

## 3. How to Add Another Web Search Provider

The search layer is built on a clean provider abstraction in `backend/app/services/web_search_service.py`.

### Step 1: Implement the `WebSearchProvider` Interface

```python
from app.services.web_search_service import WebSearchProvider, SearchResult
from typing import List
import httpx

class BingSearchProvider(WebSearchProvider):
    def __init__(self, api_key: str, timeout: int = 10):
        self.api_key = api_key
        self.timeout = timeout

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                "https://api.bing.microsoft.com/v7.0/search",
                headers=headers,
                params={"q": query, "count": max_results}
            )
            data = resp.json()
            results = []
            for item in data.get("webPages", {}).get("value", []):
                results.append(SearchResult(
                    title=item.get("name", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    source_name="Bing"
                ))
            return results
```

### Step 2: Register in `WebSearchService._get_provider()`

```python
elif provider_name == "bing":
    return BingSearchProvider(api_key=settings.WEB_SEARCH_API_KEY, timeout=self.timeout)
```

---

## 4. How to Add Specialized Real-Time APIs

Specialized real-time providers live in `backend/app/services/realtime_service.py` under the `RealtimeProvider` interface.

### Example: Adding a Sports Score Provider

```python
class SportsProvider(RealtimeProvider):
    category = "sports"

    def can_handle(self, query: str) -> bool:
        tokens = ["ipl", "cricket score", "premier league", "match result"]
        return any(t in query.lower() for t in tokens)

    async def get_data(self, query: str) -> Optional[List[SearchResult]]:
        # Fetch live data from sports API
        ...
```

Register your provider in `RealtimeService.__init__()`:
```python
self.providers: List[RealtimeProvider] = [
    WeatherProvider(),
    CryptoProvider(),
    StockProvider(),
    SportsProvider(),  # <-- Added
]
```

---

## 5. Testing the System

### Running Automated Backend Tests

The project includes an end-to-end test suite verifying intent detection, provider abstractions, source deduplication, memory isolation, multilingual handling, error recovery, and secret protection:

```bash
# Run all tests
python -m pytest backend/tests

# Run specifically the real-time search test suite
python -m pytest backend/tests/test_zara_realtime_search.py -v
```

### Manual Testing Scenarios

1. **Factual Real-Time Query**:
   - Query: *"Who is the current Chief Minister of Tamil Nadu?"*
   - Verify: Status transitions `🔎 Searching the web...` → `📚 Reading current sources...` → `✦ Generating answer...`. Source cards appear with official government links.
2. **Standard Knowledge Query**:
   - Query: *"What is a Python generator function?"*
   - Verify: Zero search overhead, instant reasoning without web lookup.
3. **Personal User Memory**:
   - Turn 1: *"Remember that my favorite framework is FastAPI."*
   - Turn 2: *"What is my favorite framework?"*
   - Verify: Answered from SQLite memory without triggering web search. Web facts are not saved as personal memory.
4. **Multilingual Test**:
   - Tamil: *"தமிழ்நாட்டின் தற்போதைய முதலமைச்சர் யார்?"* (Answers in Tamil script with live sources).
   - Hindi: *"तमिलनाडु के वर्तमान मुख्यमंत्री कौन हैं?"* (Answers in Hindi script with live sources).
5. **Search Failure Graceful Degradation**:
   - Simulate a network disconnect or invalid key.
   - Verify: Zara responds honestly with *"I couldn't retrieve current web information right now, so I don't want to give you an outdated answer."* without crashing or hallucinating.
