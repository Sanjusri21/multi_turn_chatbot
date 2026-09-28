# MemoryBot — Multi-Turn AI Chatbot with Persistent Memory

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5.2-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![JWT](https://img.shields.io/badge/Auth-JWT%20%2B%20PBKDF2-orange?style=flat)](https://jwt.io/)

**MemoryBot** is a production-grade, full-stack multi-turn conversational AI assistant engineered for true continuity. Unlike stateless chat apps that lose context after every session, MemoryBot combines **multi-turn session history**, **real-time streaming LLM responses**, **automatic persistent long-term memory extraction**, **context window budgeting with auto-summarization**, **live conversation search**, and a developer-oriented **Memory Debugger**.

The floating robot companion has been removed from the main chat workspace to prioritize a focused, modern, distraction-free conversational experience while retaining RotoBot branding on authentication and welcome views.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Authentication Flow](#authentication-flow)
- [Chat & Streaming Flow](#chat--streaming-flow)
- [Persistent Memory Architecture](#persistent-memory-architecture)
- [Context Management & Budgeting](#context-management--budgeting)
- [LLM Provider Integration](#llm-provider-integration)
- [File Processing & Voice Input](#file-processing--voice-input)
- [Conversation Search](#conversation-search)
- [Memory Debugger](#memory-debugger)
- [API Endpoints Reference](#api-endpoints-reference)
- [Database Schema](#database-schema)
- [Environment Variables](#environment-variables)
- [How to Run Backend & Frontend](#how-to-run-backend--frontend)
- [Testing & Validation](#testing--validation)
- [Troubleshooting](#troubleshooting)

---

## Project Overview

MemoryBot bridges the gap between raw LLM APIs and real-world conversational assistants:
1. **Persistent Long-Term Memory**: Automatically extracts personal user facts (name, tech stack, education, projects, preferences) and saves them across conversations without storing random questions or file contents.
2. **Real-time SSE Streaming**: Chunks stream progressively to the UI with generating indicators, abort/stop controls, and automatic non-streaming fallback.
3. **Multi-Turn Continuity & History**: Conversations are organized temporally (*Today*, *Yesterday*, *Previous 7 days*, *Older*) with title auto-generation, manual rename, and deletion.
4. **Full Conversation Search**: Search across titles, summaries, keywords, and message content with frontend debouncing.
5. **In-place Regeneration & Feedback**: Regenerate assistant responses without creating duplicate user messages, and submit thumbs up/down feedback.
6. **Code Highlighting & Copy**: Full GitHub-flavored Markdown rendering with syntax highlighting, copy-all, and single-click copy-code.
7. **Developer Memory Debugger**: Inspect active system prompts, response style instructions, long-term memories, conversation summaries, keyword tags, and assembled prompt context in real-time.

---

## Architecture & Tech Stack

```
User (Browser)
    │
    ▼
React 18 + Vite Frontend
    │  • SSE streaming reader & chunk buffering
    │  • Debounced search & temporal conversation lists
    │  • Markdown & syntax-highlighted code blocks
    │  • Drag-and-drop file upload & Web Speech voice input
    │  • Memory Debugger modal
    │
    ▼ HTTP / SSE (JWT Bearer Token)
FastAPI Backend (Python 3.11+)
    │
    ├── Auth & Security (PBKDF2-SHA256, PyJWT)
    ├── API Route Handlers (/api/chat, /api/conversations, /api/memories, /api/settings)
    ├── Chat Service (Flow orchestration, streaming, regeneration, feedback)
    ├── Context Service (Modular budget assembly & response style enforcement)
    ├── Memory Service (Rule-based & LLM extraction, category mapping, deduplication)
    ├── Summarization Service (Background incremental conversation compaction)
    └── LLM Service (Provider abstraction for Gemini, OpenAI, and Mock fallback)
            │
            ├── Google Gemini (gemini-2.5-flash via google-genai / google.generativeai)
            ├── OpenAI (gpt-4o-mini via openai client)
            └── Mock Provider (Zero-dependency offline mode with deterministic tests)
```

### Backend Tech Stack
- **Framework**: FastAPI (Async ASGI)
- **Database & ORM**: SQLite 3 with SQLAlchemy 2.0
- **Security**: PBKDF2-HMAC-SHA256 (standard library) + PyJWT
- **Validation**: Pydantic v2 & Pydantic-Settings
- **Testing**: `pytest` & `pytest-asyncio`

### Frontend Tech Stack
- **Framework**: React 18 with Vite
- **Styling**: Vanilla CSS with custom properties & glassmorphism
- **Markdown & Code**: `react-markdown` with custom syntax and copy triggers
- **Icons**: Lucide React
- **State Management**: React Context (`AuthContext`, `ChatContext`)

---

## Authentication Flow

1. **Sign Up (`POST /api/auth/signup`)**:
   - Validates username and password complexity.
   - Hashes password using standard `hashlib.pbkdf2_hmac` with a secure random salt.
   - Creates the `User` and generates a default `UserSettings` profile.
2. **Log In (`POST /api/auth/login`)**:
   - Verifies password hash.
   - Issues a signed stateless JWT access token (HS256).
   - Returns token and user metadata.
3. **Request Authorization**:
   - Frontend stores the JWT in `localStorage` and automatically attaches it as an `Authorization: Bearer <token>` header to all outgoing requests.
   - Backend `get_current_user` dependency verifies the token signature and resolves the `User` record on every protected route.

---

## Chat & Streaming Flow

```
User sends message / clicks Regenerate
             │
             ▼
   POST /api/chat/stream
             │
             ├── 1. Persist user message to SQLite (skipped on regenerate)
             ├── 2. Fetch active long-term memories for user
             ├── 3. Fetch conversation history, summary, and file context
             ├── 4. Read user response style preference (Concise/Balanced/Detailed/Beginner-friendly)
             ├── 5. ContextService builds modular system prompt & token-budgeted messages
             ├── 6. LLMService calls provider stream (Gemini/OpenAI/Mock)
             │
             ▼ Server-Sent Events (SSE)
   Event: "chunk" -> Data: {"chunk": "..."}
   Event: "status" -> Data: {"stage": "extracting_memory"}
   Event: "memory_saved" -> Data: {"key": "...", "value": "..."}
   Event: "done" -> Data: {"assistant_message": {...}}
             │
             ├── 7. Persist final assistant response to SQLite Message table
             └── 8. Trigger background memory extraction & conversation auto-summarization
```

- **Frontend Handling**: Readable stream reader progressively appends tokens to the active message bubble.
- **Stop Generation**: Users can click `Stop generating` at any time; the frontend aborts the `fetch` signal and displays the tokens received so far.
- **Non-Streaming Fallback**: If SSE streaming is interrupted or fails, the frontend cleanly falls back to `POST /api/chat`.

---

## Persistent Memory Architecture

MemoryBot maintains two independent tiers of memory:
1. **Short-Term Conversation History**: Multi-turn dialogue tied strictly to a specific `conversation_id`.
2. **Persistent Long-Term Memory**: Structured key-value facts tied to the `user_id` across *all* conversations.

### Memory Categories
Memories are automatically classified or manually organized into:
- 👤 **Personal**: Name, location, identity details (`name`, `location`)
- 🎓 **Education**: Degree, major, certifications (`field`, `education`)
- 💻 **Technologies**: Languages, frameworks, tools (`technology`, `skill`)
- 🚀 **Projects**: Applications and software under development (`project`)
- 🎯 **Goals**: Professional and learning milestones (`goal`)
- ⭐ **Preferences**: Coding style, favorite tools (`preference`)
- 📋 **Other**: Miscellaneous user facts

### Extraction Guardrails
- **Only User Facts Are Saved**: Statements like *"My name is Sanju and I am learning Python"* extract `name = Sanju` and `technology = Python`.
- **Informational Inquiries Are Ignored**: Queries like *"Explain Python"*, *"What is FastAPI?"*, or conversational greetings (*"Hello"*) are strictly rejected and never saved to memory.
- **File Content Isolation**: Document text from uploaded PDFs/TXTs is maintained strictly as conversation context and never automatically dumped into long-term memory.
- **Visual Feedback**: When a long-term memory is extracted or updated, an auto-dismissing `✨ Memory saved` badge appears beneath the assistant bubble.

---

## Context Management & Budgeting

`ContextService` builds the exact context envelope sent to the LLM:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. SYSTEM PROMPT                                            │
│    Core persona, identity guidelines, and directives        │
├─────────────────────────────────────────────────────────────┤
│ 2. RESPONSE STYLE DIRECTIVE                                 │
│    • Concise: Direct answers, minimal fluff                 │
│    • Balanced: Standard depth and code examples             │
│    • Detailed: Deep explanations, edge cases, internals     │
│    • Beginner-friendly: Simple analogies, step-by-step      │
├─────────────────────────────────────────────────────────────┤
│ 3. USER LONG-TERM MEMORY                                    │
│    Active user facts (e.g., Name: Sanju, Skill: Python)     │
├─────────────────────────────────────────────────────────────┤
│ 4. CONVERSATION SUMMARY                                     │
│    Recursive summary of messages older than sliding window  │
├─────────────────────────────────────────────────────────────┤
│ 5. RELEVANT FILE CONTEXT                                    │
│    Transient file snippets uploaded in current session      │
├─────────────────────────────────────────────────────────────┤
│ 6. RECENT MESSAGES (SLIDING WINDOW)                         │
│    Last N raw messages (default: 10 messages)               │
├─────────────────────────────────────────────────────────────┤
│ 7. CURRENT USER MESSAGE                                     │
│    Latest prompt / query to be answered                     │
└─────────────────────────────────────────────────────────────┘
```

---

## LLM Provider Integration

Supported LLM engines via unified provider interface:
- **Google Gemini**: Uses `gemini-2.5-flash` or `gemini-1.5-flash` via the official Google GenAI SDK. Full native chunk streaming support.
- **OpenAI**: Compatible with `gpt-4o-mini`, `gpt-4o`, and custom base URLs.
- **Mock Provider**: Zero-dependency deterministic offline provider for automated testing, offline development, and zero-cost verifications.

---

## File Processing & Voice Input

- **File Attachments**: Supports `.txt`, `.py`, `.json`, `.csv`, `.md`, and `.pdf` files. Text extracts are injected cleanly into the transient conversation context without polluting user long-term memory.
- **Voice Input**: Web Speech API integration in `MessageInput.jsx`. Tap the microphone icon `🎤` to speak; real-time transcription populates the input field.

---

## Conversation Search

Search conversations directly from the sidebar without page reload:
- **Endpoint**: `GET /api/conversations/search?q=query` or `GET /api/conversations?q=query`
- **Scope**: Matches conversation titles, cumulative summaries, keyword tags, and individual message content.
- **Debounce**: Frontend executes search after 300ms idle, avoiding unnecessary database queries.

---

## Memory Debugger

Accessible from **Settings → Memory Debugger**:
- **LLM Engine**: Provider (`gemini`, `openai`, `mock`) and active model name.
- **Context Budget**: Live count of included messages vs window threshold.
- **Active Components**: Status checkmarks for System Prompt, Long-Term Memories, Conversation Summary, and Keywords.
- **View Full Assembled Context**: Inspect the exact formatted text payload sent to the LLM without exposing API keys or secrets.

---

## API Endpoints Reference

### Authentication (`/api/auth`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/signup` | Register new user account |
| `POST` | `/api/auth/login` | Authenticate and obtain JWT token |
| `GET` | `/api/auth/me` | Fetch authenticated user profile |

### Chat & LLM (`/api/chat`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Send message (synchronous fallback) |
| `POST` | `/api/chat/stream` | Stream message chunks via Server-Sent Events |
| `POST` | `/api/chat/regenerate` | Regenerate assistant response in-place |
| `POST` | `/api/chat/feedback` | Record 👍 or 👎 feedback on a message |
| `GET` | `/api/chat/debug-context` | Retrieve assembled LLM prompt context for debugging |

### Conversations (`/api/conversations`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/conversations` | List conversations (supports `?q=` search) |
| `GET` | `/api/conversations/search` | Dedicated conversation search endpoint |
| `POST` | `/api/conversations` | Create a new conversation thread |
| `GET` | `/api/conversations/{id}` | Fetch conversation messages and file metadata |
| `PATCH` | `/api/conversations/{id}` | Rename conversation title |
| `DELETE` | `/api/conversations/{id}` | Delete conversation and messages |

### Persistent Memory (`/api/memories`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/memories` | List user memories (supports `?category=`) |
| `POST` | `/api/memories` | Manually insert a persistent fact |
| `PATCH` | `/api/memories/{id}` | Update memory key/value/category |
| `DELETE` | `/api/memories/{id}` | Delete a specific memory item |
| `DELETE` | `/api/memories` | Clear all memories for current user |

### Settings (`/api/settings`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/settings` | Get user preferences (response style, theme, system prompt) |
| `PATCH` | `/api/settings` | Update user settings |
| `POST` | `/api/settings/password` | Change account password |
| `DELETE` | `/api/settings/account` | Delete user account and all data |

---

## Database Schema

```
┌─────────────────────────────────┐
│ users                           │
├─────────────────────────────────┤
│ id (PK)                         │
│ username (UNIQUE)               │
│ email (UNIQUE)                  │
│ password_hash                   │
│ is_active                       │
│ created_at                      │
└─────────────────────────────────┘
         │               │
         ▼               ▼
┌──────────────────┐  ┌──────────────────┐
│ conversations    │  │ user_settings    │
├──────────────────┤  ├──────────────────┤
│ id (PK)          │  │ id (PK)          │
│ user_id (FK)     │  │ user_id (FK)     │
│ title            │  │ theme            │
│ summary          │  │ response_style   │
│ keywords         │  │ system_prompt    │
│ created_at       │  │ memory_enabled   │
│ updated_at       │  │ summary_enabled  │
└──────────────────┘  └──────────────────┘
         │
         ▼
┌──────────────────┐  ┌──────────────────┐
│ messages         │  │ memories         │
├──────────────────┤  ├──────────────────┤
│ id (PK)          │  │ id (PK)          │
│ conversation_id  │  │ user_id (FK)     │
│ user_id (FK)     │  │ category         │
│ role             │  │ key              │
│ content          │  │ value            │
│ has_file_context │  │ confidence       │
│ file_metadata    │  │ created_at       │
│ created_at       │  │ updated_at       │
└──────────────────┘  └──────────────────┘
         │
         ▼
┌──────────────────┐
│ message_feedback │
├──────────────────┤
│ id (PK)          │
│ message_id (FK)  │
│ user_id (FK)     │
│ conversation_id  │
│ feedback (up/down│
│ created_at       │
└──────────────────┘
```

---

## Environment Variables

Configure backend settings via `backend/.env`:

```env
# LLM Provider Configuration
LLM_PROVIDER=gemini                  # "gemini" | "openai" | "mock"
GEMINI_API_KEY=your_gemini_api_key   # Leave blank to use offline Mock provider
GEMINI_MODEL=gemini-2.5-flash        # or gemini-1.5-flash

# OpenAI Settings (if LLM_PROVIDER=openai)
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini

# Database Configuration
DATABASE_URL=sqlite:///./data/memorybot.db

# Security & JWT
SECRET_KEY=generate_a_random_32_byte_hex_string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Context & Memory Limits
MAX_CONTEXT_MESSAGES=10
SUMMARY_TRIGGER_THRESHOLD=14
```

---

## How to Run Backend & Frontend

### 1. Run the Backend
From the project root:
```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Run the Frontend
From the `frontend/` directory:
```powershell
npm run dev
```
Chatbot App: [http://localhost:5173](http://localhost:5173)

---

## Testing & Validation

### Backend Automated Test Suite
Run the 28 comprehensive tests (100% pass rate):
```powershell
python -m pytest backend/tests/ -v
```

Tests verify:
- Synchronous & streaming LLM chat endpoints
- Multi-turn conversation history
- Persistent long-term memory extraction & retrieval
- Cross-conversation memory isolation
- Full-text conversation search
- Assistant response regeneration
- Message feedback persistence (thumbs up/down)
- User settings & response style prompt integration
- Memory Debugger context assembly
- Authentication ownership & multi-tenant isolation

### Frontend Production Build
```powershell
cd frontend
npm run build
```

---

## Troubleshooting

- **CORS Issues**: Ensure frontend is running on `http://localhost:5173` or update `ALLOWED_ORIGINS` in `backend/app/core/config.py`.
- **Port 8000 in Use**: Free the port using PowerShell:
  ```powershell
  Get-NetTCPConnection -LocalPort 8000 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
  ```
- **Gemini API Quotas / Rate Limits**: Set `LLM_PROVIDER=mock` in `backend/.env` for instant local testing without API keys.
- **Database Reset**: To start with a clean state, delete `data/memorybot.db`; it will be regenerated automatically on the next backend start.
