import time
from typing import List, Dict, Any, Optional, Iterator, Callable, Tuple
from app.core.config import settings
from app.core.logging_config import logger
from app.services.llm_service import (
    BaseLLMProvider,
    LLMProviderError,
    LLMQuotaExhaustedError,
    LLMServiceUnavailableError,
    ConfigurationError
)

class LLMRouter:
    """
    Failover routing engine for LLM providers.
    - PRIMARY: Google Gemini
    - FALLBACK: xAI Grok (when Gemini encounters quota/rate-limit or service errors)
    """

    def __init__(
        self,
        primary_provider: Optional[BaseLLMProvider] = None,
        fallback_provider: Optional[BaseLLMProvider] = None,
        primary_name: str = "gemini",
        fallback_name: str = "grok",
        primary: Optional[BaseLLMProvider] = None,
        fallback: Optional[BaseLLMProvider] = None,
    ):
        self.primary_provider = primary_provider or primary
        self.fallback_provider = fallback_provider or fallback
        self.primary_name = primary_name
        self.fallback_name = fallback_name
        self.last_provider_used: str = primary_name

    def has_fallback(self) -> bool:
        """Returns True if a secondary fallback provider is active and configured."""
        return self.fallback_provider is not None

    @staticmethod
    def is_fallback_safe(error: Exception) -> bool:
        """
        Determines if an error is a provider-side failure eligible for Grok fallback.
        Application bugs, schema validation errors, and programming errors must NEVER trigger fallback.
        """
        # Exclude client/application programming bugs
        if isinstance(error, (TypeError, ValueError, KeyError, AttributeError, IndexError, NotImplementedError)):
            return False

        # Explicit provider error categories
        if isinstance(error, (LLMQuotaExhaustedError, LLMServiceUnavailableError)):
            return True

        # Timeout & Network connection errors
        if isinstance(error, (TimeoutError, ConnectionError)):
            return True

        # Provider errors representing upstream HTTP or network issues
        if isinstance(error, LLMProviderError):
            err_str = str(error).lower()
            transient_tokens = [
                "429", "503", "502", "504", "quota", "resource_exhausted",
                "unavailable", "timeout", "timed out", "connection",
                "network", "couldn't reach", "reach the ai service", "bad gateway"
            ]
            if any(token in err_str for token in transient_tokens):
                return True

        # Configuration error on primary provider (e.g. missing Gemini key) is fallback-safe if Grok is available
        if isinstance(error, ConfigurationError):
            return True

        return False

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Executes generation on Primary (Gemini) with automatic failover to Fallback (Grok).
        """
        logger.info(f"[LLM ROUTER] Primary provider: {self.primary_name.capitalize()}")

        try:
            response = self.primary_provider.generate(
                messages=messages,
                temperature=temperature,
                images=images
            )
            logger.info(f"[LLM ROUTER] {self.primary_name.capitalize()} response successful")
            self.last_provider_used = self.primary_name
            return response

        except Exception as primary_error:
            # Check if fallback is configured and error is safe for failover
            if not self.has_fallback():
                logger.error(f"[LLM ROUTER] {self.primary_name.capitalize()} failed and no fallback provider is configured: {primary_error}")
                raise primary_error

            if not self.is_fallback_safe(primary_error):
                logger.error(f"[LLM ROUTER] Error is not fallback-safe ({type(primary_error).__name__}): {primary_error}")
                raise primary_error

            # Classify error message for logging
            if isinstance(primary_error, LLMQuotaExhaustedError) or "429" in str(primary_error) or "quota" in str(primary_error).lower():
                logger.warning(f"[LLM ROUTER] {self.primary_name.capitalize()} failed with 429 quota exhaustion")
                logger.info(f"[LLM ROUTER] Attempting fallback provider: {self.fallback_name.capitalize()}")
            elif isinstance(primary_error, LLMServiceUnavailableError) or "503" in str(primary_error):
                logger.warning(f"[LLM ROUTER] {self.primary_name.capitalize()} service unavailable; attempting {self.fallback_name.capitalize()} fallback")
            else:
                logger.warning(f"[LLM ROUTER] {self.primary_name.capitalize()} provider failure ({primary_error}); attempting {self.fallback_name.capitalize()} fallback")

            # Execute on fallback provider
            try:
                fallback_response = self.fallback_provider.generate(
                    messages=messages,
                    temperature=temperature,
                    images=images
                )
                logger.info(f"[LLM ROUTER] Fallback successful: {self.fallback_name.capitalize()}")
                self.last_provider_used = self.fallback_name
                return fallback_response

            except Exception as fallback_error:
                logger.error(f"[LLM ROUTER] {self.primary_name.capitalize()} and {self.fallback_name.capitalize()} providers unavailable. Grok error: {fallback_error}")
                if isinstance(primary_error, LLMQuotaExhaustedError) and isinstance(fallback_error, LLMQuotaExhaustedError):
                    raise LLMQuotaExhaustedError(
                        "Zara is temporarily unavailable. Both Gemini and Grok API quotas have been exhausted. Please try again shortly."
                    )
                raise LLMServiceUnavailableError(
                    "Zara is temporarily unavailable. Both AI providers are currently unavailable. Please try again shortly."
                )

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        images: Optional[List[Dict[str, Any]]] = None,
        on_fallback: Optional[Callable[[str, str], None]] = None
    ) -> Iterator[str]:
        """
        Executes streaming generation on Primary (Gemini).
        If Gemini fails BEFORE any content is yielded, seamlessly fails over to Grok.
        If Gemini fails AFTER content is yielded, terminates cleanly without duplicate output.
        """
        logger.info(f"[LLM ROUTER] Primary provider: {self.primary_name.capitalize()}")
        has_emitted_content = False

        try:
            primary_iter = self.primary_provider.generate_stream(
                messages=messages,
                temperature=temperature,
                images=images
            )
            for chunk in primary_iter:
                if chunk:
                    if chunk.strip():
                        has_emitted_content = True
                    self.last_provider_used = self.primary_name
                    yield chunk
            return

        except Exception as primary_error:
            # If content was already emitted, do NOT fallback to avoid duplicating or corrupting stream
            if has_emitted_content:
                logger.error(f"[LLM ROUTER] {self.primary_name.capitalize()} stream interrupted after partial output: {primary_error}")
                raise primary_error

            if not self.has_fallback():
                logger.error(f"[LLM ROUTER] {self.primary_name.capitalize()} stream failed and no fallback provider is configured: {primary_error}")
                raise primary_error

            if not self.is_fallback_safe(primary_error):
                logger.error(f"[LLM ROUTER] Stream error is not fallback-safe: {primary_error}")
                raise primary_error

            if isinstance(primary_error, LLMQuotaExhaustedError) or "429" in str(primary_error) or "quota" in str(primary_error).lower():
                logger.warning(f"[LLM ROUTER] {self.primary_name.capitalize()} failed with 429 quota exhaustion")
            elif isinstance(primary_error, LLMServiceUnavailableError) or "503" in str(primary_error):
                logger.warning(f"[LLM ROUTER] {self.primary_name.capitalize()} service unavailable; attempting {self.fallback_name.capitalize()} fallback")
            else:
                logger.warning(f"[LLM ROUTER] {self.primary_name.capitalize()} stream failed before output: {primary_error}")

            logger.info(f"[LLM ROUTER] Attempting fallback provider: {self.fallback_name.capitalize()}")

            # Notify caller of fallback event (e.g. for SSE status emission)
            if on_fallback:
                try:
                    on_fallback(self.primary_name, self.fallback_name)
                except TypeError:
                    try:
                        on_fallback({"from": self.primary_name, "to": self.fallback_name})
                    except Exception as notify_err:
                        logger.warning(f"Error in on_fallback notification: {notify_err}")
                except Exception as notify_err:
                    logger.warning(f"Error in on_fallback notification: {notify_err}")

            # Stream from fallback provider
            try:
                fallback_iter = self.fallback_provider.generate_stream(
                    messages=messages,
                    temperature=temperature,
                    images=images
                )
                self.last_provider_used = self.fallback_name
                for chunk in fallback_iter:
                    if chunk:
                        yield chunk
                logger.info(f"[LLM ROUTER] Fallback successful: {self.fallback_name.capitalize()}")
                return

            except Exception as fallback_error:
                logger.error(f"[LLM ROUTER] Both {self.primary_name.capitalize()} and {self.fallback_name.capitalize()} stream providers failed. Grok error: {fallback_error}")
                if isinstance(primary_error, LLMQuotaExhaustedError) and isinstance(fallback_error, LLMQuotaExhaustedError):
                    raise LLMQuotaExhaustedError(
                        "Zara is temporarily unavailable. Both Gemini and Grok API quotas have been exhausted. Please try again shortly."
                    )
                raise LLMServiceUnavailableError(
                    "Zara is temporarily unavailable. Both AI providers are currently unavailable. Please try again shortly."
                )
