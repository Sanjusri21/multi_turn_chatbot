import os
import re
import uuid
from pathlib import Path
from typing import Tuple
from app.core.config import settings

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".csv", ".docx", ".json", ".md"}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS

MIME_TYPE_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".json": "application/json",
    ".md": "text/markdown",
}

def get_upload_dir() -> Path:
    """Returns and ensures the canonical uploads directory inside data/uploads."""
    db_path = settings.RESOLVED_DB_PATH
    upload_dir = db_path.parent / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir

def sanitize_filename(filename: str) -> str:
    """Strips path traversal components and normalizes filename."""
    base = os.path.basename(filename).strip()
    # Replace unsafe characters
    cleaned = re.sub(r"[^\w\.\-\s]", "_", base)
    return cleaned or "attachment"

def validate_file_metadata(filename: str, file_size: int, content_type: str = "") -> Tuple[str, str]:
    """
    Validates file extension and size.
    Returns (cleaned_filename, normalized_extension).
    Raises ValueError if validation fails.
    """
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File size exceeds the 10 MB limit ({file_size / (1024 * 1024):.2f} MB).")

    cleaned = sanitize_filename(filename)
    ext = Path(cleaned).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext or 'unknown'}'. Allowed formats: Images (PNG, JPG, JPEG, WEBP) and Documents (PDF, TXT, CSV, DOCX, JSON, MD)."
        )

    return cleaned, ext

def generate_stored_filename(original_filename: str) -> Tuple[str, str]:
    """Generates a collision-free UUID storage filename while preserving safe extension."""
    cleaned, ext = validate_file_metadata(original_filename, 0)
    unique_id = str(uuid.uuid4())
    stored_name = f"{unique_id}{ext}"
    return unique_id, stored_name
