import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.repositories.message_repository import MessageRepository
from app.repositories.memory_repository import MemoryRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.settings_repository import SettingsRepository
from app.services.prompt_service import prompt_service
from app.utils.text_utils import format_memories_for_prompt
from app.core.config import settings

STYLE_INSTRUCTIONS: Dict[str, str] = {
    "concise": "Answer directly, succinctly, and avoid unnecessary preamble or filler.",
    "balanced": "Provide clear, well-structured, informative, and engaging responses with balanced detail.",
    "detailed": "Provide comprehensive, in-depth explanations with background principles, technical depth, edge cases, and thorough examples.",
    "beginner-friendly": "Explain concepts using simple language, relatable everyday analogies, clear step-by-step explanations, and minimal jargon.",
    "beginner_friendly": "Explain concepts using simple language, relatable everyday analogies, clear step-by-step explanations, and minimal jargon."
}

class ContextService:
    def __init__(self, db: Session):
        self.db = db
        self.msg_repo = MessageRepository(db)
        self.mem_repo = MemoryRepository(db)
        self.conv_repo = ConversationRepository(db)
        self.settings_repo = SettingsRepository(db)

    def get_system_prompt(self) -> str:
        """Loads the base system prompt instructions."""
        return prompt_service.get_system_prompt()

    def get_user_style_instructions(self, style: Optional[str]) -> str:
        """Returns the specific response style prompt directive based on user settings."""
        normalized = (style or "balanced").strip().lower()
        return STYLE_INSTRUCTIONS.get(normalized, STYLE_INSTRUCTIONS["balanced"])

    def get_memories_block(self, user_id: str, memory_enabled: bool, query: Optional[str] = None) -> Optional[str]:
        """Formats long-term user memories if memory feature is enabled."""
        if not memory_enabled:
            return None
        if query:
            memories = self.mem_repo.retrieve_relevant(user_id=user_id, query=query)
        else:
            memories = self.mem_repo.list_by_user(user_id)
        if not memories:
            return None
        formatted = format_memories_for_prompt(memories)
        return f"[LONG-TERM USER MEMORY]:\n{formatted}"

    def get_previous_conversations_block(
        self,
        user_id: str,
        current_conversation_id: Optional[str],
        query: str
    ) -> Optional[str]:
        """
        Cross-conversation retrieval: Searches previous conversations for messages relevant to query.
        """
        if not query:
            return None
        prev_msgs = self.msg_repo.search_previous_messages(
            user_id=user_id,
            query=query,
            exclude_conversation_id=current_conversation_id,
            limit=3
        )
        if not prev_msgs:
            return None
        lines = []
        for m in prev_msgs:
            role_label = "User" if m.role == "user" else "Zara"
            lines.append(f"- ({role_label}): \"{m.content[:180]}\"")
        return "[RELEVANT PREVIOUS CONVERSATION EXCERPTS]:\n" + "\n".join(lines)

    def get_summary_block(self, conversation_id: Optional[str], user_id: str) -> Optional[str]:
        """Retrieves and formats ongoing conversation summary if present."""
        if not conversation_id:
            return None
        conv = self.conv_repo.get(conversation_id, user_id=user_id)
        if conv and conv.summary:
            return f"[PREVIOUS CONVERSATION SUMMARY]:\n{conv.summary}"
        return None

    def get_keywords_block(self, conversation_id: Optional[str], user_id: str) -> Optional[str]:
        """Retrieves and formats tracked conversation keywords/topics."""
        if not conversation_id:
            return None
        conv = self.conv_repo.get(conversation_id, user_id=user_id)
        if conv and conv.keywords:
            try:
                kw_list = json.loads(conv.keywords)
                if isinstance(kw_list, list) and kw_list:
                    return f"[IMPORTANT CONVERSATION KEYWORDS & TOPICS]:\n" + ", ".join(kw_list)
            except Exception:
                if conv.keywords.strip():
                    return f"[IMPORTANT CONVERSATION KEYWORDS & TOPICS]:\n{conv.keywords}"
        return None

    def get_recent_messages(self, conversation_id: Optional[str], limit: Optional[int] = None) -> List[Any]:
        """Fetches the latest short-term conversation turns up to limit."""
        if not conversation_id:
            return []
        effective_limit = limit or settings.MAX_CONTEXT_MESSAGES
        return self.msg_repo.list_by_conversation(
            conversation_id=conversation_id,
            limit=effective_limit
        )

    def get_retrieval_info(
        self,
        conversation_id: Optional[str],
        user_id: str,
        query: str
    ) -> Dict[str, Any]:
        """
        Determines if long-term memory or cross-conversation facts are relevant to the query.
        """
        user_settings = self.settings_repo.get_or_create(user_id)
        if not user_settings.memory_enabled:
            return {"memory_used": False, "memories": [], "previous_excerpts": []}

        relevant_mems = self.mem_repo.retrieve_relevant(user_id=user_id, query=query, limit=5)
        prev_msgs = self.msg_repo.search_previous_messages(
            user_id=user_id,
            query=query,
            exclude_conversation_id=conversation_id,
            limit=3
        )
        # Check if query specifically targets memory or project or past info
        q_lower = query.lower()
        has_memory_trigger = any(t in q_lower for t in [
            "project", "name", "signaura", "alina", "study", "learning", "python", "fastapi", "yesterday",
            "earlier", "remember", "what is my", "what was my", "tell me about", "திட்டம்", "பெயர்", "பிராஜக்ட்", "प्रोजेक्ट", "नाम"
        ])
        memory_used = bool((relevant_mems and has_memory_trigger) or prev_msgs)
        return {
            "memory_used": memory_used,
            "memories": relevant_mems,
            "previous_excerpts": prev_msgs
        }

    def build_llm_messages(
        self,
        conversation_id: str,
        user_id: str,
        current_user_message: str,
        language: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Assembles the complete, modular LLM prompt sequence:
        1. Base System Prompt (Zara)
        2. User Response Preferences
        3. Relevant Long-term User Memories
        4. Relevant Previous Conversation Excerpts (Cross-conversation memory)
        5. Conversation Summary
        6. Important Keywords
        7. Language Directive
        8. Recent Messages from short-term history
        9. Current User Message
        """
        messages: List[Dict[str, str]] = []
        user_settings = self.settings_repo.get_or_create(user_id)

        # 1. Base System Prompt
        system_parts = [self.get_system_prompt()]

        # 2. User Response Style Preference
        style_instruction = self.get_user_style_instructions(user_settings.response_style)
        system_parts.append(f"[RESPONSE STYLE PREFERENCE ({user_settings.response_style})]:\n{style_instruction}")

        # 3. Relevant Long-term User Memories
        mem_block = self.get_memories_block(user_id, user_settings.memory_enabled, query=current_user_message)
        if mem_block:
            system_parts.append(mem_block)

        # 4. Relevant Previous Conversation Excerpts (Cross-conversation memory, if memory enabled)
        if user_settings.memory_enabled:
            prev_conv_block = self.get_previous_conversations_block(user_id, conversation_id, query=current_user_message)
            if prev_conv_block:
                system_parts.append(prev_conv_block)

        # 5. Conversation Summary
        summary_block = self.get_summary_block(conversation_id, user_id)
        if summary_block:
            system_parts.append(summary_block)

        # 6. Conversation Keywords
        kw_block = self.get_keywords_block(conversation_id, user_id)
        if kw_block:
            system_parts.append(kw_block)

        # 7. Language Directive
        if language == "ta":
            system_parts.append("[LANGUAGE DIRECTIVE]:\nThe user explicitly selected Tamil (தமிழ்). Respond accurately and fluently in Tamil script.")
        elif language == "hi":
            system_parts.append("[LANGUAGE DIRECTIVE]:\nThe user explicitly selected Hindi (हिन्दी). Respond accurately and fluently in Hindi Devanagari script.")
        elif language == "en":
            system_parts.append("[LANGUAGE DIRECTIVE]:\nThe user explicitly selected English. Respond in English.")

        messages.append({
            "role": "system",
            "content": "\n\n".join(system_parts)
        })

        # 8. Recent Messages
        recent_msgs = self.get_recent_messages(conversation_id)
        for msg in recent_msgs:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # 9. Current User Message (if not already included)
        if not recent_msgs or recent_msgs[-1].content != current_user_message or recent_msgs[-1].role != "user":
            messages.append({
                "role": "user",
                "content": current_user_message
            })

        return messages


    def get_debug_context(self, conversation_id: Optional[str], user_id: str) -> Dict[str, Any]:
        """
        Provides full developer inspection data for the Memory Debugger.
        Never exposes API keys or secrets.
        """
        user_settings = self.settings_repo.get_or_create(user_id)
        all_memories = self.mem_repo.list_by_user(user_id)
        recent_msgs = self.get_recent_messages(conversation_id)
        total_msg_count = self.msg_repo.count_by_conversation(conversation_id) if conversation_id else 0

        conv = self.conv_repo.get(conversation_id, user_id=user_id) if conversation_id else None
        keywords: List[str] = []
        if conv and conv.keywords:
            try:
                parsed = json.loads(conv.keywords)
                if isinstance(parsed, list):
                    keywords = parsed
            except Exception:
                keywords = [k.strip() for k in conv.keywords.split(",") if k.strip()]

        # Build final context payload preview
        sample_msg = recent_msgs[-1].content if recent_msgs else "Hello"
        assembled_messages = self.build_llm_messages(
            conversation_id=conversation_id or "preview",
            user_id=user_id,
            current_user_message=sample_msg
        )

        formatted_final_context = "\n\n".join([
            f"=== {m['role'].upper()} ===\n{m['content']}"
            for m in assembled_messages
        ])

        from app.core.config import settings as app_settings
        provider_name = app_settings.LLM_PROVIDER.capitalize()
        model_name = app_settings.MODEL_NAME or app_settings.GEMINI_MODEL or "gemini-2.5-flash"

        memories_data = [
            {"key": m.key, "value": m.value, "category": m.category}
            for m in all_memories
        ]

        recent_msgs_data = [
            {"id": m.id, "role": m.role, "content": m.content, "timestamp": str(m.timestamp)}
            for m in recent_msgs
        ]

        return {
            "llm_provider": provider_name,
            "model_name": model_name,
            "context_usage": {
                "current_messages": len(recent_msgs),
                "max_messages": settings.MAX_CONTEXT_MESSAGES,
                "total_thread_messages": total_msg_count
            },
            "system_prompt_loaded": True,
            "system_prompt": self.get_system_prompt(),
            "user_preferences": {
                "response_style": user_settings.response_style,
                "instructions": self.get_user_style_instructions(user_settings.response_style),
                "memory_enabled": user_settings.memory_enabled,
                "auto_save_memory": user_settings.auto_save_memory
            },
            "memories": memories_data,
            "conversation_summary": conv.summary if conv else None,
            "keywords": keywords,
            "file_context": None,
            "recent_messages": recent_msgs_data,
            "final_context": formatted_final_context
        }
