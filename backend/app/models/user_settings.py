import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # General
    language = Column(String(20), default="en", nullable=False)
    response_style = Column(String(30), default="balanced", nullable=False)  # balanced, creative, precise
    enter_behavior = Column(String(20), default="send", nullable=False)      # send, newline

    # Appearance
    theme = Column(String(20), default="dark", nullable=False)               # dark, light, system
    accent_style = Column(String(30), default="blue_violet", nullable=False)
    animations_enabled = Column(Boolean, default=True, nullable=False)

    # Memory
    memory_enabled = Column(Boolean, default=True, nullable=False)
    auto_save_memory = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationship
    user = relationship("User", back_populates="settings")
