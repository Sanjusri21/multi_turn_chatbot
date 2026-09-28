from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.services.llm_service import LLMService, get_llm_service
from app.core.config import settings
from app.core.logging_config import logger

class SummarizationService:
    def __init__(self, db: Session, llm_service: Optional[LLMService] = None):
        self.db = db
        self.conv_repo = ConversationRepository(db)
        self.msg_repo = MessageRepository(db)
        self.llm_service = llm_service or get_llm_service()

    def check_and_summarize(self, conversation_id: str, user_id: str) -> Optional[str]:
        """
        If the conversation exceeds the trigger threshold, generates a compact summary
        of older messages and stores it on the conversation record.
        """
        total_msgs = self.msg_repo.count_by_conversation(conversation_id)
        if total_msgs < settings.SUMMARY_TRIGGER_THRESHOLD:
            return None

        conv = self.conv_repo.get(conversation_id, user_id=user_id)
        if not conv:
            return None

        all_msgs = self.msg_repo.list_by_conversation(conversation_id)
        older_msgs_count = max(0, len(all_msgs) - settings.MAX_CONTEXT_MESSAGES)
        if older_msgs_count <= 0:
            return conv.summary

        messages_to_summarize = [
            {"role": m.role, "content": m.content}
            for m in all_msgs[:older_msgs_count]
        ]

        try:
            logger.info(f"Summarizing {len(messages_to_summarize)} older messages for conversation {conversation_id}...")
            new_summary = self.llm_service.generate_summary(
                messages=messages_to_summarize,
                existing_summary=conv.summary
            )
            if new_summary:
                self.conv_repo.update(conversation_id, user_id=user_id, summary=new_summary)
                logger.info(f"Updated conversation summary: {new_summary}")
                return new_summary
        except Exception as e:
            logger.error(f"Failed to generate conversation summary: {e}")

        return conv.summary
