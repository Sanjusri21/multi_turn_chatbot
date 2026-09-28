from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.repositories.user_repository import UserRepository
from app.repositories.settings_repository import SettingsRepository
from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.auth_schema import UserSignupRequest, UserLoginRequest, TokenResponse, UserResponse
from app.models.user import User

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.settings_repo = SettingsRepository(db)

    def signup(self, data: UserSignupRequest) -> TokenResponse:
        existing = self.user_repo.get_by_email(data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists."
            )

        hashed_pw = hash_password(data.password)
        user = self.user_repo.create(
            name=data.name,
            email=data.email,
            hashed_password=hashed_pw
        )

        # Initialize default user settings
        self.settings_repo.get_or_create(user.id)

        token = create_access_token(data={"sub": user.id, "email": user.email})
        return TokenResponse(
            access_token=token,
            user=UserResponse.model_validate(user)
        )

    def login(self, data: UserLoginRequest) -> TokenResponse:
        user = self.user_repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        token = create_access_token(data={"sub": user.id, "email": user.email})
        return TokenResponse(
            access_token=token,
            user=UserResponse.model_validate(user)
        )

    def change_password(self, user_id: str, current_pw: str, new_pw: str) -> bool:
        user = self.user_repo.get_by_id(user_id)
        if not user or not verify_password(current_pw, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect."
            )

        new_hashed = hash_password(new_pw)
        return self.user_repo.update_password(user_id, new_hashed)

    def delete_account(self, user_id: str) -> bool:
        return self.user_repo.delete(user_id)
