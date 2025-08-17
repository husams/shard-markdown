"""ChromaDB decorators for common operations."""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from ..utils.errors import ChromaDBError


F = TypeVar("F", bound=Callable[..., Any])


def require_connection(func: F) -> F:  # noqa: UP047
    """Decorator to ensure ChromaDB connection is established before operation.

    This decorator replaces the repeated connection validation blocks in
    ChromaDB operations methods, reducing code duplication.

    Args:
        func: Function to wrap with connection validation

    Returns:
        Wrapped function that validates connection before execution

    Raises:
        ChromaDBError: If connection is not established (error code 1400)
    """

    @wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        # Validate connection state
        if not self.client._connection_validated or self.client.client is None:
            raise ChromaDBError(
                "ChromaDB connection not established",
                error_code=1400,
                context={"operation": func.__name__},
            )

        # Execute the original function
        return func(self, *args, **kwargs)

    return wrapper  # type: ignore[return-value]
