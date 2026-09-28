from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

from app.schemas.file_schema import AttachmentResponse

class MessageBase(BaseModel):
    role: str
    content: str

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: str
    conversation_id: str
    user_id: Optional[str] = None
    language: Optional[str] = "en"
    timestamp: datetime
    attachments: List[AttachmentResponse] = []
    model_config = ConfigDict(from_attributes=True)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User input message")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID if continuing a thread")
    attachment_ids: Optional[List[str]] = Field(default=None, description="List of uploaded file IDs attached to this message")
    language: Optional[str] = Field(None, description="Explicit language preference: 'en', 'ta', 'hi'")

class ExtractedMemoryItem(BaseModel):
    key: str
    value: str
    category: str
    importance: Optional[str] = "normal"

class ChatResponse(BaseModel):
    conversation_id: str
    user_message: MessageResponse
    assistant_message: MessageResponse
    response: Optional[str] = None
    language: str = "en"
    detected_language: str = "en"
    memory_used: bool = False
    voice_enabled: bool = True
    extracted_memories: List[ExtractedMemoryItem] = []
    robot_state: str = "HAPPY"

class RegenerateRequest(BaseModel):
    conversation_id: str = Field(..., description="ID of conversation to regenerate response in")
    message_id: Optional[str] = Field(None, description="Specific assistant message ID to regenerate, or last if omitted")
    language: Optional[str] = Field(None, description="Explicit language preference: 'en', 'ta', 'hi'")

class MessageFeedbackRequest(BaseModel):
    message_id: str = Field(..., description="ID of assistant message to give feedback on")
    feedback: Optional[str] = Field(None, description="'like', 'dislike', or null to clear")

class MessageFeedbackResponse(BaseModel):
    message_id: str
    feedback: Optional[str]
    message: str = "Thanks for your feedback."

class ContextUsageInfo(BaseModel):
    current_messages: int
    max_messages: int

class MemoryDebuggerResponse(BaseModel):
    llm_provider: str
    model_name: str
    context_usage: ContextUsageInfo
    system_prompt_loaded: bool
    system_prompt: str
    user_preferences: dict
    memories: List[dict]
    conversation_summary: Optional[str] = None
    keywords: List[str] = []
    file_context: Optional[str] = None
    recent_messages: List[dict] = []
    final_context: str

