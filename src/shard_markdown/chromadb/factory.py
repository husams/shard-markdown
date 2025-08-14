"""ChromaDB client factory with mock support."""

import os

from ..config.settings import ChromaDBConfig
from ..utils.logging import get_logger
from .protocol import ChromaDBClientProtocol


logger = get_logger(__name__)


def create_chromadb_client(config: ChromaDBConfig) -> ChromaDBClientProtocol:
    """Create ChromaDB client based on environment.

    Args:
        config: ChromaDB configuration

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


def _create_mock_client(config: ChromaDBConfig) -> ChromaDBClientProtocol:
    """Create mock client with proper error handling.

    Args:
        config: ChromaDB configuration

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

                return MockChromaDBClient(config)
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
            "This is expected in production. Please ensure ChromaDB is installed and running."
        ) from e


def _is_chromadb_available() -> bool:
    """Check if ChromaDB is available."""
    try:
        import chromadb  # noqa: F401

        return True
    except ImportError:
        return False


def _test_chromadb_connectivity(config: ChromaDBConfig) -> bool:
    """Test if ChromaDB server is accessible.

    Args:
        config: ChromaDB configuration

    Returns:
        True if ChromaDB server is accessible, False otherwise
    """
    try:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)  # Short timeout for quick test
        result = sock.connect_ex((config.host, config.port))
        sock.close()

        if result == 0:
            logger.debug(
                f"ChromaDB server is accessible at {config.host}:{config.port}"
            )
            return True
        else:
            logger.debug(
                f"ChromaDB server not accessible at {config.host}:{config.port}"
            )
            return False

    except (OSError, ImportError) as e:
        logger.debug("Failed to test ChromaDB connectivity: %s", e)
        return False
