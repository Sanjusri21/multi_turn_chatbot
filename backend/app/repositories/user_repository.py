from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.user import User

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email.strip().lower()).first()

    def create(
        self,
        name: str,
        email: str,
        hashed_password: str,
        role: str = "USER",
        account_status: str = "PENDING"
    ) -> User:
        user = User(
            name=name.strip(),
            email=email.strip().lower(),
            hashed_password=hashed_password,
            role=role,
            account_status=account_status
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_all(self, status: Optional[str] = None) -> List[User]:
        query = self.db.query(User)
        if status:
            query = query.filter(User.account_status == status.upper())
        return query.order_by(User.created_at.desc()).all()

    def get_pending(self) -> List[User]:
        return self.db.query(User).filter(User.account_status == "PENDING").order_by(User.created_at.asc()).all()

    def update_status(
        self,
        user_id: str,
        status: str,
        approved_by: Optional[str] = None
    ) -> Optional[User]:
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.account_status = status.upper()
        if status.upper() == "APPROVED":
            user.approved_at = datetime.now(timezone.utc)
            user.approved_by = approved_by
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_password(self, user_id: str, new_hashed_password: str) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            return False
        user.hashed_password = new_hashed_password
        self.db.commit()
        return True

    def delete(self, user_id: str) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            return False
        self.db.delete(user)
        self.db.commit()
        return True
