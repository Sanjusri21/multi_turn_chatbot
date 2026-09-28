from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.memory_service import MemoryService
from app.schemas.memory_schema import MemoryResponse, MemoryCreate, MemoryUpdate

router = APIRouter(prefix="/memories", tags=["Memories"])

@router.get("", response_model=List[MemoryResponse])
def get_memories(
    category: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = MemoryService(db)
    if query:
        return service.retrieve_relevant_memories(current_user.id, query)
    if category and category.upper() != "ALL":
        return service.list_by_category(current_user.id, category)
    return service.list_all_memories(current_user.id)

@router.get("/relevant", response_model=List[MemoryResponse])
def get_relevant_memories(
    query: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = MemoryService(db)
    return service.retrieve_relevant_memories(current_user.id, query)

@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
def create_memory(
    payload: MemoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = MemoryService(db)
    return service.create_memory(
        user_id=current_user.id,
        key=payload.key,
        value=payload.value,
        category=payload.category,
        conversation_id=payload.conversation_id,
        source_conversation_id=payload.source_conversation_id,
        memory_text=payload.memory_text,
        importance=payload.importance or "normal"
    )

@router.put("/{memory_id}", response_model=MemoryResponse)
@router.patch("/{memory_id}", response_model=MemoryResponse)
def update_memory(
    memory_id: str,
    payload: MemoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = MemoryService(db)
    cat = payload.category or payload.memory_type
    updated = service.update_memory(
        memory_id=memory_id,
        user_id=current_user.id,
        key=payload.key,
        value=payload.value,
        category=cat,
        memory_text=payload.memory_text,
        importance=payload.importance
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Memory item not found.")
    return updated

@router.delete("/{memory_id}", status_code=status.HTTP_200_OK)
def delete_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = MemoryService(db)
    success = service.delete_memory(memory_id=memory_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory item not found.")
    return {"message": "Memory deleted successfully."}

@router.delete("", status_code=status.HTTP_200_OK)
def clear_all_memories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = MemoryService(db)
    count = service.clear_all_memories(user_id=current_user.id)
    return {"message": f"Cleared {count} persistent memories."}
