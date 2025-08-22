"""Base interface for storage backends."""

from abc import ABC, abstractmethod
from typing import Any


class StorageBackend(ABC):
    """Base interface for storage backends."""

    @abstractmethod
    def store(self, chunks: list[dict[str, Any]], collection: str) -> None:
        """Store chunks in the backend.

        Args:
            chunks: List of chunk dictionaries to store
            collection: Name of the collection to store in
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if storage backend is available.

        Returns:
            True if the backend is available and ready
        """
        pass
