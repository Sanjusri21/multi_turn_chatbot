from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.message_attachment import MessageAttachment
from app.models.message import Message
from app.utils.file_utils import ALLOWED_IMAGE_EXTENSIONS, get_upload_dir
from app.services.image_service import image_service
from app.core.logging_config import logger

MAX_FILE_CONTEXT_CHARS = 25000  # Safe limit to keep within prompt window while retaining detailed context

class FileContextService:
    def __init__(self, db: Session):
        self.db = db
        self.upload_dir = get_upload_dir()

    def build_file_context(
        self,
        conversation_id: str,
        current_attachments: Optional[List[MessageAttachment]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Gathers:
        1. Extracted document text from current attachments and recent conversation attachments.
        2. Multimodal image payloads for current message images.
        Returns:
            (formatted_file_context_text, list_of_image_payloads)
        """
        all_attachments: List[MessageAttachment] = []
        seen_ids = set()

        # 1. Prioritize current message attachments
        if current_attachments:
            for att in current_attachments:
                if att.id not in seen_ids:
                    all_attachments.append(att)
                    seen_ids.add(att.id)

        # 2. Retrieve prior attachments from earlier messages in the same conversation
        if conversation_id:
            prior_atts = self.db.query(MessageAttachment).join(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(MessageAttachment.created_at.desc()).limit(5).all()

            for att in prior_atts:
                if att.id not in seen_ids:
                    all_attachments.append(att)
                    seen_ids.add(att.id)

        doc_blocks = []
        image_payloads = []
        total_chars = 0

        for att in all_attachments:
            ext = Path(att.filename).suffix.lower()

            # If image:
            if ext in ALLOWED_IMAGE_EXTENSIONS:
                # Only feed image bytes to LLM for newly uploaded images (or recent 1 image)
                file_path = self.upload_dir / att.stored_filename
                if file_path.exists():
                    try:
                        payload = image_service.prepare_multimodal_payload(file_path, att.content_type)
                        image_payloads.append(payload)
                    except Exception as e:
                        logger.warning(f"Could not load image payload for {att.filename}: {e}")
            else:
                # Extracted text document
                text = att.extracted_text or ""
                if not text:
                    continue

                # Truncate if single document is excessively large
                if len(text) > MAX_FILE_CONTEXT_CHARS:
                    truncated = text[:MAX_FILE_CONTEXT_CHARS] + f"\n\n[... Truncated for length. Displaying first {MAX_FILE_CONTEXT_CHARS} characters of {len(text)} total characters ...]"
                else:
                    truncated = text

                remaining_budget = MAX_FILE_CONTEXT_CHARS - total_chars
                if remaining_budget <= 100:
                    break

                if len(truncated) > remaining_budget:
                    truncated = truncated[:remaining_budget] + "\n... [Remaining content trimmed to preserve conversation context]"

                total_chars += len(truncated)
                doc_blocks.append(
                    f"### ATTACHED FILE: {att.filename} ({att.content_type})\n```\n{truncated}\n```"
                )

        file_context_str = ""
        if doc_blocks:
            file_context_str = (
                "## RELEVANT ATTACHED DOCUMENTS & FILES IN THIS CONVERSATION:\n"
                "The user has provided the following file content. Use it accurately to answer questions, analyze concepts, and assist the user:\n\n"
                + "\n\n".join(doc_blocks)
            )

        return file_context_str, image_payloads
