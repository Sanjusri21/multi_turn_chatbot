from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.conversation_service import ConversationService
from app.schemas.conversation_schema import (
    ConversationResponse,
    ConversationDetailResponse,
    ConversationCreate,
    ConversationUpdate
)
from app.schemas.chat_schema import MessageResponse

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("", response_model=List[ConversationResponse])
def get_conversations(
    q: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ConversationService(db)
    if q and q.strip():
        return service.search_conversations(user_id=current_user.id, query=q)
    return service.list_conversations(user_id=current_user.id)

@router.get("/search", response_model=List[ConversationResponse])
def search_conversations_endpoint(
    q: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ConversationService(db)
    return service.search_conversations(user_id=current_user.id, query=q)

@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ConversationService(db)
    return service.create_conversation(user_id=current_user.id, title=payload.title)

@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation_detail(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ConversationService(db)
    conv = service.get_conversation(conversation_id, user_id=current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    messages = [MessageResponse.model_validate(m) for m in conv.messages]
    return ConversationDetailResponse(
        id=conv.id,
        title=conv.title,
        summary=conv.summary,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=messages
    )

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ConversationService(db)
    conv = service.get_conversation(conversation_id, user_id=current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return [MessageResponse.model_validate(m) for m in conv.messages]

@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ConversationService(db)
    updated = service.update_conversation(conversation_id, user_id=current_user.id, title=payload.title)
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return updated

@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ConversationService(db)
    success = service.delete_conversation(conversation_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"message": "Conversation deleted successfully"}
