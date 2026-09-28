from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.user_settings import UserSettings

class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(self, user_id: str) -> Optional[UserSettings]:
        return self.db.query(UserSettings).filter(UserSettings.user_id == user_id).first()

    def get_or_create(self, user_id: str) -> UserSettings:
        settings = self.get_by_user_id(user_id)
        if not settings:
            try:
                settings = UserSettings(user_id=user_id)
                self.db.add(settings)
                self.db.commit()
                self.db.refresh(settings)
            except Exception:
                self.db.rollback()
                settings = self.get_by_user_id(user_id)
        return settings

    def update(self, user_id: str, updates: Optional[Dict[str, Any]] = None, **kwargs) -> UserSettings:
        settings = self.get_or_create(user_id)
        merged = {}
        if updates:
            merged.update(updates)
        if kwargs:
            merged.update(kwargs)
        for key, value in merged.items():
            if value is not None and hasattr(settings, key):
                setattr(settings, key, value)
        self.db.commit()
        self.db.refresh(settings)
        return settings

