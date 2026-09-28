import io
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image
from app.core.logging_config import logger

class ImageService:
    """Handles image verification, format checking, and bytes preparation for multimodal LLMs."""

    def validate_and_inspect(self, file_path: Path) -> Dict[str, Any]:
        try:
            with Image.open(file_path) as img:
                return {
                    "format": img.format,
                    "width": img.width,
                    "height": img.height,
                    "mode": img.mode,
                    "valid": True
                }
        except Exception as e:
            logger.error(f"Image validation error for {file_path.name}: {e}")
            raise ValueError(f"Invalid or corrupted image file: {e}")

    def prepare_multimodal_payload(self, file_path: Path, mime_type: str) -> Dict[str, Any]:
        """Prepares raw bytes and mime_type for multimodal LLM consumption."""
        data = file_path.read_bytes()
        return {
            "bytes": data,
            "mime_type": mime_type or "image/jpeg",
            "filename": file_path.name
        }

image_service = ImageService()
