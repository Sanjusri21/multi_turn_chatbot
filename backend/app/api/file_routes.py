from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_approved_user, decode_access_token, security_bearer
from app.models.user import User
from app.services.file_service import FileService
from app.schemas.file_schema import FileUploadResponse

router = APIRouter(prefix="/files", tags=["Files"])

def get_file_view_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> User:
    raw_token = None
    if credentials and credentials.credentials:
        raw_token = credentials.credentials
    elif token:
        raw_token = token

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view files."
        )

    payload = decode_access_token(raw_token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token."
        )

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found."
        )

    if user.role != "ADMIN" and user.account_status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not approved to access files."
        )

    return user

@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_approved_user),
    db: Session = Depends(get_db)
):
    service = FileService(db)
    return await service.save_uploaded_file(file, user_id=current_user.id)

@router.get("/{file_id}/view")
def view_file(
    file_id: str,
    current_user: User = Depends(get_file_view_user),
    db: Session = Depends(get_db)
):
    service = FileService(db)
    path, filename, content_type = service.get_file_record(file_id, user_id=current_user.id)
    return FileResponse(
        path=path,
        media_type=content_type,
        filename=filename
    )
