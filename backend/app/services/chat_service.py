import json
from typing import Optional, Dict, Any, List, Generator
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app.services.context_service import ContextService
from app.services.summarization_service import SummarizationService
from app.services.file_service import FileService
from app.services.file_context_service import FileContextService
from app.services.llm_service import LLMService, get_llm_service
from app.repositories.message_repository import MessageRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.schemas.chat_schema import ChatResponse, MessageResponse, ExtractedMemoryItem
from app.utils.text_utils import detect_language
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
        Executes the official multi-turn chat workflow with persistent cross-conversation
        memory and multilingual support for Zara.
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

        llm_messages = self.context_service.build_llm_messages(
            conversation_id=conversation_id,
            user_id=user_id,
            current_user_message=message,
            language=effective_language
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

        try:
            assistant_reply = self.llm_service.generate_response(
                llm_messages,
                temperature=temperature,
                images=image_payloads if image_payloads else None
            )
        except Exception as e:
            logger.error(f"LLM Generation failure for user {user_id}: {e}")
            raise e

        assistant_msg = self.msg_repo.create(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=assistant_reply,
            language=effective_language
        )
        self.db.refresh(assistant_msg)
        self.conv_service.conv_repo.touch(conversation_id, user_id=user_id)

        extracted_memories = []
        if user_settings.memory_enabled and user_settings.auto_save_memory:
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
            robot_state=robot_state
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
        - data: {"type": "init", "conversation_id": "...", "user_message": {...}, "language": "...", "memory_used": bool}
        - data: {"type": "chunk", "chunk": "..."}
        - data: {"type": "done", "conversation_id": "...", "assistant_message": {...}, "response": "...", "language": "...", "memory_used": bool, "extracted_memories": [...]}
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

        # 1. Send initial event with user message, confirmed conversation_id, and language metadata
        init_payload = {
            "type": "init",
            "conversation_id": conversation_id,
            "user_message": MessageResponse.model_validate(user_msg).model_dump(mode="json"),
            "language": effective_language,
            "detected_language": detected_lang,
            "memory_used": memory_used,
            "voice_enabled": True
        }
        yield f"data: {json.dumps(init_payload)}\n\n"

        llm_messages = self.context_service.build_llm_messages(
            conversation_id=conversation_id,
            user_id=user_id,
            current_user_message=message,
            language=effective_language
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
        try:
            stream_gen = self.llm_service.generate_response_stream(
                llm_messages,
                temperature=temperature,
                images=image_payloads if image_payloads else None
            )
            for chunk in stream_gen:
                if chunk:
                    full_reply_parts.append(chunk)
                    chunk_payload = {"type": "chunk", "chunk": chunk}
                    yield f"data: {json.dumps(chunk_payload)}\n\n"
        except Exception as e:
            logger.error(f"Streaming failed for user {user_id}: {e}")
            err_payload = {"type": "error", "message": "The response stream was interrupted. Try regenerating the response."}
            yield f"data: {json.dumps(err_payload)}\n\n"
            return

        assistant_reply = "".join(full_reply_parts).strip()
        if not assistant_reply:
            assistant_reply = "I apologize, but I could not generate a response. Please try asking again."

        # 2. Persist complete response
        assistant_msg = self.msg_repo.create(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=assistant_reply,
            language=effective_language
        )
        self.db.refresh(assistant_msg)
        self.conv_service.conv_repo.touch(conversation_id, user_id=user_id)

        # 3. Extract persistent memory if enabled
        extracted_memories = []
        if user_settings.memory_enabled and user_settings.auto_save_memory:
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

        # 4. Send completion event with full metadata for Zara TTS & UI
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
            "robot_state": "SUCCESS" if extracted_memories else "HAPPY"
        }
        yield f"data: {json.dumps(done_payload)}\n\n"


    def regenerate_response(
        self,
        user_id: str,
        conversation_id: str,
        message_id: Optional[str] = None
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

        # Build context excluding the old assistant reply
        llm_messages = self.context_service.build_llm_messages(
            conversation_id=conversation_id,
            user_id=user_id,
            current_user_message=user_prompt.content
        )

        user_settings = self.settings_repo.get_or_create(user_id)
        temperature = self._resolve_temperature(user_settings.response_style)

        # Generate new answer
        try:
            new_reply = self.llm_service.generate_response(llm_messages, temperature=temperature)
        except Exception as e:
            logger.error(f"Regeneration error for user {user_id}: {e}")
            raise HTTPException(status_code=502, detail="MemoryBot couldn't reach the AI service. Please check your connection or try again.")

        # Update assistant message in DB
        target_assistant_msg.content = new_reply
        self.db.commit()
        self.db.refresh(target_assistant_msg)
        self.conv_service.conv_repo.touch(conversation_id, user_id=user_id)

        return ChatResponse(
            conversation_id=conversation_id,
            user_message=MessageResponse.model_validate(user_prompt),
            assistant_message=MessageResponse.model_validate(target_assistant_msg),
            extracted_memories=[],
            robot_state="HAPPY"
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
