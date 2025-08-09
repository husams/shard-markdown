"""Utilities for E2E testing."""

import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from shard_markdown.utils.logging import get_logger
from tests.fixtures.chromadb_fixtures import ChromaDBTestFixture


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


# TestDataManager is available for future E2E test enhancements
# Currently not used but provides utilities for test data management
class TestDataManager:
    """Manages test data creation and cleanup."""

    def __init__(self, fixture: ChromaDBTestFixture) -> None:
        """Initialize test data manager.

        Args:
            fixture: ChromaDB test fixture
        """
        self.fixture = fixture
        self._created_collections: set[str] = set()

    def create_test_document(
        self, content: str, filename: str = "test.md"
    ) -> dict[str, Any]:
        """Create test document data.

        Args:
            content: Document content
            filename: Document filename

        Returns:
            Document data dictionary
        """
        return {
            "content": content,
            "filename": filename,
            "metadata": {"source": filename, "created_by": "test", "test": True},
        }

    def create_isolated_collection(self, base_name: str = "test") -> str:
        """Create an isolated collection with unique name.

        Args:
            base_name: Base name for the collection

        Returns:
            Unique collection name
        """
        unique_name = f"{base_name}-{uuid.uuid4().hex[:8]}"
        self.fixture.create_test_collection(unique_name)
        self._created_collections.add(unique_name)
        logger.debug(f"Created isolated collection: {unique_name}")
        return unique_name

    def cleanup_collections(self) -> None:
        """Clean up all created collections."""
        if self._created_collections and self.fixture.client:
            logger.info(
                f"Cleaning up {len(self._created_collections)} test collections"
            )
            for collection_name in self._created_collections:
                try:
                    self.fixture.client.delete_collection(collection_name)
                    logger.debug(f"Deleted test collection: {collection_name}")
                except Exception as e:
                    logger.warning(
                        f"Failed to delete test collection {collection_name}: {e}"
                    )
            self._created_collections.clear()

    def ensure_collection_empty(self, collection_name: str) -> bool:
        """Ensure a collection is empty and ready for testing.

        Args:
            collection_name: Name of the collection

        Returns:
            True if collection is empty
        """
        if not self.fixture.client:
            return False

        try:
            collection = self.fixture.client.get_collection(collection_name)
            count = collection.count()
            if count > 0:
                logger.warning(
                    f"Collection {collection_name} has {count} items, not empty"
                )
                return False
            return True
        except Exception as e:
            logger.warning(f"Failed to check collection {collection_name}: {e}")
            return False
