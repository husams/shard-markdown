"""ChromaDB client factory with mock support."""

import os

from ..config.settings import ChromaDBConfig
from ..utils.logging import get_logger
from .protocol import ChromaDBClientProtocol


logger = get_logger(__name__)


def create_chromadb_client(
    config: ChromaDBConfig, use_mock: bool | None = None
) -> ChromaDBClientProtocol:
    """Create ChromaDB client with optional mock support.

    Args:
        config: ChromaDB configuration
        use_mock: Whether to use mock client. If None, auto-detect based on
            environment

    Returns:
        ChromaDB client (real or mock) conforming to ChromaDBClientProtocol
    """
    # Auto-detect if we should use mock
    if use_mock is None:
        # Use mock if SHARD_MD_USE_MOCK_CHROMADB is set or if ChromaDB is not
        # available
        mock_env_var = os.getenv("SHARD_MD_USE_MOCK_CHROMADB", "")
        use_mock = (
            mock_env_var.lower() in ("true", "1", "yes")
            or not _is_chromadb_available()
            or not _test_chromadb_connectivity(config)
        )

    if use_mock or not _is_chromadb_available():
        logger.info("Using mock ChromaDB client for development/testing")
        from .mock_client import MockChromaDBClient

        return MockChromaDBClient(config)
    else:
        logger.info("Using real ChromaDB client")
        from .client import ChromaDBClient

        return ChromaDBClient(config)


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
