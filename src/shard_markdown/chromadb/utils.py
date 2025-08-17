"""ChromaDB utility functions for common operations."""

import socket
from typing import Any


def prepare_include_list(
    include_metadata: bool,
    include_distances: bool = False,
    base_items: list[str] | None = None,
) -> Any:
    """Prepare include list for ChromaDB operations.

    This function consolidates the repeated include list preparation logic
    found in operations methods, providing consistent behavior across
    different ChromaDB operations.

    Args:
        include_metadata: Whether to include metadata in results
        include_distances: Whether to include distances in results (for queries)
        base_items: Base items to include (defaults to ["documents"])

    Returns:
        List of items to include in ChromaDB operations (typed as Any for compatibility)
    """
    # Use default base items if none provided
    if base_items is None:
        base_items = ["documents"]

    # Start with base items
    include: list[str] = list(base_items)

    # Add distances if requested and not already present
    if include_distances and "distances" not in include:
        include.append("distances")

    # Add metadata if requested and not already present
    if include_metadata and "metadatas" not in include:
        include.append("metadatas")

    # Return as Any type for ChromaDB compatibility
    return include


def check_socket_connectivity(host: str, port: int, timeout: float = 2.0) -> bool:
    """Test socket connectivity to a host and port.

    This function consolidates the socket testing logic found in both
    factory.py and client.py, providing a consistent approach to
    connectivity testing.

    Args:
        host: Host to connect to
        port: Port to connect to
        timeout: Connection timeout in seconds

    Returns:
        True if connection successful, False otherwise
    """
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        return result == 0

    except (OSError, TimeoutError, socket.gaierror):
        return False
    finally:
        if sock:
            sock.close()
