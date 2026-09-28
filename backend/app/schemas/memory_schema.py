from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class MemoryBase(BaseModel):
    key: str = Field(..., max_length=100, description="Memory identifier key, e.g. 'name', 'field_of_study'")
    value: str = Field(..., description="Memory factual content")
    category: str = Field("other", description="Category: identity, preference, interest, education, skill, goal, other")
    memory_type: Optional[str] = Field(None, description="Alias for category")
    memory_text: Optional[str] = Field(None, description="Descriptive sentence of the memory fact")
    importance: Optional[str] = Field("normal", description="Importance level: low, normal, high")

class MemoryCreate(MemoryBase):
    conversation_id: Optional[str] = None
    source_conversation_id: Optional[str] = None

class MemoryUpdate(BaseModel):
    key: Optional[str] = Field(None, max_length=100)
    value: Optional[str] = None
    category: Optional[str] = None
    memory_type: Optional[str] = None
    memory_text: Optional[str] = None
    importance: Optional[str] = None

class MemoryResponse(MemoryBase):
    id: str
    memory_id: Optional[str] = None
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    source_conversation_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

