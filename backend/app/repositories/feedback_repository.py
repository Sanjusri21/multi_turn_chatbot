from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.message_feedback import MessageFeedback

class FeedbackRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_message_and_user(self, message_id: str, user_id: str) -> Optional[MessageFeedback]:
        return self.db.query(MessageFeedback).filter(
            MessageFeedback.message_id == message_id,
            MessageFeedback.user_id == user_id
        ).first()

    def set_feedback(
        self,
        message_id: str,
        user_id: str,
        conversation_id: str,
        feedback: Optional[str]
    ) -> Optional[MessageFeedback]:
        """
        Creates, updates, or clears user feedback for an assistant message.
        If feedback is None or empty, deletes any existing feedback.
        """
        existing = self.get_by_message_and_user(message_id, user_id)
        if not feedback:
            if existing:
                self.db.delete(existing)
                self.db.commit()
            return None

        clean_feedback = feedback.strip().lower()
        if clean_feedback not in ("like", "dislike"):
            raise ValueError("Feedback must be 'like' or 'dislike'.")

        if existing:
            existing.feedback = clean_feedback
            existing.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            item = MessageFeedback(
                message_id=message_id,
                user_id=user_id,
                conversation_id=conversation_id,
                feedback=clean_feedback
            )
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            return item
