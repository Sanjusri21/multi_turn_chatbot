from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.schemas.chat_schema import MessageResponse

class ConversationBase(BaseModel):
    title: str = Field(..., max_length=255)

class ConversationCreate(BaseModel):
    title: Optional[str] = Field("New Conversation", max_length=255)

class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)

class ConversationResponse(ConversationBase):
    id: str
    summary: Optional[str] = None
    keywords: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = []
    model_config = ConfigDict(from_attributes=True)
