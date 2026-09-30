from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_approved_user
from app.models.user import User
from app.repositories.settings_repository import SettingsRepository
from app.schemas.settings_schema import SettingsResponse, SettingsUpdateRequest

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("", response_model=SettingsResponse)
def get_settings(current_user: User = Depends(get_current_approved_user), db: Session = Depends(get_db)):
    repo = SettingsRepository(db)
    settings = repo.get_or_create(current_user.id)
    return SettingsResponse.model_validate(settings)

@router.patch("", response_model=SettingsResponse)
def update_settings(data: SettingsUpdateRequest, current_user: User = Depends(get_current_approved_user), db: Session = Depends(get_db)):
    repo = SettingsRepository(db)
    updates = data.model_dump(exclude_unset=True)
    settings = repo.update(current_user.id, updates)
    return SettingsResponse.model_validate(settings)
