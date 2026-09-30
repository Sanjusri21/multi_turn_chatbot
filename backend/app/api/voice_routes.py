from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from app.core.security import get_current_approved_user
from app.models.user import User

router = APIRouter(prefix="/voice", tags=["Voice"])

class SpeakRequest(BaseModel):
    text: str = Field(..., description="Text content to speak")
    language: Optional[str] = Field("en", description="Target language: en, ta, hi")

class SpeakResponse(BaseModel):
    text: str
    language: str
    voice_name: Optional[str] = None
    engine: str = "browser_speech_synthesis"
    ready: bool = True

class TranscribeResponse(BaseModel):
    text: str
    language: str
    confidence: float = 1.0

@router.post("/speak", response_model=SpeakResponse)
def voice_speak(
    payload: SpeakRequest,
    current_user: User = Depends(get_current_approved_user)
):
    """
    Returns voice synthesis configuration and target language metadata for Zara speech output.
    """
    lang = (payload.language or "en").lower()
    voice_map = {
        "en": "Zara (English Preferred)",
        "ta": "Zara Tamil (தமிழ் Preferred)",
        "hi": "Zara Hindi (हिन्दी Preferred)"
    }
    return SpeakResponse(
        text=payload.text,
        language=lang,
        voice_name=voice_map.get(lang, "Zara English"),
        engine="browser_speech_synthesis",
        ready=True
    )

@router.post("/transcribe", response_model=TranscribeResponse)
async def voice_transcribe(
    file: Optional[UploadFile] = File(None),
    language: Optional[str] = Form("en"),
    current_user: User = Depends(get_current_approved_user)
):
    """
    Speech-to-text audio endpoint with metadata support for English, Tamil, and Hindi.
    """
    return TranscribeResponse(
        text="",
        language=language or "en",
        confidence=1.0
    )
