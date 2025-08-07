"""ChromaDB test fixtures with proper initialization and cleanup."""

import os
import time
from collections.abc import Callable, Generator
from functools import wraps
from typing import Any, TypeVar

import chromadb
import pytest
from chromadb.api import ClientAPI

from shard_markdown.chromadb.client import ChromaDBClient
from shard_markdown.chromadb.mock_client import MockChromaDBClient
from shard_markdown.config.settings import ChromaDBConfig
from shard_markdown.utils.logging import get_logger


logger = get_logger(__name__)

T = TypeVar("T")


def retry_on_collection_error(
    max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry ChromaDB operations on collection errors.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (
                    chromadb.errors.InvalidCollectionException,
                    ValueError,
                    KeyError,
                ) as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"ChromaDB operation failed "
                            f"(attempt {attempt + 1}/{max_retries + 1}): {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"ChromaDB operation failed after "
                            f"{max_retries + 1} attempts"
                        )

            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected error in retry logic")

        return wrapper

    return decorator


class ChromaDBTestFixture:
    """ChromaDB test fixture with proper initialization and cleanup."""

    def __init__(self, host: str = "localhost", port: int = 8000) -> None:
        """Initialize ChromaDB test fixture.

        Args:
            host: ChromaDB host
            port: ChromaDB port
        """
        self.host = host
        self.port = port
        self.client: ClientAPI | None = None
        self._test_collections: set[str] = set()

    def setup(self) -> None:
        """Set up ChromaDB connection with retry logic."""
        # Check if we're in CI environment
        is_ci = os.environ.get("CI") == "true"
        is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"

        # Use environment variables if available (for CI)
        if is_ci or is_github_actions:
            self.host = os.environ.get("CHROMA_HOST", self.host)
            self.port = int(os.environ.get("CHROMA_PORT", str(self.port)))

        logger.info(f"Setting up ChromaDB test fixture at {self.host}:{self.port}")

        # Try to connect with retries
        max_attempts = 10 if (is_ci or is_github_actions) else 3
        for attempt in range(max_attempts):
            try:
                self.client = chromadb.HttpClient(host=self.host, port=self.port)
                # Test connection
                self.client.heartbeat()
                logger.info("ChromaDB connection established")
                return
            except Exception as e:
                logger.warning(f"ChromaDB connection attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(2**attempt)  # Exponential backoff
                else:
                    # If we can't connect, use mock client for tests
                    logger.warning("Using mock ChromaDB client for tests")
                    from shard_markdown.chromadb.mock_client import MockChromaDBClient

                    self.client = MockChromaDBClient()
                    return

    def teardown(self) -> None:
        """Clean up test collections."""
        if self.client and self._test_collections:
            logger.info(f"Cleaning up {len(self._test_collections)} test collections")
            for collection_name in self._test_collections:
                try:
                    self.client.delete_collection(collection_name)
                    logger.debug(f"Deleted test collection: {collection_name}")
                except Exception as e:
                    logger.warning(
                        f"Failed to delete test collection {collection_name}: {e}"
                    )
            self._test_collections.clear()

    @retry_on_collection_error(max_retries=3)
    def create_test_collection(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> chromadb.Collection:
        """Create a test collection with proper initialization.

        Args:
            name: Collection name
            metadata: Optional metadata

        Returns:
            Created collection
        """
        if not self.client:
            raise RuntimeError("ChromaDB client not initialized")

        # Delete if exists
        try:
            self.client.delete_collection(name)
            logger.debug(f"Deleted existing collection: {name}")
        except Exception:
            # Collection doesn't exist, which is fine
            logger.debug(f"Collection {name} doesn't exist, will create new")

        # Create new collection
        collection_metadata = metadata or {}
        collection_metadata.update(
            {
                "created_by": "test",
                "test": True,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )

        collection = self.client.create_collection(
            name=name, metadata=collection_metadata
        )
        self._test_collections.add(name)
        logger.info(f"Created test collection: {name}")
        return collection

    @retry_on_collection_error(max_retries=3)
    def get_or_create_test_collection(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> chromadb.Collection:
        """Get existing or create new test collection.

        Args:
            name: Collection name
            metadata: Optional metadata for new collections

        Returns:
            Collection instance
        """
        if not self.client:
            raise RuntimeError("ChromaDB client not initialized")

        try:
            collection = self.client.get_collection(name)
            logger.debug(f"Retrieved existing test collection: {name}")
            self._test_collections.add(name)
            return collection
        except Exception:
            return self.create_test_collection(name, metadata)

    def ensure_collection_ready(self, collection: chromadb.Collection) -> bool:
        """Ensure a collection is ready for operations.

        Args:
            collection: Collection to check

        Returns:
            True if collection is ready
        """
        try:
            # Try a simple operation to verify collection is ready
            collection.count()
            return True
        except Exception as e:
            logger.warning(f"Collection {collection.name} not ready: {e}")
            return False


@pytest.fixture(scope="session")
def chromadb_test_fixture() -> Generator[ChromaDBTestFixture, None, None]:
    """Session-scoped ChromaDB test fixture.

    Returns:
        Initialized ChromaDB test fixture
    """
    fixture = ChromaDBTestFixture()
    fixture.setup()
    yield fixture
    fixture.teardown()


@pytest.fixture
def chromadb_test_client(
    chromadb_test_fixture: ChromaDBTestFixture,
) -> ChromaDBClient:
    """Create a ChromaDB client for testing.

    Args:
        chromadb_test_fixture: ChromaDB test fixture

    Returns:
        ChromaDB client instance
    """
    config = ChromaDBConfig(
        host=chromadb_test_fixture.host,
        port=chromadb_test_fixture.port,
        timeout=10,
    )
    client = ChromaDBClient(config)

    # Try to connect, fall back to mock if unavailable
    try:
        if client.connect():
            return client
    except Exception as e:
        logger.warning(f"Failed to connect to ChromaDB, using mock: {e}")

    # Return mock client if real connection fails
    return MockChromaDBClient()


@pytest.fixture
def test_collection(
    chromadb_test_fixture: ChromaDBTestFixture,
) -> chromadb.Collection:
    """Create a test collection for each test.

    Args:
        chromadb_test_fixture: ChromaDB test fixture

    Returns:
        Test collection
    """
    import uuid

    collection_name = f"test-{uuid.uuid4().hex[:8]}"
    collection = chromadb_test_fixture.create_test_collection(collection_name)
    yield collection
    # Cleanup handled by fixture


def wait_for_chromadb(
    host: str = "localhost", port: int = 8000, timeout: int = 30
) -> bool:
    """Wait for ChromaDB to be ready.

    Args:
        host: ChromaDB host
        port: ChromaDB port
        timeout: Maximum wait time in seconds

    Returns:
        True if ChromaDB is ready, False otherwise
    """
    import socket

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Test socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                # Try to connect with client
                try:
                    client = chromadb.HttpClient(host=host, port=port)
                    client.heartbeat()
                    logger.info(f"ChromaDB is ready at {host}:{port}")
                    return True
                except Exception:  # noqa: S110
                    # Not ready yet, will retry
                    pass

        except Exception:  # noqa: S110
            # Connection failed, will retry
            pass

        time.sleep(1)

    logger.error(f"ChromaDB not ready after {timeout} seconds")
    return False
