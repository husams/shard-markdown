"""ChromaDB test fixtures with real instances only (no Mock fallbacks)."""

import os
import subprocess
import time
from collections.abc import Callable, Generator
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar

import pytest


# Handle optional ChromaDB import
try:
    import chromadb

    CHROMADB_AVAILABLE = True
except ImportError:  # pragma: no cover
    chromadb = None  # noqa: F841
    CHROMADB_AVAILABLE = False

if TYPE_CHECKING:
    import chromadb

from shard_markdown.chromadb.client import ChromaDBClient
from shard_markdown.config import Settings
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
                except (ValueError, KeyError, RuntimeError) as e:
                    # Also catch chromadb errors if available
                    if CHROMADB_AVAILABLE:
                        try:
                            import chromadb.errors

                            if isinstance(
                                e,
                                chromadb.errors.InvalidArgumentError
                                | chromadb.errors.NotFoundError,
                            ):
                                pass  # Will be handled below
                            elif not isinstance(
                                e, ValueError | KeyError | RuntimeError
                            ):
                                raise
                        except (ImportError, AttributeError):
                            # ChromaDB errors not available, continue
                            pass
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


class ChromaDBContainerManager:
    """Manage ChromaDB Docker container for testing."""

    def __init__(
        self,
        image: str = "chromadb/chroma:1.0.16",
        port: int = 8000,
        container_name: str = "shard-md-test-chromadb",
    ) -> None:
        """Initialize ChromaDB container manager.

        Args:
            image: Docker image to use
            port: Port to expose ChromaDB on
            container_name: Name of the container
        """
        self.image = image
        self.port = port
        self.container_name = container_name

    def is_running(self) -> bool:
        """Check if the ChromaDB container is running.

        Returns:
            True if container is running
        """
        try:
            result = subprocess.run(  # noqa: S603, S607
                [
                    "docker",
                    "ps",
                    "--filter",
                    f"name={self.container_name}",
                    "--format",
                    "{{.Names}}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            return self.container_name in result.stdout
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def start_container(self) -> bool:
        """Start the ChromaDB container if not running.

        Returns:
            True if started successfully or already running
        """
        if self.is_running():
            logger.info(f"ChromaDB container {self.container_name} already running")
            return True

        try:
            # Stop any existing container with the same name
            subprocess.run(  # noqa: S603, S607
                ["docker", "stop", self.container_name],
                capture_output=True,
                check=False,
            )
            subprocess.run(  # noqa: S603, S607
                ["docker", "rm", self.container_name],
                capture_output=True,
                check=False,
            )

            # Start new container
            cmd = [
                "docker",
                "run",
                "-d",
                "--name",
                self.container_name,
                "-p",
                f"{self.port}:8000",
                "-e",
                "ANONYMIZED_TELEMETRY=false",
                "-e",
                "ALLOW_RESET=true",
                self.image,
            ]

            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            container_id = result.stdout.strip()
            logger.info(
                f"Started ChromaDB container {self.container_name}: {container_id}"
            )
            return True

        except subprocess.SubprocessError as e:
            if "docker" in str(e).lower() and "not found" in str(e).lower():
                logger.error(
                    "Docker is not installed or not in PATH. Please install Docker to "
                    "run ChromaDB tests."
                )
            else:
                logger.error(f"Docker command failed: {e}")
            return False
        except FileNotFoundError:
            logger.error(
                "Docker executable not found. Please install Docker to run "
                "ChromaDB tests."
            )
            return False

    def stop_container(self) -> bool:
        """Stop the ChromaDB container.

        Returns:
            True if stopped successfully
        """
        try:
            subprocess.run(  # noqa: S603, S607
                ["docker", "stop", self.container_name],
                capture_output=True,
                check=True,
            )
            subprocess.run(  # noqa: S603, S607
                ["docker", "rm", self.container_name],
                capture_output=True,
                check=True,
            )
            logger.info(f"Stopped ChromaDB container {self.container_name}")
            return True
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to stop ChromaDB container: {e}")
            return False
        except FileNotFoundError:
            logger.error("Docker executable not found.")
            return False

    def wait_for_ready(self, timeout: int = 30) -> bool:
        """Wait for ChromaDB to be ready.

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            True if ChromaDB is ready
        """
        return wait_for_chromadb("localhost", self.port, timeout)


class ChromaDBTestFixture:
    """ChromaDB test fixture with real instances only (no Mock fallback)."""

    def __init__(
        self, host: str = "localhost", port: int = 8000, require_real: bool = True
    ) -> None:
        """Initialize ChromaDB test fixture.

        Args:
            host: ChromaDB host
            port: ChromaDB port
            require_real: If True, requires real ChromaDB instance (no mock fallback)
        """
        self.host = host
        self.port = port
        self.require_real = require_real
        self.client: ChromaDBClient | None = None
        self._test_collections: set[str] = set()
        self.container_manager = ChromaDBContainerManager(port=port)

    def setup(self) -> None:
        """Set up ChromaDB connection with retry logic - NO MOCK FALLBACK."""
        # Check if ChromaDB is available
        if not CHROMADB_AVAILABLE:
            raise RuntimeError(
                "ChromaDB not installed. Install with: pip install 'chromadb>=1.0.16'"
            )

        # Check if we're in CI environment
        is_ci = os.environ.get("CI") == "true"
        is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"

        # Use environment variables if available (for CI)
        if is_ci or is_github_actions:
            self.host = os.environ.get("CHROMA_HOST", self.host)
            self.port = int(os.environ.get("CHROMA_PORT", str(self.port)))

        logger.info(f"Setting up ChromaDB test fixture at {self.host}:{self.port}")

        # For local development (not CI), try to start container if needed
        if not (is_ci or is_github_actions):
            if not wait_for_chromadb(self.host, self.port, timeout=5):
                logger.info("ChromaDB not accessible, attempting to start container")
                if self.container_manager.start_container():
                    if not self.container_manager.wait_for_ready(timeout=30):
                        raise RuntimeError(
                            f"ChromaDB container started but not ready at "
                            f"{self.host}:{self.port}"
                        )
                else:
                    raise RuntimeError(
                        "Failed to start ChromaDB container. "
                        "Please ensure Docker is running."
                    )

        # Try to connect with exponential backoff
        max_attempts = 10 if (is_ci or is_github_actions) else 5
        for attempt in range(max_attempts):
            try:
                # Get auth token from environment if available
                auth_token = os.environ.get("CHROMA_AUTH_TOKEN")
                config = Settings(
                    chroma_host=self.host,
                    chroma_port=self.port,
                    chroma_timeout=10,
                    chroma_auth_token=auth_token,
                )
                client = ChromaDBClient(config)

                # Try to connect
                if client.connect():
                    self.client = client
                    logger.info("ChromaDB connection established")
                    return
                else:
                    raise ConnectionError("Failed to connect to ChromaDB")

            except Exception as e:
                logger.warning(f"ChromaDB connection attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(min(2**attempt, 30))  # Exponential backoff
                else:
                    # Final attempt failed - raise error
                    raise RuntimeError(
                        f"Failed to connect to ChromaDB at {self.host}:{self.port} "
                        f"after {max_attempts} attempts. Please ensure ChromaDB is "
                        f"running or available in CI environment."
                    ) from e

    def teardown(self) -> None:
        """Clean up test collections."""
        if self._test_collections and self.client:
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
    ) -> Any:  # chromadb.Collection
        """Create a test collection with proper initialization.

        Args:
            name: Collection name
            metadata: Optional metadata (currently unused but kept for API consistency)

        Returns:
            Created collection
        """
        if not self.client:
            raise RuntimeError("ChromaDB client not initialized")

        # Delete if exists
        try:
            self.client.delete_collection(name)
            logger.debug(f"Deleted existing collection: {name}")
        except Exception as e:
            # Collection doesn't exist, which is fine
            # Log the specific exception for debugging
            logger.debug(f"Collection {name} doesn't exist, will create new: {e}")

        # Create new collection using ChromaDBClient
        collection = self.client.get_or_create_collection(
            name=name, create_if_missing=True, metadata=None
        )

        self._test_collections.add(name)
        logger.info(f"Created test collection: {name}")
        return collection

    @retry_on_collection_error(max_retries=3)
    def get_or_create_test_collection(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> Any:  # chromadb.Collection
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
        except Exception as e:
            # Log the specific exception for debugging
            logger.debug(f"Failed to get collection {name}, creating new: {e}")
            return self.create_test_collection(name, metadata)

    def ensure_collection_ready(self, collection: Any) -> bool:
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
    fixture = ChromaDBTestFixture(require_real=True)
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
    if chromadb_test_fixture.client:
        return chromadb_test_fixture.client

    raise RuntimeError("ChromaDB client not available in fixture")


@pytest.fixture
def test_collection(
    chromadb_test_fixture: ChromaDBTestFixture,
) -> Any:  # chromadb.Collection
    """Create a test collection for each test.

    Args:
        chromadb_test_fixture: ChromaDB test fixture

    Returns:
        Test collection
    """
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")

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
                    if chromadb is None:
                        raise ImportError("chromadb not available")
                    # Get auth token from environment if available
                    auth_token = os.environ.get("CHROMA_AUTH_TOKEN")
                    settings = None
                    if auth_token:
                        # Create settings with authentication
                        settings = chromadb.Settings(
                            chroma_client_auth_provider="chromadb.auth.token_authn.TokenAuthClientProvider",
                            chroma_client_auth_credentials=auth_token,
                        )
                    client = (
                        chromadb.HttpClient(host=host, port=port, settings=settings)
                        if settings
                        else chromadb.HttpClient(host=host, port=port)
                    )
                    client.heartbeat()
                    logger.info(f"ChromaDB is ready at {host}:{port}")
                    return True
                except Exception as e:
                    # Not ready yet, will retry
                    logger.debug(f"ChromaDB client connection failed: {e}")

        except Exception as e:
            # Connection failed, will retry
            logger.debug(f"ChromaDB socket connection failed: {e}")

        time.sleep(1)

    logger.error(f"ChromaDB not ready after {timeout} seconds")
    return False
