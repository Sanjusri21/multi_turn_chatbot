# Zara — Architecture & Real-Time Retrieval Journey

Zara (formerly MemoryBot) is a production-ready, modular multi-turn conversational AI assistant powered by Google Gemini and SQLite. Zara combines **persistent user memory** with **live real-time web retrieval**, preventing stale hallucinated answers for time-sensitive questions without requiring vector databases, embeddings, or RAG.

---

## 1. High-Level Architecture & Request Flow

```
User (Web UI / Voice STT)
       ↓
Frontend (React 18 + Vite)
       ↓  (HTTP POST /api/chat/stream or /api/chat with Bearer JWT)
FastAPI Router (chat_routes.py)
       ↓  (User authentication & JWT validation)
Chat Service (chat_service.py)
       ↓
Intent & Freshness Detection (intent_service.py)
       ├── Analyzes query for temporal indicators, entity statuses, live data keywords
       └── Determines: NORMAL_QUERY | MEMORY_QUERY | REAL_TIME_QUERY
       ↓
┌───────────────────────────────────────────────┐
│           Is Current Info Required?           │
└───────────────────────┬───────────────────────┘
                        │
         ┌──────────────┴──────────────┐
         │ NO                          │ YES
         ↓                             ↓
Context Service               Real-Time Retrieval Layer
(System prompt +              (SSE status: "searching")
 User preferences +                    ↓
 Long-term memories +         Web Search / Specialized APIs
 Thread summary +             (DuckDuckGo / Tavily / Open-Meteo / CoinGecko)
 Conversation history +                ↓
 Current user query)          (SSE status: "reading_sources")
         │                             ↓
         │                    Source Processing & Ranking (source_service.py)
         │                    (Authoritative domain boost, deduplication, URL check)
         │                             ↓
         └──────────────┬──────────────┘
                        ↓
                 Context Builder (context_service.py)
                 (Injects "REAL-TIME INFORMATION RULE" & Retrieved Sources)
                        ↓
                 (SSE status: "generating")
                        ↓
                 LLM Service (llm_service.py)
                 (Google Gemini 2.5 Flash / OpenAI / MockLLM)
                        ↓
                 Response Persistence & Memory Isolation
                 (Saves message with sources JSON; does NOT store web facts in user memory)
                        ↓
                 React Frontend UI
                 (Displays live sources cards + Markdown + Syntax-highlighted code + TTS)
```

---

## 2. Intent & Freshness Detection (`intent_service.py`)

Zara strictly differentiates between questions requiring **pretrained reasoning**, **long-term personal memory**, and **live real-time verification**:

1. **Temporal & Freshness Markers**:
   - English: `current`, `currently`, `today`, `tonight`, `now`, `latest`, `recent`, `recently`, `this week`, `this month`, `this year`, `live`, `real-time`, `as of today`, `who is the current...`, `what is happening...`, `latest news`, `current price`, `current status`.
   - Tamil: `தற்போதைய`, `இன்றைய`, `சமீபத்திய`, `இப்போது`, `இப்பொழுது`, `நடப்பு`, `புதிய`.
   - Hindi: `वर्तमान`, `आज`, `हाल ही में`, `अभी`, `ताज़ा`, `लेटेस्ट`, `नवीनतम`.
2. **Semantic Real-Time Intent**:
   - Officeholders & Political Leaders: e.g., *"Who is the current Chief Minister of Tamil Nadu?"*
   - Live Weather: e.g., *"What is the weather today in Coimbatore?"*
   - Market Prices: e.g., *"Current Bitcoin price"*, *"Apple stock price"*.
   - Sports & Live Events: e.g., *"What happened in today's IPL match?"*
   - Software & Tech Releases: e.g., *"What is the latest version of Python?"*
3. **Non-Real-Time Queries (Zero Search Overhead)**:
   - General knowledge: *"What is Python?"*, *"Explain CNN"*.
   - Conversation & Personal Memory: *"What did I tell you about my project?"*, *"My name is Sanju"*.

---

## 3. Real-Time Retrieval Layer (`web_search_service.py` & `realtime_service.py`)

### Web Search Provider Abstraction
The search subsystem decouples search engines behind a common interface:

```python
class WebSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        ...
```

- **DuckDuckGoProvider**: Zero-credential, high-availability async search via `httpx`.
- **TavilySearchProvider**: Specialized AI search provider using `TAVILY_API_KEY`.
- **SerpApiSearchProvider**: Google Search API provider using `SERPAPI_API_KEY`.
- **MockSearchProvider**: Deterministic offline provider for automated test suites.

### Specialized Real-Time Providers
Zara prioritizes structured, authoritative endpoints over general search when appropriate:
- **WeatherProvider**: Uses Open-Meteo free geocoding and weather API.
- **CryptoProvider**: Uses CoinGecko simple price API.
- **StockProvider**: Extensible stock pricing interface.

---

## 4. Source Processing & Authoritative Priority (`source_service.py`)

Retrieved sources are sanitized and evaluated before reaching the LLM:
1. **Deduplication**: Removes duplicate URLs, titles, and empty snippets.
2. **Authoritative Domain Ranking**:
   - Government & Official: `.gov`, `.gov.in`, `nic.in`, `assembly.tn.gov.in`, `sansad.in`.
   - Technology: `docs.python.org`, `python.org`, `github.com`, `kernel.org`, `w3.org`.
   - Reputable News: `reuters.com`, `apnews.com`, `bbc.com`, `thehindu.com`.
3. **Prompt Framing**: Formats sources into a bounded markdown block with clear index numbers, titles, and snippets.
4. **Citation Extraction**: Generates markdown citations with validated URLs.

---

## 5. Context Integration & "Do Not Trust Outdated Knowledge"

When real-time sources are retrieved, `ContextService` injects the **Real-Time Information Rule** into Gemini's system instructions:

```
REAL-TIME INFORMATION RULE:
The following information was retrieved from current web sources.
Use the retrieved sources when answering the user's current-information question.
Do not claim that you know something from your internal knowledge when the answer is based on retrieved sources.
Do not invent facts that are not supported by the retrieved information.
If the sources disagree:
- identify the disagreement
- prefer authoritative and recent sources
- do not silently combine conflicting claims.
If the retrieved information is insufficient:
say that the available sources do not provide enough information.
```

---

## 6. Memory Isolation

Zara strictly preserves the boundary between user memory and web facts:
- **Long-Term Memory**: Stores only durable user attributes (*"User works as a software engineer"*, *"User's name is Sanju"*).
- **Web Search Results**: Stored only in message metadata (`messages.sources` column and `web_search_logs` table) for rendering citations. Web facts are **never** upserted into the `memories` table.

---

## 7. Streaming Flow (Server-Sent Events)

The SSE streaming endpoint (`POST /api/chat/stream`) emits lifecycle status events to keep the user informed during real-time queries:

```
event: status
data: {"stage":"searching","message":"🔎 Searching the web..."}

event: status
data: {"stage":"reading_sources","message":"📚 Reading current sources..."}

event: status
data: {"stage":"generating","message":"✦ Generating answer..."}

event: chunk
data: {"text":"According to the Tamil Nadu Legislative Assembly..."}

event: done
data: {"message_id":"...","conversation_id":"...","sources":[...]}
```

For non-real-time queries, Zara emits:
```
event: status
data: {"stage":"thinking","message":"✦ Thinking..."}
```

---

## 8. Multilingual Architecture (English, Tamil, Hindi)

Zara provides native multilingual support across the entire real-time pipeline:
1. **Query Intent Detection**: Detects temporal tokens in English, Tamil, and Hindi.
2. **Retrieval**: Searches using language-aware keywords.
3. **Response Generation**:
   - English: Direct synthesis with citations.
   - Tamil: Natural Tamil script synthesis directly from Gemini without intermediate English translation.
   - Hindi: Natural Devanagari script synthesis directly from Gemini.
4. **Voice Matching (STT/TTS)**:
   - English: `en-IN`
   - Tamil: `ta-IN`
   - Hindi: `hi-IN`
   - Strict matching ensures no silent fallback to English voices.

---

## 9. Error Handling & Graceful Fallback

- **Search Provider Unavailable / Network Timeout**:
  Zara catches search errors safely, logs a sanitized warning, and returns an honest disclaimer:
  > *"I couldn't retrieve current web information right now, so I don't want to give you an outdated answer."*
  Zara **never** falls back to potentially stale pretrained knowledge to guess current facts.
- **Empty Search Results**:
  Zara states clearly that no reliable current sources were found rather than hallucinating details.
- **LLM Rate Limits / API Failures**:
  Handled with friendly error notifications in the UI without crashing the chat session.

---

## 10. Security & Secrets Management

1. **Zero Secret Exposure**: Search API keys and Gemini API keys are loaded exclusively on the backend via `backend/app/core/config.py`.
2. **Git Hygiene**: `backend/.env` is ignored by `.gitignore`. `backend/.env.example` contains only empty placeholders.
3. **Log Sanitization**: Search queries and result counts are safely logged (`[Search] query="..." results=5`), while secret tokens are strictly masked.
4. **URL Validation**: Frontend only renders clickable links for URLs adhering to valid `http://` or `https://` protocols.

---

## 11. Database Schema

| Table | Primary Key | Key Columns | Purpose |
|---|---|---|---|
| `users` | `id` (UUID) | `name`, `email`, `hashed_password` | User identity & authentication |
| `user_settings` | `id` (UUID) | `user_id`, `response_style`, `theme`, `memory_enabled` | User personalization |
| `conversations` | `id` (UUID) | `user_id`, `title`, `summary`, `keywords`, `updated_at` | Multi-turn chat threads |
| `messages` | `id` (UUID) | `conversation_id`, `role`, `content`, `sources`, `timestamp` | User & Assistant messages |
| `web_search_logs` | `id` (UUID) | `user_id`, `conversation_id`, `query`, `provider`, `result_count`, `searched_at` | Lightweight search audit log |
| `message_attachments` | `id` (UUID) | `message_id`, `filename`, `file_path`, `content_type` | Uploaded document & image metadata |
| `memories` | `id` (UUID) | `user_id`, `key`, `value`, `category`, `conversation_id` | Durable persistent user facts |
| `message_feedback` | `id` (UUID) | `message_id`, `user_id`, `conversation_id`, `feedback` | User 👍 / 👎 ratings |
