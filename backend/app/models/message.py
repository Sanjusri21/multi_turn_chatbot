import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    role = Column(String(20), nullable=False)  # "system", "user", "assistant"
    content = Column(Text, nullable=False)
    language = Column(String(10), nullable=True, default="en")
    sources = Column(Text, nullable=True)  # JSON-encoded array of retrieved sources
    timestamp = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User", foreign_keys=[user_id])
    attachments = relationship("MessageAttachment", back_populates="message", cascade="all, delete-orphan", order_by="MessageAttachment.created_at.asc()")

