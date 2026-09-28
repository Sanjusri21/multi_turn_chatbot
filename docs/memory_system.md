# MemoryBot — Persistent Memory Architecture

## Short-Term vs. Long-Term Memory

In traditional LLM applications, context is either completely ephemeral (forgotten when the tab closes) or naive (stuffing every message until token overflow occurs).

MemoryBot implements a dual-memory system:

### 1. Short-Term Conversation Memory
- Backed by the `messages` table in SQLite.
- Stores every conversation turn: `id`, `conversation_id`, `role`, `content`, `timestamp`.
- Managed by `ContextService` which limits active history to the most recent `MAX_CONTEXT_MESSAGES` (default 10).
- Older messages exceeding the threshold are automatically compressed into `conversation.summary` by `SummarizationService`.

### 2. Long-Term Persistent Memory
- Backed by the `memories` table in SQLite.
- Independent of conversations: persists indefinitely across sessions and threads.
- Categorized schema:
  - `key`: unique normalized identifier (e.g. `name`, `field_of_study`, `favorite_language`)
  - `value`: factual content (e.g. `Sanju`, `AI & Data Science`)
  - `category`: one of `identity`, `preference`, `interest`, `education`, `skill`, `goal`, or `other`
  - `created_at` and `updated_at`: timestamps for auditing

## Automated Extraction Pipeline

After every conversational exchange, the `MemoryService` triggers an extraction step with low temperature ($0.1$):

```
User Prompt + Assistant Response
              │
              ▼
   Memory Extraction Prompt
              │
              ▼
  JSON Schema Normalization
              │
              ▼
  Key Deduping & DB Upsert
```

### Prompt Guardrails
- Only extracts persistent facts (e.g. identity, hobbies, skills, long-term goals).
- Discards momentary or ephemeral comments (e.g. "I am hungry right now").
- Eliminates duplicate entries by upserting based on normalized keys.

## User Control & Transparency
The Memory Panel provides full visibility:
- Review all stored facts organized by category pills.
- Manually create, edit, or delete specific items.
- "Clear all memories" action with a safety confirmation dialog.
