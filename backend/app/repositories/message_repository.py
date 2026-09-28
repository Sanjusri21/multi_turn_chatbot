from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.message import Message

class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, message_id: str) -> Optional[Message]:
        return self.db.query(Message).filter(Message.id == message_id).first()

    def create(
        self,
        conversation_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
        language: Optional[str] = "en"
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
            language=language or "en",
            timestamp=datetime.now(timezone.utc)
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def list_by_conversation(self, conversation_id: str, limit: Optional[int] = None) -> List[Message]:
        query = self.db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.timestamp.asc())
        if limit:
            # If limit is specified, get the last N messages
            total = query.count()
            if total > limit:
                return query.offset(total - limit).all()
        return query.all()

    def count_by_conversation(self, conversation_id: str) -> int:
        return self.db.query(Message).filter(Message.conversation_id == conversation_id).count()

    def get_oldest_messages(self, conversation_id: str, count: int) -> List[Message]:
        return self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.timestamp.asc()).limit(count).all()

    def search_previous_messages(
        self,
        user_id: str,
        query: str,
        exclude_conversation_id: Optional[str] = None,
        limit: int = 4
    ) -> List[Message]:
        """
        Cross-conversation retrieval: Searches user messages and assistant messages
        belonging to user_id across previous conversations for relevant terms.
        Strictly isolated to user_id.
        """
        from app.models.conversation import Conversation
        import re

        clean_query = query.strip()
        if not clean_query:
            return []

        # Extract meaningful terms (length >= 3)
        terms = [t.lower() for t in re.findall(r"[\w]+", clean_query) if len(t) >= 3]
        # Ignore frequent non-content words
        stop_words = {"what", "when", "where", "which", "about", "your", "tell", "yesterday", "earlier", "remember", "project"}
        content_terms = [t for t in terms if t not in stop_words] or terms

        q = self.db.query(Message).join(
            Conversation, Message.conversation_id == Conversation.id
        ).filter(
            Conversation.user_id == user_id
        )

        if exclude_conversation_id:
            q = q.filter(Message.conversation_id != exclude_conversation_id)

        # Retrieve candidates from earlier conversations
        candidates = q.order_by(Message.timestamp.desc()).limit(40).all()

        scored = []
        for msg in candidates:
            text_lower = msg.content.lower()
            score = 0
            for term in content_terms:
                if term in text_lower:
                    score += 2
            if score > 0:
                scored.append((score, msg))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

