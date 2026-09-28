from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from app.repositories.memory_repository import MemoryRepository
from app.repositories.conversation_repository import ConversationRepository
from app.models.memory import Memory
from app.services.llm_service import LLMService, get_llm_service
from app.core.logging_config import logger

class MemoryService:
    def __init__(self, db: Session, llm_service: Optional[LLMService] = None):
        self.db = db
        self.memory_repo = MemoryRepository(db)
        self.conv_repo = ConversationRepository(db)
        self._llm_service = llm_service

    @property
    def llm_service(self) -> LLMService:
        if self._llm_service is None:
            self._llm_service = get_llm_service()
        return self._llm_service

    def list_all_memories(self, user_id: str) -> List[Memory]:
        return self.memory_repo.list_by_user(user_id)

    def list_by_category(self, user_id: str, category: str) -> List[Memory]:
        return self.memory_repo.list_by_category(user_id, category)

    def retrieve_relevant_memories(self, user_id: str, query: str, limit: int = 8) -> List[Memory]:
        """
        Public memory retrieval service returning memories belonging to user_id relevant to query.
        """
        return self.memory_repo.retrieve_relevant(user_id=user_id, query=query, limit=limit)

    def retrieve_relevant_conversations(
        self,
        user_id: str,
        query: str,
        exclude_conversation_id: Optional[str] = None,
        limit: int = 4
    ) -> List[Any]:
        """
        Cross-conversation retrieval service returning relevant historical message turns for user_id.
        """
        from app.repositories.message_repository import MessageRepository
        msg_repo = MessageRepository(self.db)
        return msg_repo.search_previous_messages(
            user_id=user_id,
            query=query,
            exclude_conversation_id=exclude_conversation_id,
            limit=limit
        )

    def create_memory(
        self,
        user_id: str,
        key: str,
        value: str,
        category: str = "other",
        conversation_id: Optional[str] = None,
        source_conversation_id: Optional[str] = None,
        memory_text: Optional[str] = None,
        importance: Optional[str] = "normal"
    ) -> Memory:
        return self.memory_repo.upsert(
            user_id=user_id,
            key=key,
            value=value,
            category=category,
            conversation_id=conversation_id or source_conversation_id,
            source_conversation_id=source_conversation_id or conversation_id,
            memory_text=memory_text,
            importance=importance
        )

    def save_memory(self, user_id: str, memory: Any) -> Memory:
        """
        Public save_memory API: Accepts dict, MemoryCreate, or keyword object.
        """
        if isinstance(memory, dict):
            k = memory.get("key") or "fact"
            v = memory.get("value") or memory.get("memory_text") or ""
            c = memory.get("category") or memory.get("memory_type") or "other"
            conv_id = memory.get("conversation_id") or memory.get("source_conversation_id")
            mem_text = memory.get("memory_text")
            imp = memory.get("importance", "normal")
        else:
            k = getattr(memory, "key", "fact")
            v = getattr(memory, "value", getattr(memory, "memory_text", ""))
            c = getattr(memory, "category", getattr(memory, "memory_type", "other"))
            conv_id = getattr(memory, "conversation_id", getattr(memory, "source_conversation_id", None))
            mem_text = getattr(memory, "memory_text", None)
            imp = getattr(memory, "importance", "normal")

        return self.create_memory(
            user_id=user_id,
            key=k,
            value=v,
            category=c,
            conversation_id=conv_id,
            source_conversation_id=conv_id,
            memory_text=mem_text,
            importance=imp
        )

    def extract_memories(self, user_message: str, conversation_context: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Public extraction service delegating to LLM service.
        """
        return self.llm_service.extract_memories(
            user_message=user_message,
            assistant_response=conversation_context or ""
        )

    def update_memory(
        self,
        memory_id: str,
        user_id: str,
        key: Optional[str] = None,
        value: Optional[str] = None,
        category: Optional[str] = None,
        conversation_id: Optional[str] = None,
        source_conversation_id: Optional[str] = None,
        memory_text: Optional[str] = None,
        importance: Optional[str] = None
    ) -> Optional[Memory]:
        return self.memory_repo.update(
            memory_id=memory_id,
            user_id=user_id,
            key=key,
            value=value,
            category=category,
            conversation_id=conversation_id or source_conversation_id,
            source_conversation_id=source_conversation_id or conversation_id,
            memory_text=memory_text,
            importance=importance
        )

    def delete_memory(self, memory_id: str, user_id: str) -> bool:
        return self.memory_repo.delete(memory_id=memory_id, user_id=user_id)

    def clear_all_memories(self, user_id: str) -> int:
        return self.memory_repo.delete_all(user_id)

    def extract_and_store_memories(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str,
        conversation_id: Optional[str] = None
    ) -> List[Memory]:
        """
        Invokes LLM extraction and persists new or updated persistent facts for this user,
        and saves relevant keywords for this conversation thread.
        Avoids duplicates by upserting on key and updating existing memories.
        """
        try:
            # 1. Extract and store conversation keywords
            if conversation_id:
                extracted_kws = self.llm_service.extract_keywords(user_message)
                if extracted_kws:
                    self.conv_repo.append_keywords(conversation_id, user_id=user_id, new_keywords=extracted_kws)
                    logger.info(f"Conversation {conversation_id} - Appended keywords: {extracted_kws}")

            # 2. Extract structured memories (identity, education, skills, projects, interests, goals)
            extracted_items = self.llm_service.extract_memories(
                user_message=user_message,
                assistant_response=assistant_response
            )
            saved_memories = []
            for item in extracted_items:
                k = item.get("key")
                v = item.get("value")
                c = item.get("category", "other")
                imp = item.get("importance", "normal")
                mem_text = item.get("memory_text") or f"User's {str(k).replace('_', ' ')} is {str(v)}."
                if k and v:
                    mem = self.memory_repo.upsert(
                        user_id=user_id,
                        key=k,
                        value=v,
                        category=c,
                        conversation_id=conversation_id,
                        source_conversation_id=conversation_id,
                        memory_text=mem_text,
                        importance=imp
                    )
                    saved_memories.append(mem)
                    logger.info(f"User {user_id} - Saved memory: [{c}] {k} = {v} (conv: {conversation_id})")

            return saved_memories
        except Exception as e:
            logger.error(f"Error in extract_and_store_memories for user {user_id}: {e}")
            return []
