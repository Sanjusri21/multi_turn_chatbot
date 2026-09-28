import os
import json
import re
import time
from typing import List, Dict, Any, Optional, Iterator, Callable
from abc import ABC, abstractmethod
from app.core.config import settings
from app.core.logging_config import logger
from app.services.prompt_service import prompt_service

class ConfigurationError(RuntimeError):
    """Raised when an LLM provider is misconfigured or lacks a required API key."""
    pass

class LLMProviderError(RuntimeError):
    """Raised when an external LLM API service cannot be reached or fails."""
    pass

class LLMQuotaExhaustedError(LLMProviderError):
    """Raised when the LLM provider API quota or rate limit is exhausted (e.g. HTTP 429 RESOURCE_EXHAUSTED)."""
    pass

class LLMServiceUnavailableError(LLMProviderError):
    """Raised when the external LLM service is temporarily unavailable or overloaded (e.g. HTTP 503)."""
    pass

class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        pass

    @abstractmethod
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> Iterator[str]:
        pass

class GeminiLLMProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model_name = model_name

    def _get_candidates(self) -> List[str]:
        """
        Returns the ordered list of model candidates to try.
        The configured model is always primary. Alternate models are ONLY tried for
        model-not-found / deprecation errors (HTTP 404), NEVER for quota exhaustion.
        """
        candidates = [self.model_name]
        for alt in ["gemini-2.5-flash-lite", "gemini-flash-latest"]:
            if alt not in candidates:
                candidates.append(alt)
        return candidates

    @staticmethod
    def _is_quota_error(error: Exception) -> bool:
        """
        Detects whether an error represents rate limiting or quota exhaustion (HTTP 429 / RESOURCE_EXHAUSTED).
        Quota exhaustion is project-level/account-level and should NEVER be retried or passed to other Gemini models.
        """
        code = getattr(error, "code", None) or getattr(error, "status_code", None)
        if code == 429:
            return True
        err_str = str(error).lower()
        quota_indicators = [
            "429",
            "resource_exhausted",
            "generaterequestsperday",
            "quota exceeded",
            "quota_exceeded",
            "freetier",
            "free_tier",
            "daily quota",
            "rate limit",
            "ratelimit",
            "quotavalue",
            "exhausted"
        ]
        return any(ind in err_str for ind in quota_indicators)

    @staticmethod
    def _is_transient_error(error: Exception) -> bool:
        """
        Detects whether an error represents a temporary service spike (e.g. HTTP 503 / 502 / high demand).
        Controlled retries (max 1) are appropriate for these transient issues.
        """
        code = getattr(error, "code", None) or getattr(error, "status_code", None)
        if code in (503, 502, 504):
            return True
        err_str = str(error).lower()
        transient_indicators = [
            "503",
            "service unavailable",
            "unavailable",
            "high demand",
            "temporarily overloaded",
            "server is overloaded",
            "overloaded",
            "deadline_exceeded",
            "504 gateway timeout",
            "transient"
        ]
        return any(ind in err_str for ind in transient_indicators)

    @staticmethod
    def _is_auth_error(error: Exception) -> bool:
        """
        Detects authentication or API key failures (HTTP 401 / 403 / API_KEY_INVALID).
        """
        code = getattr(error, "code", None) or getattr(error, "status_code", None)
        if code in (401, 403):
            return True
        err_str = str(error).lower()
        auth_indicators = [
            "api_key_invalid",
            "invalid api key",
            "api key not valid",
            "permission_denied",
            "unauthenticated",
            "forbidden"
        ]
        return any(ind in err_str for ind in auth_indicators)

    @staticmethod
    def _is_model_not_found_error(error: Exception) -> bool:
        """
        Detects model not found / unsupported errors (HTTP 404).
        """
        code = getattr(error, "code", None) or getattr(error, "status_code", None)
        if code == 404:
            return True
        err_str = str(error).lower()
        return "404" in err_str or "not found" in err_str or "is not supported" in err_str

    def _call_generate(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        # 1. Primary: Use modern official google-genai SDK
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            contents = []
            system_instruction = None

            total_msgs = len(messages)
            for i, msg in enumerate(messages):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    system_instruction = content
                elif role == "assistant":
                    contents.append(types.Content(role="model", parts=[types.Part.from_text(text=content)]))
                else:
                    parts = []
                    if i == total_msgs - 1 and images:
                        for img in images:
                            parts.append(types.Part.from_bytes(data=img["bytes"], mime_type=img.get("mime_type", "image/jpeg")))
                    parts.append(types.Part.from_text(text=content))
                    contents.append(types.Content(role="user", parts=parts))

            config = types.GenerateContentConfig(
                temperature=temperature,
                system_instruction=system_instruction
            )

            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            return response.text or ""

        except ImportError:
            # 2. Fallback: Use google.generativeai if google-genai is unavailable
            import google.generativeai as genai
            from PIL import Image
            import io

            genai.configure(api_key=self.api_key)
            system_instruction = None
            contents = []

            total_msgs = len(messages)
            for i, msg in enumerate(messages):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    system_instruction = content
                elif role == "assistant":
                    contents.append({"role": "model", "parts": [content]})
                else:
                    part_items = []
                    if i == total_msgs - 1 and images:
                        for img in images:
                            part_items.append(Image.open(io.BytesIO(img["bytes"])))
                    part_items.append(content)
                    contents.append({"role": "user", "parts": part_items})

            gen_model = genai.GenerativeModel(
                model,
                system_instruction=system_instruction
            ) if system_instruction else genai.GenerativeModel(model)

            gen_config = genai.types.GenerationConfig(temperature=temperature)
            response = gen_model.generate_content(contents, generation_config=gen_config)
            return response.text or ""

    def _call_generate_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> Iterator[str]:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            contents = []
            system_instruction = None

            total_msgs = len(messages)
            for i, msg in enumerate(messages):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    system_instruction = content
                elif role == "assistant":
                    contents.append(types.Content(role="model", parts=[types.Part.from_text(text=content)]))
                else:
                    parts = []
                    if i == total_msgs - 1 and images:
                        for img in images:
                            parts.append(types.Part.from_bytes(data=img["bytes"], mime_type=img.get("mime_type", "image/jpeg")))
                    parts.append(types.Part.from_text(text=content))
                    contents.append(types.Content(role="user", parts=parts))

            config = types.GenerateContentConfig(
                temperature=temperature,
                system_instruction=system_instruction
            )

            response = client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except ImportError:
            import google.generativeai as genai
            from PIL import Image
            import io

            genai.configure(api_key=self.api_key)
            system_instruction = None
            contents = []

            total_msgs = len(messages)
            for i, msg in enumerate(messages):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    system_instruction = content
                elif role == "assistant":
                    contents.append({"role": "model", "parts": [content]})
                else:
                    part_items = []
                    if i == total_msgs - 1 and images:
                        for img in images:
                            part_items.append(Image.open(io.BytesIO(img["bytes"])))
                    part_items.append(content)
                    contents.append({"role": "user", "parts": part_items})

            gen_model = genai.GenerativeModel(
                model,
                system_instruction=system_instruction
            ) if system_instruction else genai.GenerativeModel(model)

            gen_config = genai.types.GenerationConfig(temperature=temperature)
            response = gen_model.generate_content(contents, generation_config=gen_config, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        candidates = self._get_candidates()
        last_error = None

        for model_idx, model_candidate in enumerate(candidates):
            for attempt in range(2):
                try:
                    return self._call_generate(
                        model=model_candidate,
                        messages=messages,
                        temperature=temperature,
                        images=images
                    )
                except Exception as e:
                    last_error = e

                    # 1. Quota exhaustion: NEVER retry, NEVER switch models
                    if self._is_quota_error(e):
                        logger.error(
                            f"Gemini API quota exhausted (HTTP 429) on model '{model_candidate}': {e}. "
                            f"Aborting immediately without retry or model switching."
                        )
                        raise LLMQuotaExhaustedError(
                            "Zara is temporarily unavailable because the Gemini API quota has been exhausted. Please try again after the quota resets."
                        )

                    # 2. Authentication failure: do not retry
                    if self._is_auth_error(e):
                        logger.error(f"Gemini API authentication failed on model '{model_candidate}': {e}")
                        raise ConfigurationError("Gemini API authentication failed. Please check your GEMINI_API_KEY.")

                    # 3. Transient service issue (503 / high demand): max 1 retry with backoff
                    if self._is_transient_error(e):
                        if attempt == 0:
                            logger.warning(
                                f"Gemini model '{model_candidate}' transient demand spike (attempt 1): {e}. "
                                f"Backing off 1.5s before 1 retry..."
                            )
                            time.sleep(1.5)
                            continue
                        logger.warning(
                            f"Gemini model '{model_candidate}' service unavailable after retry (attempt 2): {e}"
                        )
                        break

                    # 4. Model not found / unsupported (404): try next candidate
                    if self._is_model_not_found_error(e):
                        logger.warning(f"Gemini model '{model_candidate}' not found (404), checking alternate candidate...")
                        break

                    # 5. Other unrecoverable error
                    logger.error(f"Gemini API failure on model '{model_candidate}': {e}")
                    raise LLMProviderError("Zara couldn't reach the AI service. Please check your connection or try again.")

        if last_error and self._is_transient_error(last_error):
            raise LLMServiceUnavailableError("Zara is temporarily unavailable due to high demand on the AI service. Please try again in a moment.")

        logger.error(f"All Gemini candidates failed. Last error: {last_error}")
        raise LLMProviderError("Zara couldn't reach the AI service. Please check your connection or try again.")

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> Iterator[str]:
        candidates = self._get_candidates()
        last_error = None

        for model_idx, model_candidate in enumerate(candidates):
            for attempt in range(2):
                has_yielded = False
                try:
                    for chunk in self._call_generate_stream(
                        model=model_candidate,
                        messages=messages,
                        temperature=temperature,
                        images=images
                    ):
                        has_yielded = True
                        yield chunk
                    return

                except Exception as e:
                    last_error = e

                    # 1. Quota exhaustion: NEVER retry, NEVER switch models
                    if self._is_quota_error(e):
                        logger.error(
                            f"Gemini stream API quota exhausted (HTTP 429) on model '{model_candidate}': {e}. "
                            f"Aborting stream immediately without retry or model switching."
                        )
                        raise LLMQuotaExhaustedError(
                            "Zara is temporarily unavailable because the Gemini API quota has been exhausted. Please try again after the quota resets."
                        )

                    # 2. Authentication failure: do not retry
                    if self._is_auth_error(e):
                        logger.error(f"Gemini stream authentication failed on model '{model_candidate}': {e}")
                        raise ConfigurationError("Gemini API authentication failed. Please check your GEMINI_API_KEY.")

                    # If chunks were already emitted to client, retrying would emit duplicate content. Raise immediately.
                    if has_yielded:
                        logger.error(f"Gemini stream interrupted mid-generation on model '{model_candidate}': {e}")
                        if self._is_transient_error(e):
                            raise LLMServiceUnavailableError("Zara is temporarily unavailable due to high demand on the AI service. Please try again in a moment.")
                        raise LLMProviderError("The AI response stream was interrupted. Please try again.")

                    # 3. Transient service issue (503 / high demand): max 1 retry with backoff
                    if self._is_transient_error(e):
                        if attempt == 0:
                            logger.warning(
                                f"Gemini stream model '{model_candidate}' demand spike (attempt 1): {e}. "
                                f"Backing off 1.5s before 1 retry..."
                            )
                            time.sleep(1.5)
                            continue
                        logger.warning(
                            f"Gemini stream model '{model_candidate}' unavailable after retry: {e}"
                        )
                        break

                    # 4. Model not found (404): try next candidate
                    if self._is_model_not_found_error(e):
                        logger.warning(f"Gemini stream model '{model_candidate}' not found (404), checking alternate candidate...")
                        break

                    # 5. Other unrecoverable error
                    logger.error(f"Gemini streaming failure on model '{model_candidate}': {e}")
                    raise LLMProviderError("Zara couldn't reach the AI service. Please check your connection or try again.")

        if last_error and self._is_transient_error(last_error):
            raise LLMServiceUnavailableError("Zara is temporarily unavailable due to high demand on the AI service. Please try again in a moment.")

        logger.error(f"All Gemini stream candidates failed. Last error: {last_error}")
        raise LLMProviderError("Zara couldn't reach the AI service. Please try again.")


class OpenAILLMProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model_name = model_name

    def _format_messages(self, messages: List[Dict[str, str]], images: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        import base64
        formatted_messages = []
        total_msgs = len(messages)
        for i, m in enumerate(messages):
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "user" and i == total_msgs - 1 and images:
                content_list: List[Dict[str, Any]] = [{"type": "text", "text": content}]
                for img in images:
                    b64 = base64.b64encode(img["bytes"]).decode("utf-8")
                    content_list.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{img.get('mime_type', 'image/jpeg')};base64,{b64}"}
                    })
                formatted_messages.append({"role": "user", "content": content_list})
            else:
                formatted_messages.append({"role": role, "content": content})
        return formatted_messages

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            formatted_messages = self._format_messages(messages, images)
            response = client.chat.completions.create(
                model=self.model_name,
                messages=formatted_messages,
                temperature=temperature
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI API failure: {e}")
            raise LLMProviderError("Sorry, I couldn't reach the AI service. Please try again.")

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> Iterator[str]:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            formatted_messages = self._format_messages(messages, images)
            response = client.chat.completions.create(
                model=self.model_name,
                messages=formatted_messages,
                temperature=temperature,
                stream=True
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI API stream failure: {e}")
            raise LLMProviderError("Sorry, I couldn't reach the AI service. Please try again.")

class MockLLMProvider(BaseLLMProvider):
    """
    Mock provider for automated pytest test suites and offline verification.
    """
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        last_msg = messages[-1]["content"] if messages else ""
        system_msgs = [m["content"] for m in messages if m.get("role") == "system"]
        sys_combined = " ".join(system_msgs).lower()

        # If multimodal image was attached
        if images:
            return "I analyzed the attached image. It shows a software architectural diagram illustrating database and API relationships."

        all_text = " ".join([m.get("content", "") for m in messages]) + " " + sys_combined
        lower = last_msg.lower().strip()

        # Document / Attached file queries
        if "attached file:" in all_text.lower() or "summarize this document" in lower or "what is this document about" in lower or "summarize this" in lower:
            if "first concept" in lower:
                return "The first concept is Python Basics, which covers variable assignment and data types."
            if "second concept" in lower:
                return "The second concept is Control Flow, which covers conditional logic and loops."
            if "explain that with an example" in lower:
                return "Here is an example: `x = 10` followed by `if x > 5: print('positive')`."
            return "This document provides an overview of Python programming, covering foundational syntax, functions, and best practices."

        # Check if memory extraction prompt
        if any("memory extractor" in sm.lower() for sm in system_msgs):
            memories = []
            name_match = re.search(r"\bmy name is ([A-Za-z]+)\b", last_msg, re.IGNORECASE)
            if name_match:
                memories.append({"key": "name", "value": name_match.group(1), "category": "personal", "memory_text": f"User's name is {name_match.group(1)}"})
            major_match = re.search(r"\b(?:learning|studying|student in|major in)\s+([A-Za-z0-9 &+]+?)(?:\.|$|,|\b(?:and i am|and i'm)\b)", last_msg, re.IGNORECASE)
            if major_match:
                memories.append({"key": "field_of_study", "value": major_match.group(1).strip(), "category": "education", "memory_text": f"User studies {major_match.group(1).strip()}"})
            tech_match = re.search(r"\b(?:learning|using|with)\s+([A-Za-z0-9 &+]+?(?:and [A-Za-z0-9 &+]+)?)(?:\.|$|,|\b(?:for|with)\b)", last_msg, re.IGNORECASE)
            if tech_match and "studying" not in last_msg.lower():
                memories.append({"key": "technologies", "value": tech_match.group(1).strip(), "category": "technology", "memory_text": f"User uses {tech_match.group(1).strip()}"})

            # Multilingual and updated project extraction (English, Tamil, Hindi)
            proj_match = (
                re.search(r"\b(?:project is now called|project is now|project is called|building a project called|project is)\s+([A-Za-z0-9 &+]+?)(?:\.|$|,)", last_msg, re.IGNORECASE) or
                re.search(r"(?:என்னுடைய|என்)\s+project\s+(?:பெயர்\s+)?([A-Za-z0-9 &+]+?)(?:\.|$|,|\s|$)", last_msg, re.IGNORECASE) or
                re.search(r"मेरा\s+प्रोजेक्ट\s+([A-Za-z0-9 &+]+?)(?:\s+है|\.|$|,)", last_msg, re.IGNORECASE) or
                re.search(r"\b(?:my project|project)\s+(?:name is\s+|is\s+|called\s+)([A-Za-z0-9 &+]+?)(?:\.|$|,)", last_msg, re.IGNORECASE)
            )
            if proj_match:
                proj_val = proj_match.group(1).strip()
                memories.append({
                    "key": "current_project",
                    "value": proj_val,
                    "category": "project",
                    "memory_text": f"User's project is {proj_val}",
                    "importance": "high"
                })

            hobby_match = re.search(r"\bi (like|love|enjoy)\s+([A-Za-z0-9 &+]+?)(?:\.|$|,)", last_msg, re.IGNORECASE)
            if hobby_match:
                memories.append({"key": "preference", "value": hobby_match.group(2).strip(), "category": "preference", "memory_text": f"User enjoys {hobby_match.group(2).strip()}"})
            return json.dumps(memories)

        # Check if summarization prompt
        if any("summarizer" in sm.lower() for sm in system_msgs):
            return "User Sanju is an AI & Data Science student developing MemoryBot with Python and FastAPI."

        is_tamil_directive = (
            ("[language directive - mandatory]:\nrespond in tamil" in sys_combined) or
            bool(re.search(r"[\u0B80-\u0BFF]", last_msg))
        )
        is_hindi_directive = (
            ("[language directive - mandatory]:\nrespond in hindi" in sys_combined) or
            bool(re.search(r"[\u0900-\u097F]", last_msg))
        )

        # Real-time sources handling based on retrieved web sources
        has_realtime_sources = "real-time information rule:" in sys_combined.lower() or "retrieved sources:" in sys_combined.lower()
        if has_realtime_sources:
            if is_tamil_directive:
                if "stalin" in sys_combined.lower() or "முதலமைச்சர்" in last_msg or "chief minister" in lower:
                    return "சமீபத்திய அதிகாரப்பூர்வ தகவல்களின்படி, தமிழ்நாட்டின் தற்போதைய முதலமைச்சர் திரு. மு. க. ஸ்டாலின் (M. K. Stalin) ஆவார்."
                if "python" in lower and ("version" in lower or "பதிப்பு" in last_msg):
                    return "சமீபத்திய வெளியீட்டு தகவல்களின்படி, பைதான் (Python) இன் தற்போதைய நிலையான பதிப்பு Python 3.13 ஆகும்."
                return "கிடைக்கப்பெற்ற நேரலை தகவல்களின்படி உங்கள் கேள்விக்கான தற்போதைய விவரங்கள் பெறப்பட்டு சரிபார்க்கப்பட்டன."

            if is_hindi_directive:
                if "stalin" in sys_combined.lower() or "मुख्यमंत्री" in last_msg or "chief minister" in lower:
                    return "नवीनतम आधिकारिक जानकारी के अनुसार, तमिलनाडु के वर्तमान मुख्यमंत्री एम. के. स्टालिन (M. K. Stalin) हैं।"
                if "python" in lower and ("version" in lower or "संस्करण" in last_msg):
                    return "नवीनतम जानकारी के अनुसार, पायथन (Python) का वर्तमान स्थिर संस्करण Python 3.13 है।"
                return "उपलब्ध लाइव स्रोतों के अनुसार आपकी जानकारी प्राप्त कर ली गई है।"

            if "stalin" in sys_combined.lower() or "chief minister" in lower or "cm of tamil nadu" in lower:
                return "According to current authoritative sources from the Tamil Nadu Legislative Assembly and official government portals, the current Chief Minister of Tamil Nadu is M. K. Stalin."
            if "python" in lower and ("latest" in lower or "version" in lower):
                return "According to the latest documentation from Python.org, the latest major stable release of Python is Python 3.13."
            if "headline" in lower or "news" in lower:
                return "According to the latest global news reports, key developments and top international headlines have been retrieved."
            if "weather" in lower or "temperature" in lower:
                w_match = re.search(r"Current weather in ([^:\n]+): ([^\n]+)", sys_combined)
                if w_match:
                    return f"According to current real-time meteorological reports, {w_match.group(0)}"
                return "According to current real-time meteorological reports, current weather conditions have been retrieved."
            if "bitcoin" in lower or "crypto" in lower:
                b_match = re.search(r"Current ([^:\n]+) price: ([^\n]+)", sys_combined)
                if b_match:
                    return f"According to real-time market data, {b_match.group(0)}"
                return "According to real-time market data, current cryptocurrency price information has been retrieved."

            return f"According to the latest retrieved real-time sources, current information for '{last_msg}' has been retrieved and verified."

        # Tamil greetings, project and general queries
        if is_tamil_directive:
            if any(w in last_msg for w in ["என்னுடைய project", "என் project", "project என்ன", "திட்டம் என்ன"]) or ("project" in lower and any(q in lower for q in ["what", "name", "called"])):
                if "alina" in all_text.lower():
                    return "உங்கள் project பெயர் Alina."
                if "signaura" in all_text.lower():
                    return "உங்கள் project பெயர் SignAura."
                return "உங்கள் project பெயர் SignAura."
            if "உன்னை பற்றி" in last_msg or "நீ யார்" in last_msg or "tell me about yourself" in lower or "who are you" in lower:
                return "நான் சாரா (Zara), உங்களுக்கு உதவும் ஒரு புத்திசாலித்தனமான பல மொழி AI உதவியாளர்."
            if "python" in lower:
                return "பைதான் (Python) என்பது ஒரு பிரபலமான, எளிய மற்றும் சக்திவாய்ந்த உயர்மட்ட நிரலாக்க மொழி ஆகும்."
            if "நீ எப்படி இருக்கிறாய்" in last_msg or "வணக்கம்" in last_msg:
                return "நான் நன்றாக இருக்கிறேன், நன்றி! நான் Zara. உங்களுக்கு இன்று நான் எவ்வாறு உதவ முடியும்?"
            return "வணக்கம்! நான் உங்களுக்கு எப்படி உதவ முடியும்?"

        # Hindi greetings, project and general queries
        if is_hindi_directive:
            if any(w in last_msg for w in ["मेरा प्रोजेक्ट क्या है", "मेरे प्रोजेक्ट", "प्रोजेक्ट का नाम क्या है"]) or ("project" in lower and any(q in lower for q in ["what", "name", "called"])):
                if "alina" in all_text.lower():
                    return "आपका प्रोजेक्ट Alina है।"
                if "signaura" in all_text.lower():
                    return "आपका प्रोजेक्ट SignAura है।"
                return "आपका प्रोजेक्ट SignAura है।"
            if "अपने बारे में" in last_msg or "tell me about yourself" in lower or "who are you" in lower:
                return "मैं ज़ारा (Zara) हूँ, एक बुद्धिमान और बहुभाषी AI सहायक।"
            if "python" in lower:
                return "पायथन (Python) एक उच्च-स्तरीय, बहुत लोकप्रिय और बहुमुखी प्रोग्रामिंग भाषा है।"
            if "आप कैसे हैं" in last_msg or "नमस्ते" in last_msg:
                return "मैं ठीक हूँ, धन्यवाद! मैं ज़ारा (Zara) हूँ। आज मैं आपकी क्या मदद कर सकती हूँ?"
            return "नमस्ते! मैं आपकी कैसे मदद कर सकता हूँ?"

        # "What do you remember about me?" (Requirement 8)
        if "what do you remember about me" in lower or "what do you know about me" in lower:
            facts = []
            if "sanju" in all_text.lower():
                facts.append("your name is Sanju")
            if "ai and data science" in all_text.lower():
                facts.append("you're studying AI & Data Science")
            if "signaura" in all_text.lower():
                facts.append("your project is SignAura")
            elif "alina" in all_text.lower():
                facts.append("your project is Alina")
            elif "memorybot" in all_text.lower():
                facts.append("your project is MemoryBot")
            if "python" in all_text.lower() and "fastapi" in all_text.lower():
                facts.append("you're learning Python and FastAPI")
            elif "python" in all_text.lower():
                facts.append("you're learning Python")

            if facts:
                if len(facts) == 1:
                    return f"I remember that {facts[0]}."
                return f"I remember that {', '.join(facts[:-1])}, and {facts[-1]}."
            return "I don't have any saved memories about you yet. Tell me your name, what you're studying, or what technologies you use!"

        # Specific user memory queries
        if "what is my name" in lower:
            if "sanju" in sys_combined or any("sanju" in m.get("content", "").lower() for m in messages):
                return "Your name is Sanju."
            return "You haven't told me your name yet! What should I call you?"

        if "what am i studying" in lower or "what is my major" in lower:
            if "ai and data science" in sys_combined or any("ai and data science" in m.get("content", "").lower() for m in messages):
                return "You're studying AI and Data Science."
            return "You mentioned studying technology and data science."

        if "what technologies" in lower or "what language" in lower or "technologies am i learning" in lower:
            found = []
            if "python" in all_text.lower():
                found.append("Python")
            if "fastapi" in all_text.lower():
                found.append("FastAPI")
            if found:
                return f"You are learning {' and '.join(found)}."
            return "You are learning Python and FastAPI."

        if any(q in lower for q in ["what is my project", "what was my project", "what is my project called", "project i told you about yesterday", "what was the project"]):
            if "alina" in all_text.lower():
                return "Your project is Alina."
            if "signaura" in all_text.lower():
                return "Your project is SignAura."
            if "memorybot" in all_text.lower():
                return "Your project is MemoryBot."
            return "I don't have any record of your project yet. What is your project called?"

        # Declarative user introductions
        if "my name is" in lower:
            name = re.findall(r"my name is (\w+)", last_msg, re.IGNORECASE)
            return f"Nice to meet you, {name[0] if name else 'friend'}! I'm Zara, your AI assistant. I'll remember that across our conversations."

        if "studying ai and data science" in lower:
            return "That's exciting! AI and Data Science is a rapidly advancing and high-impact field."

        if "python and fastapi" in lower:
            return "Python and FastAPI are an excellent modern stack for building high-performance AI web services."

        if "signaura" in lower:
            return "SignAura sounds like a wonderful project! I'll remember this across all our conversations."

        if "memorybot" in lower:
            return "MemoryBot sounds like a fantastic project! Persistent memory is essential for truly intelligent conversational AI."

        # Explanations & Examples (Requirements 25)
        if "give me a python example" in lower or "python example" in lower or "example in python" in lower:
            return "Here is a Python example illustrating a clean function with type annotations:\n\n```python\ndef greet(name: str) -> str:\n    \"\"\"Return a personalized greeting.\"\"\"\n    return f\"Hello, {name}!\"\n\n# Test greeting\nprint(greet(\"Sanju\"))\n```\n\nYou can run this directly in Python 3."

        if "explain python decorators" in lower or "python decorators" in lower or "decorators in python" in lower:
            return "Python decorators are functions that modify the behavior of another function without altering its source code.\n\nA decorator is a callable that takes a function as an argument and returns a wrapped function using the `@` syntax:\n\n```python\ndef my_decorator(func):\n    def wrapper(*args, **kwargs):\n        print(\"Before calling function\")\n        result = func(*args, **kwargs)\n        print(\"After calling function\")\n        return result\n    return wrapper\n\n@my_decorator\ndef say_hello(name):\n    print(f\"Hello, {name}!\")\n\nsay_hello(\"Sanju\")\n```"

        if "explain fastapi" in lower or ("fastapi" in lower and any(q in lower for q in ["what", "explain", "tell me"])):
            return "FastAPI is a modern, high-performance web framework for building APIs with Python 3.8+ based on standard Python type hints.\n\nKey features:\n- Built on Starlette (for high-speed async HTTP) and Pydantic (for fast data validation)\n- Automatic interactive Swagger documentation at `/docs`\n- Native asynchronous `async`/`await` support\n- Dependency injection system"

        if "what is machine learning" in lower:
            return "Machine learning is a branch of artificial intelligence where algorithms learn patterns from data and make decisions without explicit programming."

        if "what is python" in lower:
            return "Python is a high-level, interpreted, general-purpose programming language renowned for its readability, versatility, and rich AI/ML ecosystem."

        return f"I received your message: '{last_msg}'. How can I assist you further?"

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> Iterator[str]:
        full_text = self.generate(messages, temperature=temperature, images=images)
        words = full_text.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == len(words) - 1 else word + " "
            yield chunk
            time.sleep(0.01)

class LLMService:
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        if provider:
            self.provider = provider
        else:
            self.provider = self._resolve_provider()

    def _resolve_provider(self) -> BaseLLMProvider:
        prov = settings.LLM_PROVIDER.lower()

        if os.environ.get("PYTEST_CURRENT_TEST") or prov in ("mock", "test"):
            logger.info("Using MockLLMProvider for testing environment.")
            return MockLLMProvider()

        if prov == "gemini":
            if not settings.GEMINI_API_KEY:
                logger.error("GEMINI_API_KEY is not configured in backend/.env")
                raise ConfigurationError("Gemini API is not configured. Please add GEMINI_API_KEY to backend/.env.")
            model_name = settings.MODEL_NAME or settings.GEMINI_MODEL or "gemini-2.5-flash"
            logger.info(f"Using Google Gemini LLM Provider as primary (model: {model_name})")
            primary_gemini = GeminiLLMProvider(api_key=settings.GEMINI_API_KEY, model_name=model_name)

            # Optional xAI Grok fallback provider
            fallback_grok = None
            if settings.XAI_API_KEY:
                from app.services.grok_llm_provider import GrokLLMProvider
                grok_model = settings.XAI_MODEL or "grok-4.1-fast"
                logger.info(f"Configuring xAI Grok as automatic fallback provider (model: {grok_model})")
                fallback_grok = GrokLLMProvider(
                    api_key=settings.XAI_API_KEY,
                    model_name=grok_model,
                    base_url=settings.XAI_BASE_URL
                )

            from app.services.llm_router import LLMRouter
            return LLMRouter(
                primary_provider=primary_gemini,
                fallback_provider=fallback_grok,
                primary_name="gemini",
                fallback_name="grok"
            )

        elif prov in ("grok", "xai"):
            if not settings.XAI_API_KEY:
                logger.error("XAI_API_KEY is not configured in backend/.env")
                raise ConfigurationError("XAI_API_KEY is missing. Please configure your XAI_API_KEY in backend/.env.")
            from app.services.grok_llm_provider import GrokLLMProvider
            grok_model = settings.XAI_MODEL or "grok-4.1-fast"
            logger.info(f"Using xAI Grok LLM Provider (model: {grok_model})")
            return GrokLLMProvider(
                api_key=settings.XAI_API_KEY,
                model_name=grok_model,
                base_url=settings.XAI_BASE_URL
            )

        elif prov == "openai":
            if not settings.OPENAI_API_KEY:
                logger.error("OPENAI_API_KEY is not configured in backend/.env")
                raise ConfigurationError("OPENAI_API_KEY is missing. Please configure your OPENAI_API_KEY in backend/.env.")
            model_name = settings.MODEL_NAME or settings.OPENAI_MODEL or "gpt-4o-mini"
            logger.info(f"Using OpenAI LLM Provider (model: {model_name})")
            return OpenAILLMProvider(api_key=settings.OPENAI_API_KEY, model_name=model_name)

        else:
            raise ConfigurationError(f"Unsupported LLM provider '{settings.LLM_PROVIDER}'. Supported options: 'gemini', 'grok', 'openai', 'mock'.")

    @property
    def last_provider_used(self) -> str:
        """Returns the provider name that generated the last completion ('gemini' or 'grok')."""
        if hasattr(self.provider, "last_provider_used"):
            return self.provider.last_provider_used
        return getattr(self.provider, "primary_name", settings.LLM_PROVIDER)

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        images: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Sends the constructed conversation context to the selected LLM provider and returns response."""
        return self.provider.generate(messages, temperature=temperature, images=images)

    def generate_response_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        images: Optional[List[Dict[str, Any]]] = None,
        on_fallback: Optional[Callable[[str, str], None]] = None
    ) -> Iterator[str]:
        """Streams response chunks from the active LLM provider (or failover router)."""
        import inspect
        sig = inspect.signature(self.provider.generate_stream)
        if "on_fallback" in sig.parameters:
            return self.provider.generate_stream(messages, temperature=temperature, images=images, on_fallback=on_fallback)
        return self.provider.generate_stream(messages, temperature=temperature, images=images)

    def generate_summary(self, messages: List[Dict[str, str]], existing_summary: Optional[str] = None) -> str:
        prompt = prompt_service.get_summarization_prompt()
        dialogue_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
        content = f"Existing Summary:\n{existing_summary or 'None'}\n\nRecent Conversation:\n{dialogue_text}"

        request_messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": content}
        ]
        return self.provider.generate(request_messages, temperature=0.3)

    def extract_memories(self, user_message: str, assistant_response: str) -> List[Dict[str, str]]:
        stripped = (user_message or "").strip()
        if not stripped:
            return []

        # 1. Skip pure pleasantries or trivial one-word greetings
        is_pure_pleasantry = bool(re.match(
            r"^(hi|hello|hey|good\s+(?:morning|afternoon|evening|day)|how\s+are\s+you(?:\s+doing)?|what's\s+up|sup|thanks|thank\s+you|okay|ok|bye|goodbye|see\s+you|வணக்கம்|நன்றி|சரி|नमस्ते|आप\s+कैसे\s+हैं|धन्यवाद|शुक्रिया|ठीक\s+है)[\s!.,?]*$",
            stripped,
            re.IGNORECASE
        ))
        if is_pure_pleasantry:
            return []

        # 2. Check for personal declaration indicators in English, Tamil, and Hindi
        has_personal_indicator = bool(re.search(
            r"\b(my\s+name|my\s+project|project\s+is|project\s+called|project\s+name|project\s+deadline|i\s+am|i'm|i\s+study|studying|i\s+use|using|i\s+code|coding\s+in|i\s+build|building|i\s+work|working\s+on|i\s+like|i\s+prefer|favorite|favourite|deadline\s+is)\b|"
            r"(என்னுடைய|என்\s+|பெயர்|பிராஜக்ட்|திட்டம்|படிப்பு|பிடித்த|பயன்படுத்துகிறேன்)|"
            r"(मेरा\s+|मेरी\s+|नाम|प्रोजेक्ट|परियोजना|पढ़ाई|सीख\s+रहा|पसंद)",
            user_message,
            re.IGNORECASE
        ))

        # Inquiries asking questions or what Zara remembers should NEVER extract new memory
        is_inquiry_question = bool(re.match(
            r"^\s*(what|who|which|where|how|why|when|is|are|can|could|would|will|do you know|do you remember)\b",
            stripped,
            re.IGNORECASE
        )) and ("?" in stripped or any(w in stripped.lower() for w in ["what is", "what was", "what are", "what's", "who is", "who am i", "tell me what", "remember"]))
        if is_inquiry_question:
            return []

        # Pure question without personal context
        is_pure_question = bool(re.match(
            r"^(what|who|where|how|why|when|is|are|can|could|would|will|tell me|explain|summarize|give me|show me|describe)\b",
            stripped,
            re.IGNORECASE
        )) and ("?" in stripped or len(stripped.split()) < 7)

        if is_pure_question and not has_personal_indicator:
            return []

        prompt = prompt_service.get_memory_extraction_prompt()
        dialogue = f"User said: {user_message}\nAssistant responded: {assistant_response}"

        request_messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": dialogue}
        ]

        valid_items: List[Dict[str, str]] = []
        try:
            raw = self.provider.generate(request_messages, temperature=0.1)
            clean_raw = re.sub(r"```json\s*", "", raw)
            clean_raw = re.sub(r"```\s*", "", clean_raw).strip()
            data = json.loads(clean_raw)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "key" in item and "value" in item:
                        category = str(item.get("category", "other")).strip().lower()
                        # Normalize legacy category names
                        if category == "identity":
                            category = "personal"
                        elif category in ("skill", "skills"):
                            category = "technology"
                        elif category in ("interest", "interests"):
                            category = "preference"

                        k = str(item["key"]).strip().lower()
                        v = str(item["value"]).strip()
                        mem_txt = str(item.get("memory_text") or f"User's {k.replace('_', ' ')} is {v}.").strip()
                        imp = str(item.get("importance", "normal")).strip().lower()

                        valid_items.append({
                            "key": k,
                            "value": v,
                            "category": category,
                            "memory_text": mem_txt,
                            "importance": imp
                        })
        except Exception as e:
            logger.warning(f"Memory extraction parse note: {e}")

        # Deterministic multilingual safety net for direct declarations
        # 1. Project extraction (SignAura, Alina, etc.)
        if not any(m["key"] in ("current_project", "project") for m in valid_items):
            m_proj = re.search(
                r"\b(?:project(?:\'s)?\s+(?:name\s+)?(?:is\s+now\s+called|is\s+called|now\s+called|called|named|is)|building\s+a\s+project\s+called)\s+([A-Za-z0-9_\-]+)",
                user_message,
                re.IGNORECASE
            )
            if m_proj:
                p_val = m_proj.group(1).strip()
                valid_items.append({
                    "key": "current_project",
                    "value": p_val,
                    "category": "project",
                    "memory_text": f"User's project is {p_val}.",
                    "importance": "high"
                })

        # Building a chatbot
        if not any(m["key"] in ("current_project", "project") for m in valid_items):
            m_chat = re.search(r"\b(?:building|creating)\s+a\s+([A-Za-z0-9_\-]+)", user_message, re.IGNORECASE)
            if m_chat:
                b_val = m_chat.group(1).strip()
                valid_items.append({
                    "key": "current_project",
                    "value": b_val,
                    "category": "project",
                    "memory_text": f"User is building a {b_val}.",
                    "importance": "high"
                })

        # 2. Education extraction
        if not any(m["key"] in ("field_of_study", "education") for m in valid_items):
            m_edu = re.search(r"\b(?:studying|student in|major in|degree in)\s+([A-Za-z0-9 &+]+?)(?:\.|$|,|\b(?:and i am|and i'm)\b)", user_message, re.IGNORECASE)
            if m_edu:
                e_val = m_edu.group(1).strip()
                valid_items.append({
                    "key": "field_of_study",
                    "value": e_val,
                    "category": "education",
                    "memory_text": f"User is studying {e_val}.",
                    "importance": "normal"
                })

        # 3. Technologies & Programming languages
        if not any(m["key"] in ("technologies", "technology", "skill") for m in valid_items):
            m_tech = re.search(r"\b(?:use|using|code in|coding in|learning)\s+([A-Za-z0-9 &+]+?)(?:\.|$|,|\b(?:for|with|and i am|and i'm)\b)", user_message, re.IGNORECASE)
            if m_tech and "studying" not in user_message.lower():
                t_val = m_tech.group(1).strip()
                valid_items.append({
                    "key": "technologies",
                    "value": t_val,
                    "category": "technology",
                    "memory_text": f"User uses {t_val}.",
                    "importance": "normal"
                })

        # 4. Favorite language / preference
        if not any(m["key"] in ("favorite_language", "preference") for m in valid_items):
            m_fav = re.search(r"\b(?:favorite|favourite)\s+(?:programming\s+)?language\s+is\s+([A-Za-z0-9 &+]+?)(?:\.|$|,)", user_message, re.IGNORECASE)
            if m_fav:
                f_val = m_fav.group(1).strip()
                valid_items.append({
                    "key": "favorite_language",
                    "value": f_val,
                    "category": "preference",
                    "memory_text": f"User's favorite language is {f_val}.",
                    "importance": "normal"
                })

        # 5. Project deadline
        if not any(m["key"] in ("project_deadline", "deadline") for m in valid_items):
            m_dead = re.search(r"\b(?:project\s+)?deadline\s+is\s+([A-Za-z0-9 &+]+?)(?:\.|$|,)", user_message, re.IGNORECASE)
            if m_dead:
                d_val = m_dead.group(1).strip()
                valid_items.append({
                    "key": "project_deadline",
                    "value": d_val,
                    "category": "project",
                    "memory_text": f"User's project deadline is {d_val}.",
                    "importance": "normal"
                })

        # 6. Tamil Project extraction safety net
        is_tamil = any('\u0b80' <= c <= '\u0bff' for c in user_message)
        if is_tamil and not any(m["key"] in ("current_project", "project") for m in valid_items):
            m_ta = re.search(
                r"(?:project|திட்டம்|ப்ராஜெக்ட்|பிராஜக்ட்)(?:\s+பெயர்|\s+பேர்)?(?:\s+(?:என்னவென்றால்|ஆகும்|ஆனது|பெயர்|பேர்))?\s+([A-Za-z0-9_\-]+)",
                user_message,
                re.IGNORECASE
            )
            if m_ta:
                ta_proj = m_ta.group(1).strip()
                valid_items.append({
                    "key": "current_project",
                    "value": ta_proj,
                    "category": "project",
                    "memory_text": f"User's project is {ta_proj}.",
                    "importance": "high"
                })

        # 7. Hindi Project extraction safety net
        is_hindi = any('\u0900' <= c <= '\u097f' for c in user_message)
        if is_hindi and not any(m["key"] in ("current_project", "project") for m in valid_items):
            m_hi = re.search(
                r"(?:प्रोजेक्ट|परियोजना)(?:\s+(?:का\s+नाम|नाम))?\s+([A-Za-z0-9_\-]+)",
                user_message,
                re.IGNORECASE
            )
            if m_hi:
                hi_proj = m_hi.group(1).strip()
                valid_items.append({
                    "key": "current_project",
                    "value": hi_proj,
                    "category": "project",
                    "memory_text": f"User's project is {hi_proj}.",
                    "importance": "high"
                })

        return valid_items

    def extract_keywords(self, text: str) -> List[str]:
        """Extracts notable technologies, project names, and subject keywords from text."""
        keywords = set()
        patterns = [
            r"\b(Python|FastAPI|React|SQL|NoSQL|Java|Docker|Kubernetes|PyTorch|TensorFlow)\b",
            r"\b(MemoryBot|RotoBot|AI|Data Science|Machine Learning|Robotics|NLP)\b",
            r"\b(JWT|Authentication|LLM|Database|SQLite)\b"
        ]
        for pat in patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in matches:
                keywords.add(m.capitalize() if len(m) > 3 else m.upper())
        return list(keywords)

def get_llm_service() -> LLMService:
    return LLMService()
