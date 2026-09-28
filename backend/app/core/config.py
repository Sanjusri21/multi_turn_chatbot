import os
from typing import Optional, List
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# Candidate .env locations to search
candidate_env_files = [
    BASE_DIR / ".env",
    PROJECT_ROOT / "backend" / ".env",
    PROJECT_ROOT / ".env",
    Path(".env").resolve(),
    Path("backend/.env").resolve(),
]

env_files_to_load = []
for p in candidate_env_files:
    if p.exists() and p.is_file():
        p_resolved = p.resolve()
        p_str = str(p_resolved)
        if p_str not in env_files_to_load:
            env_files_to_load.append(p_str)
            load_dotenv(dotenv_path=p_resolved, override=True)

if not env_files_to_load:
    env_files_to_load = [str((BASE_DIR / ".env").resolve())]

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

    def model_post_init(self, __context):
        # Direct fallback from loaded .env files if empty
        if not self.GEMINI_API_KEY:
            for env_path_str in env_files_to_load:
                env_p = Path(env_path_str)
                if env_p.exists() and env_p.is_file():
                    from dotenv import dotenv_values
                    vals = dotenv_values(env_p)
                    if vals.get("GEMINI_API_KEY"):
                        self.GEMINI_API_KEY = vals["GEMINI_API_KEY"]
                        break

        # Fallback to os.environ if still empty
        if not self.GEMINI_API_KEY and os.environ.get("GEMINI_API_KEY"):
            self.GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

        # Strip any extraneous quotes or surrounding whitespace
        if self.GEMINI_API_KEY:
            self.GEMINI_API_KEY = self.GEMINI_API_KEY.strip().strip("'").strip('"')

        if not self.OPENAI_API_KEY:
            for env_path_str in env_files_to_load:
                env_p = Path(env_path_str)
                if env_p.exists() and env_p.is_file():
                    from dotenv import dotenv_values
                    vals = dotenv_values(env_p)
                    if vals.get("OPENAI_API_KEY"):
                        self.OPENAI_API_KEY = vals["OPENAI_API_KEY"]
                        break

        if not self.OPENAI_API_KEY and os.environ.get("OPENAI_API_KEY"):
            self.OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
        if self.OPENAI_API_KEY:
            self.OPENAI_API_KEY = self.OPENAI_API_KEY.strip().strip("'").strip('"')

    model_config = SettingsConfigDict(
        env_file=tuple(env_files_to_load),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()