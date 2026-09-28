from pathlib import Path
from app.core.logging_config import logger

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

class PromptService:
    def __init__(self):
        self._system_prompt = self._load_prompt("system_prompt.txt")
        self._memory_prompt = self._load_prompt("memory_extraction_prompt.txt")
        self._summary_prompt = self._load_prompt("summarization_prompt.txt")

    def _load_prompt(self, filename: str) -> str:
        filepath = PROMPTS_DIR / filename
        try:
            if filepath.exists():
                return filepath.read_text(encoding="utf-8").strip()
            logger.warning(f"Prompt file {filename} not found at {filepath}")
            return ""
        except Exception as e:
            logger.error(f"Error loading prompt {filename}: {e}")
            return ""

    def get_system_prompt(self) -> str:
        return self._system_prompt

    def get_memory_extraction_prompt(self) -> str:
        return self._memory_prompt

    def get_summarization_prompt(self) -> str:
        return self._summary_prompt

prompt_service = PromptService()
