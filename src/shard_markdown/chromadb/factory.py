"""ChromaDB client factory with mock support."""

import os

from ..config import Settings
from ..utils.logging import get_logger
from .async_protocol import AsyncChromaDBClientProtocol
from .protocol import ChromaDBClientProtocol
from .utils import check_socket_connectivity


logger = get_logger(__name__)


def create_chromadb_client(config: Settings) -> ChromaDBClientProtocol:
    """Create ChromaDB client based on environment.

    Args:
        config: Application settings

    Returns:
        ChromaDB client (real or mock) based on environment

    Raises:
        ImportError: If ChromaDB is not available and mock is not explicitly requested
    """
    # Check if we should use mock based on environment variable
    mock_env_var = os.getenv("SHARD_MD_USE_MOCK_CHROMADB", "")
    use_mock = mock_env_var.lower() in ("true", "1", "yes")

    # Use mock if explicitly requested
    if use_mock:
        logger.info("Using mock ChromaDB client (SHARD_MD_USE_MOCK_CHROMADB=true)")
        return _create_mock_client(config)

    # Try to use real ChromaDB client
    if _is_chromadb_available() and _test_chromadb_connectivity(config):
        logger.info("Using real ChromaDB client")
        from .client import ChromaDBClient

        return ChromaDBClient(config)

    # Fall back to mock client if ChromaDB is not available
    logger.info("Using mock ChromaDB client (ChromaDB not available)")
    return _create_mock_client(config)


def _create_mock_client(config: Settings) -> ChromaDBClientProtocol:
    """Create mock client with proper error handling.

    Args:
        config: Application settings

    Returns:
        Mock ChromaDB client

    Raises:
        ImportError: If mock client cannot be imported (tests not available)
    """
    try:
        # Try to import from test fixtures
        import sys
        from pathlib import Path

        # Add tests directory to path temporarily
        test_path = Path(__file__).parent.parent.parent.parent / "tests"
        if test_path.exists():
            sys.path.insert(0, str(test_path))
            try:
                from fixtures.mock import MockChromaDBClient

                return MockChromaDBClient(config)  # type: ignore[no-any-return]
            except ImportError:
                # Mock module not available, fall through to next option
                pass
            finally:
                # Clean up path
                if str(test_path) in sys.path:
                    sys.path.remove(str(test_path))

        # If that fails, raise an informative error
        raise ImportError(
            "Mock ChromaDB client not available. "
            "Mock client is only available when running tests. "
            "Please install and start ChromaDB server, or set "
            "SHARD_MD_USE_MOCK_CHROMADB=true for testing."
        )

    except ImportError as e:
        if "Mock ChromaDB client not available" in str(e):
            raise
        # Re-raise with more context
        raise ImportError(
            f"Failed to import mock ChromaDB client: {e}. "
            "This is expected in production. Please ensure ChromaDB is installed and "
            "running."
        ) from e


def _is_chromadb_available() -> bool:
    """Check if ChromaDB is available."""
    try:
        import chromadb  # noqa: F401

        return True
    except ImportError:
        return False


def create_async_chromadb_client(
    config: Settings, max_concurrent_operations: int = 16
) -> AsyncChromaDBClientProtocol:
    """Create async ChromaDB client based on environment.

    Args:
        config: Application settings
        max_concurrent_operations: Maximum concurrent operations

    Returns:
        Async ChromaDB client (real or mock) based on environment

    Raises:
        ImportError: If ChromaDB is not available and mock is not explicitly requested
    """
    # Check if we should use mock based on environment variable
    mock_env_var = os.getenv("SHARD_MD_USE_MOCK_CHROMADB", "")
    use_mock = mock_env_var.lower() in ("true", "1", "yes")

    # Use mock if explicitly requested
    if use_mock:
        logger.info(
            "Using mock async ChromaDB client (SHARD_MD_USE_MOCK_CHROMADB=true)"
        )
        return _create_async_mock_client(config, max_concurrent_operations)

    # Try to use real async ChromaDB client
    if _is_chromadb_available() and _test_chromadb_connectivity(config):
        logger.info("Using real async ChromaDB client")
        from .async_client import AsyncChromaDBClient

        return AsyncChromaDBClient(config, max_concurrent_operations)

    # Fall back to mock client if ChromaDB is not available
    logger.info("Using mock async ChromaDB client (ChromaDB not available)")
    return _create_async_mock_client(config, max_concurrent_operations)


def _create_async_mock_client(
    config: Settings, max_concurrent_operations: int = 16
) -> AsyncChromaDBClientProtocol:
    """Create async mock client with proper error handling.

    Args:
        config: Application settings
        max_concurrent_operations: Maximum concurrent operations

    Returns:
        Mock async ChromaDB client

    Raises:
        ImportError: If mock client cannot be imported (tests not available)
    """
    try:
        # Try to import from test fixtures
        import sys
        from pathlib import Path

        # Add tests directory to path temporarily
        test_path = Path(__file__).parent.parent.parent.parent / "tests"
        if test_path.exists():
            sys.path.insert(0, str(test_path))
            try:
                from fixtures.mock import (
                    MockAsyncChromaDBClient,
                )

                return MockAsyncChromaDBClient(config, max_concurrent_operations)  # type: ignore[no-any-return]
            finally:
                # Clean up path
                if str(test_path) in sys.path:
                    sys.path.remove(str(test_path))

        # If that fails, raise an informative error
        raise ImportError(
            "Mock async ChromaDB client not available. "
            "Mock client is only available when running tests. "
            "Please install and start ChromaDB server, or set "
            "SHARD_MD_USE_MOCK_CHROMADB=true for testing."
        )

    except ImportError as e:
        if "Mock async ChromaDB client not available" in str(e):
            raise
        # Re-raise with more context
        raise ImportError(
            f"Failed to import mock async ChromaDB client: {e}. "
            "This is expected in production. Please ensure ChromaDB is installed and "
            "running."
        ) from e


def _test_chromadb_connectivity(config: Settings) -> bool:
    """Test if ChromaDB server is accessible.

    Args:
        config: Application settings

    Returns:
        True if ChromaDB server is accessible, False otherwise
    """
    try:
        # Use consolidated socket connectivity testing utility
        result = check_socket_connectivity(
            config.chroma_host, config.chroma_port, timeout=2.0
        )

        if result:
            logger.debug(
                f"ChromaDB server is accessible at "
                f"{config.chroma_host}:{config.chroma_port}"
            )
        else:
            logger.debug(
                f"ChromaDB server not accessible at "
                f"{config.chroma_host}:{config.chroma_port}"
            )

        return result

    except Exception as e:
        logger.debug("Failed to test ChromaDB connectivity: %s", e)
        return False
