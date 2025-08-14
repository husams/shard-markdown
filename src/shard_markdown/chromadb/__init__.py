"""ChromaDB integration with mock fallback."""

from typing import Optional


# Try to import real ChromaDB client, fallback to mock if not available
try:
    from .client import ChromaDBClient

    CHROMADB_AVAILABLE = True
    CHROMADB_CLIENT_CLASS: type | None = ChromaDBClient
except ImportError:
    CHROMADB_AVAILABLE = False
    CHROMADB_CLIENT_CLASS = None

from .collections import CollectionManager
from .factory import create_chromadb_client


__all__ = [
    "CHROMADB_CLIENT_CLASS",
    "CollectionManager",
    "create_chromadb_client",
    "CHROMADB_AVAILABLE",
]
