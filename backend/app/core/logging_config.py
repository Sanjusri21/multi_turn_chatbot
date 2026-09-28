import logging
import sys

def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configures structured console logging for the MemoryBot application."""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Avoid duplicate handlers if already configured
    logger = logging.getLogger("memorybot")
    if not logger.handlers:
        logger.setLevel(numeric_level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))
        logger.addHandler(handler)

    return logger

logger = setup_logging()
