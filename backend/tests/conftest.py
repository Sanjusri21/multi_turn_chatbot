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
from app.services.llm_service import MockLLMProvider, LLMService
from app.services.auth_service import AuthService
from app.schemas.auth_schema import UserSignupRequest

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
    return token_resp.user
