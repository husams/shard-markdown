"""Error handling and exception classes."""

from datetime import datetime
from typing import Any, Dict, Optional


class ShardMarkdownError(Exception):
    """Base exception for all shard-markdown errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: int, 
        category: str,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.category = category
        self.context = context or {}
        self.cause = cause
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/reporting."""
        return {
            'error_code': self.error_code,
            'category': self.category,
            'message': self.message,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'cause': str(self.cause) if self.cause else None
        }


class InputValidationError(ShardMarkdownError):
    """Errors related to invalid input validation."""
    
    def __init__(self, message: str, error_code: int = 1000, **kwargs):
        super().__init__(message, error_code, "INPUT", **kwargs)


class ConfigurationError(ShardMarkdownError):
    """Errors related to configuration issues."""
    
    def __init__(self, message: str, error_code: int = 1100, **kwargs):
        super().__init__(message, error_code, "CONFIG", **kwargs)


class FileSystemError(ShardMarkdownError):
    """Errors related to file system operations."""
    
    def __init__(self, message: str, error_code: int = 1200, **kwargs):
        super().__init__(message, error_code, "FILESYSTEM", **kwargs)


class ProcessingError(ShardMarkdownError):
    """Errors during document processing."""
    
    def __init__(self, message: str, error_code: int = 1300, **kwargs):
        super().__init__(message, error_code, "PROCESSING", **kwargs)


class ChromaDBError(ShardMarkdownError):
    """Errors related to ChromaDB operations."""
    
    def __init__(self, message: str, error_code: int = 1400, **kwargs):
        super().__init__(message, error_code, "DATABASE", **kwargs)


class SystemError(ShardMarkdownError):
    """System-level errors."""
    
    def __init__(self, message: str, error_code: int = 1500, **kwargs):
        super().__init__(message, error_code, "SYSTEM", **kwargs)


class NetworkError(ShardMarkdownError):
    """Network-related errors."""
    
    def __init__(self, message: str, error_code: int = 1600, **kwargs):
        super().__init__(message, error_code, "NETWORK", **kwargs)