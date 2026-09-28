from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.auth_service import AuthService
from app.schemas.auth_schema import (
    UserSignupRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    PasswordChangeRequest
)
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(data: UserSignupRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.signup(data)

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(data: UserLoginRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.login(data)

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Logged out successfully."}

@router.post("/change-password")
def change_password(data: PasswordChangeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = AuthService(db)
    service.change_password(current_user.id, data.current_password, data.new_password)
    return {"message": "Password updated successfully."}

@router.delete("/account")
def delete_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = AuthService(db)
    service.delete_account(current_user.id)
    return {"message": "Account deleted successfully."}
