import json
import asyncio
import concurrent.futures
from typing import Optional, Dict, Any, List, Generator
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app.services.context_service import ContextService
from app.services.summarization_service import SummarizationService
from app.services.file_service import FileService
from app.services.file_context_service import FileContextService
from app.services.llm_service import (
    LLMService,
    get_llm_service,
    LLMQuotaExhaustedError,
    LLMServiceUnavailableError,
    ConfigurationError
)
from app.services.intent_service import IntentService
from app.services.web_search_service import WebSearchService
from app.services.realtime_service import RealtimeService
from app.services.source_service import SourceService
from app.repositories.message_repository import MessageRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.schemas.chat_schema import ChatResponse, MessageResponse, ExtractedMemoryItem, SearchSourceItem
from app.utils.text_utils import detect_language
from app.core.config import settings
from app.core.logging_config import logger

class ChatService:
    def __init__(self, db: Session, llm_service: Optional[LLMService] = None):
        self.db = db
        self.conv_service = ConversationService(db)
        self.msg_repo = MessageRepository(db)
        self.llm_service = llm_service or get_llm_service()
        self.mem_service = MemoryService(db, self.llm_service)
        self.context_service = ContextService(db)
        self.summarization_service = SummarizationService(db, self.llm_service)
        self.file_service = FileService(db)
        self.file_context_service = FileContextService(db)
        self.settings_repo = SettingsRepository(db)
        self.feedback_repo = FeedbackRepository(db)
        self.intent_service = IntentService()
        self.search_service = WebSearchService()
        self.realtime_service = RealtimeService(self.search_service)
        self.source_service = SourceService()

    def _run_async(self, coro):
        """Executes an asynchronous coroutine safely from synchronous service methods."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        else:
            return asyncio.run(coro)

    def _resolve_temperature(self, response_style: str) -> float:
        temp_map = {
            "concise": 0.4,
            "balanced": 0.7,
            "detailed": 0.6,
            "beginner-friendly": 0.7,
            "beginner_friendly": 0.7,
            "creative": 0.9,
            "precise": 0.3
        }
        return temp_map.get(response_style.lower(), 0.7)

    def process_chat_message(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None,
        attachment_ids: Optional[List[str]] = None,
        language: Optional[str] = None
    ) -> ChatResponse:
        """
        Executes the upgraded multi-turn chat workflow for Zara:
        1. Detects real-time intent and temporal freshness.
        2. Retrieves live web/API sources when required.
        3. Constructs source-aware context for Gemini.
        4. Isolates persistent user memories from web search facts.
        5. Preserves multilingual response generation (en, ta, hi).
        """
        user_settings = self.settings_repo.get_or_create(user_id)

        detected_lang = detect_language(message)
        effective_language = language if language in ("en", "ta", "hi") else detected_lang

        if conversation_id:
            conv = self.conv_service.get_conversation(conversation_id, user_id=user_id)
            if not conv:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found or access denied."
                )
        else:
            conv = self.conv_service.create_conversation(user_id=user_id)
            conversation_id = conv.id

        msg_count_before = self.msg_repo.count_by_conversation(conversation_id)
        user_msg = self.msg_repo.create(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=message,
            language=effective_language
        )

        linked_attachments = []
        if attachment_ids:
            linked_attachments = self.file_service.attach_pending_files_to_message(
                attachment_ids=attachment_ids,
                message_id=user_msg.id,
                user_id=user_id
            )
        self.db.refresh(user_msg)

        file_context_str, image_payloads = self.file_context_service.build_file_context(
            conversation_id=conversation_id,
            current_attachments=linked_attachments
        )

        if msg_count_before == 0:
            self.conv_service.auto_title_from_message(conversation_id, user_id, message)

        retrieval_info = self.context_service.get_retrieval_info(
            conversation_id=conversation_id,
            user_id=user_id,
            query=message
        )
        memory_used = retrieval_info.get("memory_used", False)

        # 1. Intent and Freshness Detection
        intent = self.intent_service.detect_intent(
            message,
            conversation_id=conversation_id,
            language=effective_language
        )
        is_realtime = intent.requires_realtime
        sources: List[SearchSourceItem] = []
        search_failed = False

        if is_realtime:
            logger.info(f"[Intent] realtime=true category={intent.category}")
            logger.info(f"[Search] query='{intent.search_query}'")
            try:
                raw_results = self._run_async(
                    self.realtime_service.get_realtime_data(intent.search_query, category=intent.category)
                )
                logger.info(f"[Search] results={len(raw_results)}")
                sources = self.source_service.normalize_sources(raw_results)
                logger.info(f"[Context] realtime_sources={len(sources)}")
            except Exception as search_err:
                logger.error(f"[Search] Safe handling of search error: {search_err}")
                search_failed = True
                sources = []
        else:
            logger.info(f"[Intent] realtime=false category={intent.category}")

        # 2. Check for search failure or empty results on real-time questions
        if is_realtime and search_failed:
            if effective_language == "ta":
                assistant_reply = "தற்போது நேரலை இணைய தகவல்களை பெற முடியவில்லை, எனவே பழைய தகவல்களை உங்களுக்கு வழங்க நான் விரும்பவில்லை."
            elif effective_language == "hi":
                assistant_reply = "वर्तमान में लाइव वेब जानकारी प्राप्त नहीं हो सकी, इसलिए मैं आपको पुरानी जानकारी नहीं देना चाहती।"
            else:
                assistant_reply = "I couldn't retrieve current web information right now, so I don't want to give you an outdated answer."
        elif is_realtime and not sources:
            if effective_language == "ta":
                assistant_reply = "தற்போதைய தகவல்களுக்காக இணையத்தில் தேடினேன், ஆனால் நம்பகமான சமீபத்திய ஆதாரங்கள் கிடைக்கவில்லை."
            elif effective_language == "hi":
                assistant_reply = "मैंने वर्तमान जानकारी के लिए वेब पर खोज की, लेकिन कोई विश्वसनीय हालिया स्रोत नहीं मिला।"
            else:
                assistant_reply = "I searched the web for current information, but could not find reliable recent sources regarding your question."
        else:
            # 3. Assemble LLM prompt sequence with sources if applicable
            llm_messages = self.context_service.build_llm_messages(
                conversation_id=conversation_id,
                user_id=user_id,
                current_user_message=message,
                language=effective_language,
                retrieved_sources=sources if is_realtime else None
            )

            if file_context_str:
                llm_messages.insert(-1, {
                    "role": "user",
                    "content": f"[DOCUMENT CONTENT ATTACHED TO THIS CONVERSATION]\n{file_context_str}"
                })
                llm_messages.insert(-1, {
                    "role": "assistant",
                    "content": "I have received and reviewed the uploaded document content. I will accurately use it to answer your questions and assist you."
                })

            temperature = self._resolve_temperature(user_settings.response_style)
            logger.info(f"[LLM] provider={settings.LLM_PROVIDER}")

            try:
                assistant_reply = self.llm_service.generate_response(
                    llm_messages,
                    temperature=temperature,
                    images=image_payloads if image_payloads else None
                )
            except Exception as e:
                logger.error(f"LLM Generation failure for user {user_id}: {e}")
                raise e

            # Append clean markdown citations if not already embedded
            if sources:
                citations_md = self.source_service.format_citations_markdown(sources)
                if citations_md and "Sources:" not in assistant_reply and "**Sources:**" not in assistant_reply:
                    assistant_reply = assistant_reply.rstrip() + citations_md

        # 4. Persist assistant message with sources JSON
        sources_json = json.dumps([s.model_dump() for s in sources]) if sources else None
        assistant_msg = self.msg_repo.create(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=assistant_reply,
            language=effective_language
        )
        if sources_json:
            assistant_msg.sources = sources_json
            self.db.commit()
        self.db.refresh(assistant_msg)
        self.conv_service.conv_repo.touch(conversation_id, user_id=user_id)

        # 5. Log search metadata safely to SQLite table
        if is_realtime:
            try:
                from app.models.web_search_log import WebSearchLog
                log_entry = WebSearchLog(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    query=intent.search_query,
                    provider=settings.WEB_SEARCH_PROVIDER,
                    result_count=len(sources)
                )
                self.db.add(log_entry)
                self.db.commit()
            except Exception as log_err:
                self.db.rollback()
                logger.warning(f"Could not persist web_search_log: {log_err}")

        # 6. Memory Extraction: Separate web search facts from personal user memories
        extracted_memories = []
        if not is_realtime and user_settings.memory_enabled and user_settings.auto_save_memory:
            try:
                saved_mems = self.mem_service.extract_and_store_memories(
                    user_id=user_id,
                    user_message=message,
                    assistant_response=assistant_reply,
                    conversation_id=conversation_id
                )
                extracted_memories = [
                    ExtractedMemoryItem(
                        key=m.key,
                        value=m.value,
                        category=m.category,
                        importance=getattr(m, "importance", "normal")
                    )
                    for m in saved_mems
                ]
            except Exception as e:
                logger.warning(f"Memory extraction non-critical error: {e}")

        try:
            self.summarization_service.check_and_summarize(conversation_id, user_id=user_id)
        except Exception as e:
            logger.warning(f"Summarization non-critical error: {e}")

        robot_state = "SUCCESS" if extracted_memories else "HAPPY"

        return ChatResponse(
            conversation_id=conversation_id,
            user_message=MessageResponse.model_validate(user_msg),
            assistant_message=MessageResponse.model_validate(assistant_msg),
            response=assistant_reply,
            language=effective_language,
            detected_language=detected_lang,
            memory_used=memory_used,
            voice_enabled=True,
            extracted_memories=extracted_memories,
            robot_state=robot_state,
            sources=sources if sources else None,
            is_realtime=is_realtime,
            provider=getattr(self.llm_service, "last_provider_used", "gemini")
        )

    def process_chat_message_stream(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None,
        attachment_ids: Optional[List[str]] = None,
        language: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Executes streaming multi-turn chat workflow, yielding Server-Sent Events (SSE).
        Protocol:
        - data: {"type": "init", "conversation_id": "...", "user_message": {...}, "language": "...", "memory_used": bool, "is_realtime": bool}
        - data: {"type": "status", "stage": "searching"|"reading_sources"|"generating"|"thinking", "message": "..."}
        - data: {"type": "chunk", "chunk": "..."}
        - data: {"type": "done", "conversation_id": "...", "assistant_message": {...}, "response": "...", "sources": [...], "is_realtime": bool}
        - data: {"type": "error", "message": "..."}
        """
        user_settings = self.settings_repo.get_or_create(user_id)

        detected_lang = detect_language(message)
        effective_language = language if language in ("en", "ta", "hi") else detected_lang

        if conversation_id:
            conv = self.conv_service.get_conversation(conversation_id, user_id=user_id)
            if not conv:
                err_data = {"type": "error", "message": "Conversation not found or access denied."}
                yield f"data: {json.dumps(err_data)}\n\n"
                return
        else:
            conv = self.conv_service.create_conversation(user_id=user_id)
            conversation_id = conv.id

        msg_count_before = self.msg_repo.count_by_conversation(conversation_id)
        user_msg = self.msg_repo.create(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=message,
            language=effective_language
        )

        linked_attachments = []
        if attachment_ids:
            linked_attachments = self.file_service.attach_pending_files_to_message(
                attachment_ids=attachment_ids,
                message_id=user_msg.id,
                user_id=user_id
            )
        self.db.refresh(user_msg)

        file_context_str, image_payloads = self.file_context_service.build_file_context(
            conversation_id=conversation_id,
            current_attachments=linked_attachments
        )

        if msg_count_before == 0:
            self.conv_service.auto_title_from_message(conversation_id, user_id, message)

        retrieval_info = self.context_service.get_retrieval_info(
            conversation_id=conversation_id,
            user_id=user_id,
            query=message
        )
        memory_used = retrieval_info.get("memory_used", False)

        # 1. Intent Detection
        intent = self.intent_service.detect_intent(
            message,
            conversation_id=conversation_id,
            language=effective_language
        )
        is_realtime = intent.requires_realtime

        # 2. Send initial event with user message, confirmed conversation_id, and language metadata
        init_payload = {
            "type": "init",
            "conversation_id": conversation_id,
            "user_message": MessageResponse.model_validate(user_msg).model_dump(mode="json"),
            "language": effective_language,
            "detected_language": detected_lang,
            "memory_used": memory_used,
            "is_realtime": is_realtime,
            "voice_enabled": True
        }
        yield f"data: {json.dumps(init_payload)}\n\n"

        sources: List[SearchSourceItem] = []
        search_failed = False

        if is_realtime:
            logger.info(f"[Intent] realtime=true category={intent.category}")
            # Stream status: searching
            yield f"data: {json.dumps({'type': 'status', 'stage': 'searching', 'message': '🔎 Searching the web...'})}\n\n"
            logger.info(f"[Search] query='{intent.search_query}'")
            try:
                raw_results = self._run_async(
                    self.realtime_service.get_realtime_data(intent.search_query, category=intent.category)
                )
                logger.info(f"[Search] results={len(raw_results)}")
                sources = self.source_service.normalize_sources(raw_results)
                logger.info(f"[Context] realtime_sources={len(sources)}")
            except Exception as search_err:
                logger.error(f"[Search] Safe handling of search error: {search_err}")
                search_failed = True
                sources = []

            # Stream status: reading sources
            yield f"data: {json.dumps({'type': 'status', 'stage': 'reading_sources', 'message': '📚 Reading current sources...', 'source_count': len(sources)})}\n\n"
            # Stream status: generating
            yield f"data: {json.dumps({'type': 'status', 'stage': 'generating', 'message': '✦ Generating answer...'})}\n\n"
        else:
            logger.info(f"[Intent] realtime=false category={intent.category}")
            # Stream status: thinking
            yield f"data: {json.dumps({'type': 'status', 'stage': 'thinking', 'message': '✦ Thinking...'})}\n\n"

        # Check search failure or no results for real-time query
        if is_realtime and search_failed:
            if effective_language == "ta":
                assistant_reply = "தற்போது நேரலை இணைய தகவல்களை பெற முடியவில்லை, எனவே பழைய தகவல்களை உங்களுக்கு வழங்க நான் விரும்பவில்லை."
            elif effective_language == "hi":
                assistant_reply = "वर्तमान में लाइव वेब जानकारी प्राप्त नहीं हो सकी, इसलिए मैं आपको पुरानी जानकारी नहीं देना चाहती।"
            else:
                assistant_reply = "I couldn't retrieve current web information right now, so I don't want to give you an outdated answer."

            yield f"data: {json.dumps({'type': 'chunk', 'chunk': assistant_reply})}\n\n"
        elif is_realtime and not sources:
            if effective_language == "ta":
                assistant_reply = "தற்போதைய தகவல்களுக்காக இணையத்தில் தேடினேன், ஆனால் நம்பகமான சமீபத்திய ஆதாரங்கள் கிடைக்கவில்லை."
            elif effective_language == "hi":
                assistant_reply = "मैंने वर्तमान जानकारी के लिए वेब पर खोज की, लेकिन कोई विश्वसनीय हालिया स्रोत नहीं मिला।"
            else:
                assistant_reply = "I searched the web for current information, but could not find reliable recent sources regarding your question."

            yield f"data: {json.dumps({'type': 'chunk', 'chunk': assistant_reply})}\n\n"
        else:
            llm_messages = self.context_service.build_llm_messages(
                conversation_id=conversation_id,
                user_id=user_id,
                current_user_message=message,
                language=effective_language,
                retrieved_sources=sources if is_realtime else None
            )

            if file_context_str:
                llm_messages.insert(-1, {
                    "role": "user",
                    "content": f"[DOCUMENT CONTENT ATTACHED TO THIS CONVERSATION]\n{file_context_str}"
                })
                llm_messages.insert(-1, {
                    "role": "assistant",
                    "content": "I have received and reviewed the uploaded document content. I will accurately use it to answer your questions and assist you."
                })

            temperature = self._resolve_temperature(user_settings.response_style)

            full_reply_parts = []
            fallback_events = []

            def handle_fallback(from_prov: str, to_prov: str):
                logger.warning(f"[ChatStream] Provider failover triggered from '{from_prov}' to '{to_prov}'")
                fallback_events.append({
                    "type": "provider_fallback",
                    "from": from_prov,
                    "to": to_prov,
                    "message": "Gemini temporarily unavailable — switching to Zara's backup AI..."
                })

            try:
                stream_gen = self.llm_service.generate_response_stream(
                    llm_messages,
                    temperature=temperature,
                    images=image_payloads if image_payloads else None,
                    on_fallback=handle_fallback
                )
                for chunk in stream_gen:
                    while fallback_events:
                        fb = fallback_events.pop(0)
                        yield f"data: {json.dumps(fb)}\n\n"
                    if chunk:
                        full_reply_parts.append(chunk)
                        chunk_payload = {"type": "chunk", "chunk": chunk}
                        yield f"data: {json.dumps(chunk_payload)}\n\n"
            except LLMQuotaExhaustedError as e:
                logger.error(f"Streaming quota exhausted for user {user_id}: {e}")
                err_payload = {
                    "type": "error",
                    "code": 429,
                    "error_type": "quota_exhausted",
                    "message": str(e)
                }
                yield f"data: {json.dumps(err_payload)}\n\n"
                return
            except LLMServiceUnavailableError as e:
                logger.error(f"Streaming service unavailable for user {user_id}: {e}")
                err_payload = {
                    "type": "error",
                    "code": 503,
                    "error_type": "service_unavailable",
                    "message": str(e)
                }
                yield f"data: {json.dumps(err_payload)}\n\n"
                return
            except Exception as e:
                logger.error(f"Streaming failed for user {user_id}: {e}")
                err_payload = {"type": "error", "code": 502, "message": "The response stream was interrupted. Try regenerating the response."}
                yield f"data: {json.dumps(err_payload)}\n\n"
                return

            assistant_reply = "".join(full_reply_parts).strip()
            if not assistant_reply:
                assistant_reply = "I apologize, but I could not generate a response. Please try asking again."

            # Append citations markdown if present
            if sources:
                citations_md = self.source_service.format_citations_markdown(sources)
                if citations_md and "Sources:" not in assistant_reply and "**Sources:**" not in assistant_reply:
                    assistant_reply = assistant_reply.rstrip() + citations_md
                    yield f"data: {json.dumps({'type': 'chunk', 'chunk': citations_md})}\n\n"

        # 3. Persist complete response
        sources_json = json.dumps([s.model_dump() for s in sources]) if sources else None
        assistant_msg = self.msg_repo.create(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=assistant_reply,
            language=effective_language
        )
        if sources_json:
            assistant_msg.sources = sources_json
            self.db.commit()
        self.db.refresh(assistant_msg)
        self.conv_service.conv_repo.touch(conversation_id, user_id=user_id)

        # 4. Log search metadata safely to SQLite table
        if is_realtime:
            try:
                from app.models.web_search_log import WebSearchLog
                log_entry = WebSearchLog(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    query=intent.search_query,
                    provider=settings.WEB_SEARCH_PROVIDER,
                    result_count=len(sources)
                )
                self.db.add(log_entry)
                self.db.commit()
            except Exception as log_err:
                self.db.rollback()
                logger.warning(f"Could not persist web_search_log: {log_err}")

        # 5. Extract persistent memory if enabled and not real-time
        extracted_memories = []
        if not is_realtime and user_settings.memory_enabled and user_settings.auto_save_memory:
            try:
                saved_mems = self.mem_service.extract_and_store_memories(
                    user_id=user_id,
                    user_message=message,
                    assistant_response=assistant_reply,
                    conversation_id=conversation_id
                )
                extracted_memories = [
                    ExtractedMemoryItem(
                        key=m.key,
                        value=m.value,
                        category=m.category,
                        importance=getattr(m, "importance", "normal")
                    )
                    for m in saved_mems
                ]
            except Exception as e:
                logger.warning(f"Memory extraction non-critical error during stream: {e}")

        try:
            self.summarization_service.check_and_summarize(conversation_id, user_id=user_id)
        except Exception as e:
            logger.warning(f"Summarization non-critical error: {e}")

        # 6. Send completion event with full metadata, sources, and Zara TTS & UI info
        done_payload = {
            "type": "done",
            "conversation_id": conversation_id,
            "assistant_message": MessageResponse.model_validate(assistant_msg).model_dump(mode="json"),
            "response": assistant_reply,
            "language": effective_language,
            "detected_language": detected_lang,
            "memory_used": memory_used,
            "voice_enabled": True,
            "extracted_memories": [m.model_dump() for m in extracted_memories],
            "robot_state": "SUCCESS" if extracted_memories else "HAPPY",
            "sources": [s.model_dump() for s in sources] if sources else None,
            "is_realtime": is_realtime,
            "provider": getattr(self.llm_service, "last_provider_used", "gemini")
        }
        yield f"data: {json.dumps(done_payload)}\n\n"


    def regenerate_response(
        self,
        user_id: str,
        conversation_id: str,
        message_id: Optional[str] = None,
        language: Optional[str] = None
    ) -> ChatResponse:
        """
        Regenerates an assistant response:
        1. Identifies the assistant message to replace (or latest assistant message).
        2. Finds the corresponding user prompt turn.
        3. Generates a fresh response from LLM using current context.
        4. Updates the assistant message in place, preserving conversation IDs and order.
        """
        conv = self.conv_service.get_conversation(conversation_id, user_id=user_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found.")

        messages = self.msg_repo.list_by_conversation(conversation_id)
        if not messages:
            raise HTTPException(status_code=400, detail="Cannot regenerate in an empty conversation.")

        # Identify assistant message
        target_assistant_msg = None
        if message_id:
            for m in messages:
                if m.id == message_id and m.role == "assistant":
                    target_assistant_msg = m
                    break
        else:
            for m in reversed(messages):
                if m.role == "assistant":
                    target_assistant_msg = m
                    break

        if not target_assistant_msg:
            raise HTTPException(status_code=404, detail="No assistant message found to regenerate.")

        # Identify corresponding user prompt preceding this assistant message
        target_idx = messages.index(target_assistant_msg)
        user_prompt = None
        for i in range(target_idx - 1, -1, -1):
            if messages[i].role == "user":
                user_prompt = messages[i]
                break

        if not user_prompt:
            raise HTTPException(status_code=400, detail="No corresponding user message found.")

        effective_language = language if language in ("en", "ta", "hi") else (target_assistant_msg.language or "en")

        # Check if user prompt requires real-time information
        intent = self.intent_service.detect_intent(
            user_prompt.content,
            conversation_id=conversation_id,
            language=effective_language
        )
        is_realtime = intent.requires_realtime
        sources: List[SearchSourceItem] = []

        if is_realtime:
            try:
                raw_results = self._run_async(
                    self.realtime_service.get_realtime_data(intent.search_query, category=intent.category)
                )
                sources = self.source_service.normalize_sources(raw_results)
            except Exception as e:
                logger.error(f"[Regenerate] Search error: {e}")
                sources = []

        # Build context excluding the old assistant reply
        llm_messages = self.context_service.build_llm_messages(
            conversation_id=conversation_id,
            user_id=user_id,
            current_user_message=user_prompt.content,
            language=effective_language,
            retrieved_sources=sources if is_realtime else None
        )

        user_settings = self.settings_repo.get_or_create(user_id)
        temperature = self._resolve_temperature(user_settings.response_style)

        # Generate new answer
        try:
            new_reply = self.llm_service.generate_response(llm_messages, temperature=temperature)
        except LLMQuotaExhaustedError as e:
            logger.error(f"Regeneration quota error for user {user_id}: {e}")
            raise HTTPException(status_code=429, detail=str(e))
        except LLMServiceUnavailableError as e:
            logger.error(f"Regeneration service unavailable for user {user_id}: {e}")
            raise HTTPException(status_code=503, detail=str(e))
        except ConfigurationError as e:
            logger.error(f"Regeneration configuration error for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error(f"Regeneration error for user {user_id}: {e}")
            raise HTTPException(status_code=502, detail="Zara couldn't reach the AI service. Please check your connection or try again.")

        if sources:
            citations_md = self.source_service.format_citations_markdown(sources)
            if citations_md and "Sources:" not in new_reply and "**Sources:**" not in new_reply:
                new_reply = new_reply.rstrip() + citations_md

        # Update assistant message in DB
        target_assistant_msg.content = new_reply
        target_assistant_msg.language = effective_language
        if sources:
            target_assistant_msg.sources = json.dumps([s.model_dump() for s in sources])
        self.db.commit()
        self.db.refresh(target_assistant_msg)
        self.conv_service.conv_repo.touch(conversation_id, user_id=user_id)

        return ChatResponse(
            conversation_id=conversation_id,
            user_message=MessageResponse.model_validate(user_prompt),
            assistant_message=MessageResponse.model_validate(target_assistant_msg),
            language=effective_language,
            extracted_memories=[],
            robot_state="HAPPY",
            sources=sources if sources else None,
            is_realtime=is_realtime,
            provider=getattr(self.llm_service, "last_provider_used", "gemini")
        )

    def record_feedback(
        self,
        user_id: str,
        message_id: str,
        feedback: Optional[str]
    ) -> Dict[str, Any]:
        """
        Saves, updates, or toggles user feedback on an assistant message.
        """
        # Validate message belongs to user's conversation
        msg = self.msg_repo.get(message_id)
        if not msg:
            raise HTTPException(status_code=404, detail="Message not found.")

        conv = self.conv_service.get_conversation(msg.conversation_id, user_id=user_id)
        if not conv:
            raise HTTPException(status_code=403, detail="Access denied.")

        result = self.feedback_repo.set_feedback(
            message_id=message_id,
            user_id=user_id,
            conversation_id=msg.conversation_id,
            feedback=feedback
        )

        return {
            "message_id": message_id,
            "feedback": result.feedback if result else None,
            "message": "Thanks for your feedback."
        }
