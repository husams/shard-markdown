"""Utilities for E2E testing."""

import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from shard_markdown.utils.logging import get_logger


logger = get_logger(__name__)

T = TypeVar("T")


def isolated_collection(func: Callable[..., T]) -> Callable[..., T]:  # noqa: UP047
    """Decorator to ensure test runs with an isolated collection.

    Creates a unique collection name for each test to avoid conflicts.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        # Generate a unique collection name
        collection_suffix = uuid.uuid4().hex[:8]

        # Look for collection_name parameter and update it
        if "collection_name" in kwargs:
            base_name = kwargs["collection_name"]
            kwargs["collection_name"] = f"{base_name}-{collection_suffix}"

        return func(*args, **kwargs)

    return wrapper
