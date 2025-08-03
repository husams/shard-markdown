"""Logging configuration and utilities."""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(
    level: int = logging.INFO,
    file_path: Optional[Path] = None,
    max_file_size: int = 10485760,  # 10MB
    backup_count: int = 5,
) -> None:
    """Setup logging configuration.

    Args:
        level: Logging level
        file_path: Optional file path for file logging
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup files to keep
    """
    # Create root logger
    logger = logging.getLogger("shard_markdown")
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers.clear()

    # Setup console handler with Rich
    console_handler = RichHandler(
        console=Console(stderr=True),
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    console_handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(fmt="%(message)s", datefmt="[%X]")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Setup file handler if path provided
    if file_path:
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=file_path, maxBytes=max_file_size, backupCount=backup_count
        )
        file_handler.setLevel(level)

        # File formatter with more detail
        file_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get logger for specific module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(f"shard_markdown.{name}")


class LogContext:
    """Context manager for adding context to log messages."""

    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None

    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)
