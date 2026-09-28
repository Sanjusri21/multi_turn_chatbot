import pytest
import os
from unittest.mock import patch
from app.services.llm_service import LLMService, ConfigurationError, GeminiLLMProvider
from app.core.config import settings

def test_gemini_raises_configuration_error_when_key_missing():
    # Simulate non-test environment with LLM_PROVIDER="gemini" and GEMINI_API_KEY=""
    with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": ""}):
        with patch.object(settings, "LLM_PROVIDER", "gemini"):
            with patch.object(settings, "GEMINI_API_KEY", ""):
                with pytest.raises(ConfigurationError) as exc_info:
                    service = LLMService()
                    service._resolve_provider()
                assert "Gemini API is not configured. Please add GEMINI_API_KEY to backend/.env." in str(exc_info.value)

def test_gemini_provider_initialization_with_key():
    with patch.object(settings, "GEMINI_API_KEY", "test-dummy-api-key"):
        provider = GeminiLLMProvider(api_key="test-dummy-api-key")
        assert provider.model_name == settings.MODEL_NAME
