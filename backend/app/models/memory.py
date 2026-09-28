import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Memory(Base):
    __tablename__ = "memories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    source_conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)
    memory_text = Column(Text, nullable=True)
    memory_type = Column(String(50), nullable=True, default="other")
    importance = Column(String(20), nullable=True, default="normal")
    category = Column(String(50), nullable=False, default="other", index=True)
    # categories: identity, preference, interest, education, skill, goal, other
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    @property
    def memory_id(self) -> str:
        return self.id

    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uix_user_key"),
    )

    # Relationships
    user = relationship("User", back_populates="memories")

