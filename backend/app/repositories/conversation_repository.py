from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.conversation import Conversation

class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, conversation_id: str, user_id: Optional[str] = None) -> Optional[Conversation]:
        query = self.db.query(Conversation).filter(Conversation.id == conversation_id)
        if user_id:
            query = query.filter(Conversation.user_id == user_id)
        return query.first()

    def list_by_user(self, user_id: str) -> List[Conversation]:
        return self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).all()

    def create(self, user_id: str, title: str = "New Conversation") -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def update(
        self,
        conversation_id: str,
        user_id: str,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        keywords: Optional[str] = None
    ) -> Optional[Conversation]:
        conversation = self.get(conversation_id, user_id=user_id)
        if not conversation:
            return None
        if title is not None:
            conversation.title = title
        if summary is not None:
            conversation.summary = summary
        if keywords is not None:
            conversation.keywords = keywords
        conversation.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def append_keywords(self, conversation_id: str, user_id: str, new_keywords: List[str]) -> Optional[Conversation]:
        import json
        conversation = self.get(conversation_id, user_id=user_id)
        if not conversation or not new_keywords:
            return conversation
        existing = []
        if conversation.keywords:
            try:
                existing = json.loads(conversation.keywords)
                if not isinstance(existing, list):
                    existing = []
            except Exception:
                existing = [k.strip() for k in conversation.keywords.split(",") if k.strip()]
        
        # Merge case-insensitively while preserving capitalizations
        existing_lower = {k.lower() for k in existing}
        for kw in new_keywords:
            if kw and kw.strip() and kw.strip().lower() not in existing_lower:
                existing.append(kw.strip())
                existing_lower.add(kw.strip().lower())

        conversation.keywords = json.dumps(existing)
        conversation.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def delete(self, conversation_id: str, user_id: str) -> bool:
        conversation = self.get(conversation_id, user_id=user_id)
        if not conversation:
            return False
        self.db.delete(conversation)
        self.db.commit()
        return True

    def touch(self, conversation_id: str, user_id: str) -> None:
        conversation = self.get(conversation_id, user_id=user_id)
        if conversation:
            conversation.updated_at = datetime.now(timezone.utc)
            self.db.commit()

    def search(self, user_id: str, query: str) -> List[Conversation]:
        """
        Finds conversations belonging to user where the query matches:
        - conversation title
        - conversation summary
        - keywords
        - user and assistant message contents
        """
        clean_q = query.strip()
        if not clean_q:
            return self.list_by_user(user_id)

        pattern = f"%{clean_q}%"
        from app.models.message import Message

        matching_msg_query = (
            self.db.query(Message.conversation_id)
            .filter(Message.content.ilike(pattern))
        )

        return (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .filter(
                (Conversation.title.ilike(pattern)) |
                (Conversation.summary.ilike(pattern)) |
                (Conversation.keywords.ilike(pattern)) |
                (Conversation.id.in_(matching_msg_query))
            )
            .order_by(Conversation.updated_at.desc())
            .all()
        )

