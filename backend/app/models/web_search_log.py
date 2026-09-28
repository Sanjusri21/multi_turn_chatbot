import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class WebSearchLog(Base):
    __tablename__ = "web_search_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    query = Column(String(500), nullable=False)
    provider = Column(String(50), nullable=False, default="duckduckgo")
    result_count = Column(Integer, default=0)
    searched_at = Column(DateTime, default=utc_now, nullable=False)
