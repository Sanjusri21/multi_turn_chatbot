import os
import sys
from pathlib import Path
import pytest

# Ensure backend root is in PYTHONPATH
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
import app.models.user
import app.models.user_settings
import app.models.conversation
import app.models.message
import app.models.memory
import app.models.message_attachment
import app.models.message_feedback
import app.models.web_search_log
from app.services.llm_service import MockLLMProvider, LLMService
from app.services.auth_service import AuthService
from app.schemas.auth_schema import UserSignupRequest, UserResponse
from app.models.user import User

# Test SQLite in-memory database
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_db():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_llm_service():
    return LLMService(provider=MockLLMProvider())

@pytest.fixture
def test_user(test_db):
    auth_service = AuthService(test_db)
    token_resp = auth_service.signup(UserSignupRequest(
        name="Sanju",
        email="sanju@example.com",
        password="Password123!"
    ))
    # Mark standard test user as APPROVED for test fixtures
    user = test_db.query(User).filter(User.id == token_resp.user.id).first()
    user.account_status = "APPROVED"
    user.role = "USER"
    test_db.commit()
    test_db.refresh(user)
    return UserResponse.model_validate(user)

@pytest.fixture
def admin_user(test_db):
    auth_service = AuthService(test_db)
    token_resp = auth_service.signup(UserSignupRequest(
        name="Admin",
        email="admin@example.com",
        password="AdminPassword123!"
    ))
    user = test_db.query(User).filter(User.id == token_resp.user.id).first()
    user.account_status = "APPROVED"
    user.role = "ADMIN"
    test_db.commit()
    test_db.refresh(user)
    return UserResponse.model_validate(user)
