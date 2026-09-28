from pydantic import BaseModel, Field
from typing import Optional

class SettingsResponse(BaseModel):
    language: str = "en"
    response_style: str = "balanced"
    enter_behavior: str = "send"
    theme: str = "dark"
    accent_style: str = "blue_violet"
    animations_enabled: bool = True
    memory_enabled: bool = True
    auto_save_memory: bool = True

    class Config:
        from_attributes = True

class SettingsUpdateRequest(BaseModel):
    language: Optional[str] = None
    response_style: Optional[str] = None
    enter_behavior: Optional[str] = None
    theme: Optional[str] = None
    accent_style: Optional[str] = None
    animations_enabled: Optional[bool] = None
    memory_enabled: Optional[bool] = None
    auto_save_memory: Optional[bool] = None
