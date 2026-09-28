import os
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "MemoryBot — Multi-Turn AI Chatbot with Persistent Memory"
    VERSION: str = "2.0.0"
    DEBUG: bool = True

    # Server settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Authentication & Security
    JWT_SECRET_KEY: str = Field(
        default="memorybot-super-secure-jwt-secret-key-change-in-production-2026"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # LLM Settings
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = Field(default="")
    OPENAI_API_KEY: str = Field(default="")
    MODEL_NAME: Optional[str] = Field(default=None)
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Database
    DATABASE_URL: str = Field(
        default=f"sqlite:///{DATA_DIR / 'memorybot.db'}"
    )
    DEMO_USER_ENABLED: bool = True
    @property
    def RESOLVED_DB_PATH(self) -> Path:
        if self.DATABASE_URL.startswith("sqlite:///"):
            path_part = self.DATABASE_URL.replace("sqlite:///", "")
            p = Path(path_part)

            if not p.is_absolute():
                return (PROJECT_ROOT / path_part).resolve()

            return p.resolve()

        # PostgreSQL or another external database
        return (DATA_DIR / "memorybot.db").resolve()

    @property
    def RESOLVED_DATABASE_URL(self) -> str:
        # Production: use PostgreSQL directly
        if not self.DATABASE_URL.startswith("sqlite:///"):
            return self.DATABASE_URL

        # Local development: use SQLite
        db_path = self.RESOLVED_DB_PATH
        db_path.parent.mkdir(parents=True, exist_ok=True)

        return f"sqlite:///{db_path.as_posix()}"

    # Context window & Memory
    MAX_CONTEXT_MESSAGES: int = 20
    SUMMARY_TRIGGER_THRESHOLD: int = 14

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()