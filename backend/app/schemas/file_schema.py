from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class AttachmentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    file_size: int
    file_url: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class FileUploadResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    file_size: int
    size: Optional[int] = None
    file_url: str
    extracted_preview: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

