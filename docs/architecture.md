# MemoryBot — Architecture & Request Journey

MemoryBot is a production-ready, modular multi-turn conversational AI system designed to solve the limitations of stateless chatbots. It maintains context continuity across turns, dynamically extracts and persists long-term personal facts, manages token budgets via context windowing and auto-summarization, supports real-time streaming, and offers deep developer inspectability through the Memory Debugger.

---

## High-Level Journey: How a Message Travels Through MemoryBot

```
User Typing Message
        ↓
React Frontend (Vite + React 18)
        ↓  (HTTP POST /api/chat/stream with Bearer JWT)
FastAPI Router (chat_routes.py)
        ↓  (JWT validation & user isolation via get_current_user)
Authentication Dependency
        ↓
Chat Service (chat_service.py)
        ├── 1. Saves User Message & Attachments to SQLite
        ├── 2. Auto-titles conversation if first turn
        ↓
Context Service (context_service.py)
        ├── 3. System Prompt
        ├── 4. User Response Style Preference (Concise, Balanced, Detailed, Beginner-friendly)
        ├── 5. Injects Long-Term Memories (from MemoryRepository)
        ├── 6. Injects Cumulative Conversation Summary
        ├── 7. Injects Conversation Keywords
        ├── 8. Injects Relevant Document Content (PDF, DOCX, TXT, CSV)
        ├── 9. Injects Recent Message History (within MAX_CONTEXT_MESSAGES)
        └── 10. Injects Current User Turn
        ↓
Memory Service (memory_service.py)
        └── Prepares fact retrieval & category mapping
        ↓
LLM Service (llm_service.py)
        └── Provider Abstraction (Google Gemini 2.5 Flash / OpenAI / Mock)
        ↓
Streaming Execution
        └── Yields chunks via Server-Sent Events (SSE) back to React in real time
        ↓
Response Persistence & Fact Extraction
        ├── Saves complete Assistant Message to SQLite (messages table)
        ├── Extracts new durable personal facts (name, education, tech stack, preferences)
        ├── Upserts memories into SQLite (memories table)
        ├── Checks if conversation requires rolling summarization
        └── Updates conversation timestamp (updated_at)
        ↓
React UI
        ├── Displays progressive stream rendering
        ├── Renders Markdown & Syntax-highlighted code blocks with [Copy code]
        ├── Shows subtle auto-dismissing "✨ Memory saved" status badge
        └── Enables in-place [Regenerate] and [👍 / 👎] feedback actions
```

---

## Core Components

### 1. Frontend Layer (`frontend/src/`)
- **Pages**: `ChatPage`, `LoginPage`, `SignupPage`.
- **Chat Window**:
  - `ChatWindow.jsx`: Renders message stream, welcome prompts, and auto-scrolling.
  - `MessageBubble.jsx`: Renders user and assistant bubbles with Markdown, attachments, timestamp, action bar (`Copy`, `Regenerate`, `👍`, `👎`), and auto-dismissing `✨ Memory saved` notification chip.
  - `MarkdownRenderer.jsx`: Powered by `react-markdown` with custom components for headers, tables, blockquotes, links, and code blocks with language headers and dedicated `Copy code` buttons.
  - `MessageInput.jsx`: Comprehensive input dock supporting text input, attachments (`.pdf`, `.docx`, `.txt`, `.csv`, `.png`, `.jpg`), drag-and-drop, image paste (`Ctrl+V`), microphone voice-to-text, and generation controls (`Send` vs `Stop generating`).
- **Sidebar**:
  - `Sidebar.jsx` & `ConversationList.jsx`: Temporal grouping into **Today**, **Yesterday**, **Previous 7 days**, and **Older**. Real-time debounced search queries titles, summaries, keywords, and message contents. Supports inline thread title renaming and deletion.
- **Memory Drawer (`MemoryPanel.jsx`)**:
  - Organizes memories into clean categories:
    - 👤 Personal (name, location, identity)
    - 🎓 Education (field of study, degree)
    - 💻 Technologies (languages, frameworks)
    - 🚀 Projects (apps, repositories)
    - 🎯 Goals (learning & career objectives)
    - ⭐ Preferences (likes/dislikes)
    - 📋 Other
  - Supports Add, Edit, Delete, and "Forget All".
- **Settings Modal (`SettingsModal.jsx`)**:
  - General Settings: Response style configuration (Concise, Balanced, Detailed, Beginner-friendly).
  - Appearance Settings: Theme toggling (Dark, Light, System) and animation speed controls.
  - Memory Settings: Global memory toggle, auto-save memory toggle, and memory clear.
  - Memory Debugger: Real-time inspection of LLM provider, model, context usage, system prompt, long-term memory, conversation summary, keywords, and full compiled final context.
  - Account Settings: Password update and account deletion.

---

### 2. Backend Layer (`backend/app/`)
- **`api/`**: REST controller endpoints for Auth, Chat, Streaming, Conversations, Memories, Settings, Files, and Health.
- **`services/`**:
  - `chat_service.py`: Orchestrates multi-turn workflows, SSE response streaming, in-place regeneration, and message feedback.
  - `context_service.py`: Assembles modular context blocks (system prompt, user preferences, memories, summary, keywords, files, recent messages). Provides full developer inspection for the Memory Debugger.
  - `memory_service.py`: Extracts and standardizes user facts into durable categories. Rejects general questions, greetings, and file contents.
  - `summarization_service.py`: Automatically compresses messages exceeding the sliding window threshold into an ongoing thread summary.
  - `llm_service.py`: Provider-agnostic engine supporting Google Gemini (`gemini-2.5-flash`), OpenAI (`gpt-4o-mini`), and zero-dependency `MockLLMProvider` for offline test suites.
  - `file_context_service.py` & `file_service.py`: Parses documents (PDF, DOCX, TXT, CSV) and images into conversational context.
- **`repositories/`**: Clean database access layer isolating SQLAlchemy ORM queries for `User`, `UserSettings`, `Conversation`, `Message`, `Memory`, `MessageAttachment`, and `MessageFeedback`.
- **`models/`**: SQLAlchemy models with foreign-key constraints, cascading deletes, and indexes for fast retrieval.

---

### 3. Database Schema

| Table | Primary Key | Key Columns | Purpose |
|---|---|---|---|
| `users` | `id` (UUID) | `name`, `email`, `hashed_password` | User identity & authentication |
| `user_settings` | `id` (UUID) | `user_id`, `response_style`, `theme`, `memory_enabled` | ChatGPT-style customizations |
| `conversations` | `id` (UUID) | `user_id`, `title`, `summary`, `keywords`, `updated_at` | Multi-turn chat threads |
| `messages` | `id` (UUID) | `conversation_id`, `role`, `content`, `timestamp` | User & Assistant messages |
| `message_attachments` | `id` (UUID) | `message_id`, `filename`, `file_path`, `content_type` | Uploaded document & image metadata |
| `memories` | `id` (UUID) | `user_id`, `key`, `value`, `category`, `conversation_id` | Durable persistent user facts |
| `message_feedback` | `id` (UUID) | `message_id`, `user_id`, `conversation_id`, `feedback` | User 👍 / 👎 ratings |
