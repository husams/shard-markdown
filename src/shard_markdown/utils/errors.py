"""Error handling and exception classes."""

from datetime import datetime
from typing import Any


class ShardMarkdownError(Exception):
    """Base exception for all shard-markdown errors."""

    def __init__(
        self,
        message: str,
        error_code: int,
        category: str,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the ShardMarkdownError.

        Args:
            message: Error message description
            error_code: Unique error code for this error type
            category: Error category (e.g., INPUT, CONFIG, etc.)
            context: Additional context information
            cause: The original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.category = category
        self.context = context or {}
        self.cause = cause
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for logging/reporting."""
        return {
            "error_code": self.error_code,
            "category": self.category,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None,
        }


class InputValidationError(ShardMarkdownError):
    """Errors related to invalid input validation."""

    def __init__(self, message: str, error_code: int = 1000, **kwargs: Any) -> None:
        """Initialize the InputValidationError.

        Args:
            message: Error message description
            error_code: Unique error code (default 1000)
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, error_code, "INPUT", **kwargs)


class ConfigurationError(ShardMarkdownError):
    """Errors related to configuration issues."""

    def __init__(self, message: str, error_code: int = 1100, **kwargs: Any) -> None:
        """Initialize the ConfigurationError.

        Args:
            message: Error message description
            error_code: Unique error code (default 1100)
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, error_code, "CONFIG", **kwargs)


class FileSystemError(ShardMarkdownError):
    """Errors related to file system operations."""

    def __init__(self, message: str, error_code: int = 1200, **kwargs: Any) -> None:
        """Initialize the FileSystemError.

        Args:
            message: Error message description
            error_code: Unique error code (default 1200)
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, error_code, "FILESYSTEM", **kwargs)


class ProcessingError(ShardMarkdownError):
    """Errors during document processing."""

    def __init__(self, message: str, error_code: int = 1300, **kwargs: Any) -> None:
        """Initialize the ProcessingError.

        Args:
            message: Error message description
            error_code: Unique error code (default 1300)
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, error_code, "PROCESSING", **kwargs)


class ChromaDBError(ShardMarkdownError):
    """Errors related to ChromaDB operations."""

    def __init__(self, message: str, error_code: int = 1400, **kwargs: Any) -> None:
        """Initialize the ChromaDBError.

        Args:
            message: Error message description
            error_code: Unique error code (default 1400)
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, error_code, "DATABASE", **kwargs)


class ChromaDBConnectionError(ChromaDBError):
    """Specific errors related to ChromaDB connection issues."""

    def __init__(self, message: str, error_code: int = 1405, **kwargs: Any) -> None:
        """Initialize the ChromaDBConnectionError.

        Args:
            message: Error message description
            error_code: Unique error code (default 1405)
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, error_code, **kwargs)


class SystemError(ShardMarkdownError):
    """System-level errors."""

    def __init__(self, message: str, error_code: int = 1500, **kwargs: Any) -> None:
        """Initialize the SystemError.

        Args:
            message: Error message description
            error_code: Unique error code (default 1500)
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, error_code, "SYSTEM", **kwargs)


class NetworkError(ShardMarkdownError):
    """Network-related errors."""

    def __init__(self, message: str, error_code: int = 1600, **kwargs: Any) -> None:
        """Initialize the NetworkError.

        Args:
            message: Error message description
            error_code: Unique error code (default 1600)
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(message, error_code, "NETWORK", **kwargs)
