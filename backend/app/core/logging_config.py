"""
Logging configuration for the application.
Supports both JSON and text formatting, file and console output.
"""

import logging
import json
from datetime import datetime
from pythonjsonlogger import jsonlogger
from pathlib import Path
from .config import get_settings

settings = get_settings()


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.utcnow().isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id


def setup_logging() -> None:
    """
    Configure logging for the application.
    Creates both file and console handlers with appropriate formatters.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_file = Path(settings.LOG_FILE)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # File handler (with JSON formatting)
    file_handler = logging.FileHandler(settings.LOG_FILE)
    file_handler.setLevel(log_level)
    
    if settings.LOG_FORMAT == "json":
        file_formatter = CustomJsonFormatter()
    else:
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console handler (with text formatting)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Set specific loggers (reduce noise from libraries)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

    root_logger.info(f"Logging initialized - Level: {settings.LOG_LEVEL}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)
