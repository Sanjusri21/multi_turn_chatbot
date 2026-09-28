import base64
import time
from typing import List, Dict, Any, Optional, Iterator
from app.core.logging_config import logger
from app.services.llm_service import (
    BaseLLMProvider,
    LLMProviderError,
    LLMQuotaExhaustedError,
    LLMServiceUnavailableError,
    ConfigurationError
)

class GrokLLMProvider(BaseLLMProvider):
    """
    Dedicated LLM provider for Grok / xAI using the official OpenAI-compatible API format.
    Also supports Groq Cloud (gsk_ keys) automatically as a drop-in high-speed fallback provider.
    Used as an automatic failover provider when Gemini is unavailable or rate/quota exhausted.
    """
    def __init__(
        self,
        api_key: str,
        model_name: str = "grok-4.1-fast",
        base_url: str = "https://api.x.ai/v1",
        timeout: float = 30.0
    ):
        self.api_key = (api_key or "").strip()
        self.timeout = timeout

        clean_base = (base_url or "").rstrip("/")

        # Detect Groq Cloud key vs xAI key:
        # If user provides a Groq key (gsk_...) with default xAI base URL, auto-route to Groq Cloud endpoint
        if self.api_key.startswith("gsk_") and "api.x.ai" in clean_base:
            logger.info("[Grok Provider] Detected Groq Cloud API key (gsk_...). Auto-routing base_url to https://api.groq.com/openai/v1")
            clean_base = "https://api.groq.com/openai/v1"
            if model_name.startswith("grok"):
                model_name = "qwen/qwen3.8-27b"

        self.base_url = clean_base
        self.model_name = model_name

    def _get_candidates(self) -> List[str]:
        """Returns candidate models to try in case of model-not-found / deprecation errors."""
        candidates = [self.model_name]
        if "groq.com" in self.base_url or self.api_key.startswith("gsk_"):
            for alt in ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "allam-2-7b"]:
                if alt not in candidates:
                    candidates.append(alt)
        else:
            for alt in ["grok-4.1-fast", "grok-2-latest", "grok-beta"]:
                if alt not in candidates:
                    candidates.append(alt)
        return candidates

    def _format_messages(
        self,
        messages: List[Dict[str, str]],
        images: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Formats standard message dictionaries into OpenAI-compatible format with multimodal support."""
        formatted_messages = []
        total_msgs = len(messages)

        for i, m in enumerate(messages):
            role = m.get("role", "user")
            content = m.get("content", "")

            # Multimodal payload on the last user message if images are attached
            if role == "user" and i == total_msgs - 1 and images:
                content_list: List[Dict[str, Any]] = [{"type": "text", "text": content}]
                for img in images:
                    b64 = base64.b64encode(img["bytes"]).decode("utf-8")
                    content_list.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{img.get('mime_type', 'image/jpeg')};base64,{b64}"
                        }
                    })
                formatted_messages.append({"role": "user", "content": content_list})
            else:
                formatted_messages.append({"role": role, "content": content})

        return formatted_messages

    @staticmethod
    def _classify_error(error: Exception, model: str) -> None:
        """Classifies Grok/xAI API exceptions and raises appropriate semantic error types."""
        err_str = str(error).lower()
        code = getattr(error, "status_code", None) or getattr(error, "code", None)

        # 1. Authentication / Permission errors (401, 403, 400 invalid argument)
        if code in (401, 403) or any(k in err_str for k in ["api_key_invalid", "unauthorized", "forbidden", "invalid api key", "incorrect api key"]):
            logger.error(f"[Grok] Authentication failure on model '{model}': {error}")
            raise ConfigurationError("Backup AI provider authentication failed. Please verify your XAI_API_KEY in backend/.env.")

        # 2. Rate limit / Quota exhaustion (429)
        if code == 429 or any(k in err_str for k in ["429", "rate limit", "ratelimit", "quota", "resource_exhausted"]):
            logger.error(f"[Grok] Quota/Rate limit exceeded on model '{model}': {error}")
            raise LLMQuotaExhaustedError("Backup AI provider API quota or rate limit exceeded.")

        # 3. Service Unavailable / Overloaded (502, 503, 504, timeout)
        if code in (502, 503, 504) or any(k in err_str for k in ["503", "502", "504", "unavailable", "overloaded", "timeout", "timed out", "bad gateway"]):
            logger.error(f"[Grok] Service unavailable on model '{model}': {error}")
            raise LLMServiceUnavailableError("Backup AI provider service is temporarily unavailable due to high demand or timeout.")

        # 4. General fallback failure
        logger.error(f"[Grok] Unhandled API error on model '{model}': {error}")
        raise LLMProviderError(f"Backup AI provider API error: {error}")

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Executes a synchronous completion request to Grok with error classification."""
        from openai import OpenAI

        logger.info("[GROK] Request started")
        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
        formatted_messages = self._format_messages(messages, images)
        candidates = self._get_candidates()
        last_error = None

        for model in candidates:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=formatted_messages,
                    temperature=temperature
                )
                if not response.choices or not response.choices[0].message:
                    raise LLMProviderError("Backup AI provider returned an empty response.")

                content = response.choices[0].message.content or ""
                if not content.strip():
                    raise LLMProviderError("Backup AI provider returned a blank completion.")

                logger.info("[GROK] Response received successfully")
                return content

            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                code = getattr(e, "status_code", None) or getattr(e, "code", None)

                # If model not found (404), try next candidate
                if code == 404 or "404" in err_str or "not found" in err_str or "model_terms_required" in err_str:
                    logger.warning(f"[Grok] Model '{model}' not found or unavailable; trying alternative candidate...")
                    continue

                # Otherwise, classify and raise immediately
                self._classify_error(e, model=model)

        # If all candidates exhausted with 404s
        logger.error(f"[Grok] All candidate models failed. Last error: {last_error}")
        if last_error:
            self._classify_error(last_error, model=self.model_name)
        raise LLMProviderError("Backup AI provider failed to generate a response.")

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> Iterator[str]:
        """Executes a streaming completion request to Grok with chunk delivery."""
        from openai import OpenAI

        logger.info("[GROK] Request started")
        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
        formatted_messages = self._format_messages(messages, images)
        candidates = self._get_candidates()
        last_error = None

        for model in candidates:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=formatted_messages,
                    temperature=temperature,
                    stream=True
                )
                has_yielded = False
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                        text = chunk.choices[0].delta.content
                        if not has_yielded:
                            logger.info("[GROK] Response received successfully")
                            has_yielded = True
                        yield text
                return

            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                code = getattr(e, "status_code", None) or getattr(e, "code", None)

                # If 404 on initial call before any chunks, try next candidate
                if (code == 404 or "404" in err_str or "not found" in err_str or "model_terms_required" in err_str) and not has_yielded:
                    logger.warning(f"[Grok Stream] Model '{model}' not found or unavailable; trying alternative candidate...")
                    continue

                self._classify_error(e, model=model)

        logger.error(f"[Grok Stream] All candidate models failed. Last error: {last_error}")
        if last_error:
            self._classify_error(last_error, model=self.model_name)
        raise LLMProviderError("Backup AI provider streaming failed to generate a response.")
