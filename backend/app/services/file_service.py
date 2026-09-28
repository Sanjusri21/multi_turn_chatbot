import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.file_utils import (
    validate_file_metadata,
    generate_stored_filename,
    get_upload_dir,
    ALLOWED_IMAGE_EXTENSIONS,
    MIME_TYPE_MAP
)
from app.services.document_service import document_service
from app.services.image_service import image_service
from app.models.message_attachment import MessageAttachment
from app.models.message import Message
from app.models.conversation import Conversation
from app.schemas.file_schema import FileUploadResponse
from app.core.logging_config import logger

# In-memory staging for uploaded files before they are linked to a message in /api/chat
_pending_uploads: Dict[str, Dict[str, Any]] = {}

class FileService:
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.upload_dir = get_upload_dir()

    async def save_uploaded_file(self, file: UploadFile, user_id: str) -> FileUploadResponse:
        """
        Validates, saves to disk, extracts text (if document), and registers upload metadata.
        """
        raw_name = file.filename or "upload"
        # Peek at size or read into disk safely
        temp_dest_id, stored_name = generate_stored_filename(raw_name)
        file_path = self.upload_dir / stored_name

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to write file to storage: {str(e)}"
            )

        file_size = file_path.stat().st_size

        try:
            cleaned_name, ext = validate_file_metadata(raw_name, file_size, file.content_type or "")
        except ValueError as val_err:
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

        content_type = file.content_type or MIME_TYPE_MAP.get(ext, "application/octet-stream")
        extracted_text = ""
        preview = ""

        if ext in ALLOWED_IMAGE_EXTENSIONS:
            try:
                img_info = image_service.validate_and_inspect(file_path)
                preview = f"[Image: {img_info['format']} {img_info['width']}x{img_info['height']}]"
            except Exception as e:
                if file_path.exists():
                    file_path.unlink()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        else:
            extracted_text = document_service.extract_text(file_path, ext)
            preview = extracted_text[:300] + ("..." if len(extracted_text) > 300 else "")

        # Register in pending uploads
        meta = {
            "id": temp_dest_id,
            "user_id": user_id,
            "filename": cleaned_name,
            "stored_filename": stored_name,
            "content_type": content_type,
            "file_size": file_size,
            "extracted_text": extracted_text,
            "file_path": str(file_path)
        }
        _pending_uploads[temp_dest_id] = meta

        return FileUploadResponse(
            id=temp_dest_id,
            filename=cleaned_name,
            content_type=content_type,
            file_size=file_size,
            size=file_size,
            file_url=f"/api/files/{temp_dest_id}/view",
            extracted_preview=preview
        )

    def attach_pending_files_to_message(self, attachment_ids: List[str], message_id: str, user_id: str) -> List[MessageAttachment]:
        """Links uploaded files to a persistent message in the database."""
        if not self.db or not attachment_ids:
            return []

        attachments = []
        for aid in attachment_ids:
            meta = _pending_uploads.get(aid)
            if not meta:
                # Check if already attached in DB
                existing = self.db.query(MessageAttachment).filter(MessageAttachment.id == aid).first()
                if existing:
                    attachments.append(existing)
                continue

            # Verify ownership
            if meta["user_id"] != user_id:
                logger.warning(f"Unauthorized attachment attempt for file {aid} by user {user_id}")
                continue

            att = MessageAttachment(
                id=meta["id"],
                message_id=message_id,
                filename=meta["filename"],
                stored_filename=meta["stored_filename"],
                content_type=meta["content_type"],
                file_size=meta["file_size"],
                extracted_text=meta.get("extracted_text")
            )
            self.db.add(att)
            attachments.append(att)

        self.db.commit()
        for a in attachments:
            self.db.refresh(a)
        return attachments

    def get_file_record(self, file_id: str, user_id: str) -> Tuple[Path, str, str]:
        """
        Returns (Path, filename, content_type) verifying ownership.
        """
        # First check pending uploads
        if file_id in _pending_uploads:
            meta = _pending_uploads[file_id]
            if meta["user_id"] == user_id:
                p = Path(meta["file_path"])
                if p.exists():
                    return p, meta["filename"], meta["content_type"]

        # Check DB
        if self.db:
            att = self.db.query(MessageAttachment).join(Message).join(Conversation).filter(
                MessageAttachment.id == file_id,
                Conversation.user_id == user_id
            ).first()
            if att:
                p = self.upload_dir / att.stored_filename
                if p.exists():
                    return p, att.filename, att.content_type

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found or access denied.")
