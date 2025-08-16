"""Standardized error handling patterns for consistent error management."""

import traceback
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from rich.console import Console

from .errors import ProcessingError, ShardMarkdownError
from .logging import get_logger


logger = get_logger(__name__)
console = Console()

# Type variable for return types
T = TypeVar("T")


class ErrorHandler:
    """Standardized error handler with consistent patterns."""

    def __init__(self, verbose_level: int = 0, suppress_errors: bool = False) -> None:
        """Initialize error handler.

        Args:
            verbose_level: Level of verbosity for error reporting (0-2)
            suppress_errors: Whether to suppress re-raising errors after handling
        """
        self.verbose_level = verbose_level
        self.suppress_errors = suppress_errors

    def handle_shard_error(self, error: ShardMarkdownError, context: str = "") -> None:
        """Handle ShardMarkdownError with standardized logging and display.

        Args:
            error: The ShardMarkdownError to handle
            context: Additional context for where the error occurred
        """
        error_msg = (
            f"[red]Error{f' in {context}' if context else ''}:[/red] {error.message}"
        )
        console.print(error_msg)

        # Log the full error details
        logger.error(
            "ShardMarkdownError in %s: %s (code: %d)",
            context or "unknown",
            error.message,
            error.error_code,
        )

        if self.verbose_level > 0:
            console.print(f"[dim]Error code: {error.error_code}[/dim]")
            if error.context:
                console.print(f"[dim]Context: {error.context}[/dim]")

        if self.verbose_level > 1 and error.cause:
            console.print(f"[dim]Caused by: {error.cause}[/dim]")
            if hasattr(error.cause, "__traceback__"):
                tb_str = "".join(traceback.format_tb(error.cause.__traceback__))
                console.print(f"[dim]Traceback:\n{tb_str}[/dim]")

    def handle_unexpected_error(
        self, error: Exception, context: str = "", error_code: int = 9999
    ) -> None:
        """Handle unexpected exceptions with standardized logging.

        Args:
            error: The unexpected exception
            context: Context where the error occurred
            error_code: Error code to assign (default: 9999 for unknown errors)
        """
        error_msg = (
            f"[red]Unexpected error{f' in {context}' if context else ''}:[/red] "
            f"{str(error)}"
        )
        console.print(error_msg)

        # Log the full error details
        logger.error(
            "Unexpected error in %s: %s (%s)",
            context or "unknown",
            str(error),
            type(error).__name__,
        )

        if self.verbose_level > 0:
            console.print(f"[dim]Error type: {type(error).__name__}[/dim]")
            console.print(f"[dim]Error code: {error_code}[/dim]")

        if self.verbose_level > 1:
            tb_str = traceback.format_exc()
            console.print(f"[dim]Full traceback:\n{tb_str}[/dim]")

    def handle_processing_error(
        self,
        error: Exception,
        operation: str,
        additional_context: dict[str, Any] | None = None,
    ) -> ProcessingError:
        """Convert and handle processing errors with standardized format.

        Args:
            error: The original error
            operation: Description of the operation that failed
            additional_context: Additional context information

        Returns:
            ProcessingError instance
        """
        if isinstance(error, ProcessingError):
            # Already a ProcessingError, just handle it
            self.handle_shard_error(error, operation)
            return error

        # Convert to ProcessingError
        processing_error = ProcessingError(
            f"Failed to {operation}: {str(error)}",
            context=additional_context or {},
            cause=error,
        )

        self.handle_shard_error(processing_error, operation)
        return processing_error


def with_error_handling(
    context: str = "",
    verbose_level: int = 0,
    reraise: bool = True,
    return_on_error: Any = None,
) -> Callable[[Callable[..., T]], Callable[..., T | Any]]:
    """Decorator for standardized error handling.

    Args:
        context: Context description for error messages
        verbose_level: Verbosity level for error reporting
        reraise: Whether to re-raise errors after handling
        return_on_error: Value to return if error occurs and reraise=False

    Returns:
        Decorated function with error handling
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T | Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T | Any:
            handler = ErrorHandler(verbose_level=verbose_level)

            try:
                return func(*args, **kwargs)
            except ShardMarkdownError as e:
                handler.handle_shard_error(e, context or func.__name__)
                if reraise:
                    raise
                return return_on_error
            except Exception as e:
                handler.handle_unexpected_error(e, context or func.__name__)
                if reraise:
                    raise
                return return_on_error

        return wrapper

    return decorator


def create_error_context(operation: str, **kwargs: Any) -> dict[str, Any]:
    """Create standardized error context dictionary.

    Args:
        operation: The operation being performed
        **kwargs: Additional context fields

    Returns:
        Standardized context dictionary
    """
    context = {
        "operation": operation,
        "timestamp": str(
            logger._get_timestamp() if hasattr(logger, "_get_timestamp") else "unknown"
        ),
    }
    context.update(kwargs)
    return context


def log_error_summary(errors: list[Exception], operation: str) -> None:
    """Log a summary of multiple errors.

    Args:
        errors: List of errors that occurred
        operation: The operation during which errors occurred
    """
    if not errors:
        return

    error_summary: dict[str, int] = {}
    for error in errors:
        error_type = type(error).__name__
        error_summary[error_type] = error_summary.get(error_type, 0) + 1

    logger.warning(
        "Multiple errors during %s: %s",
        operation,
        ", ".join(
            f"{count} {error_type}" for error_type, count in error_summary.items()
        ),
    )

    console.print(
        f"[yellow]Warning: {len(errors)} errors occurred during {operation}[/yellow]"
    )
    for error_type, count in error_summary.items():
        console.print(f"[dim]  {count}x {error_type}[/dim]")
