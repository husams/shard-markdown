"""ChromaDB integration with mock fallback."""

from typing import Optional, Type

# Try to import real ChromaDB client, fallback to mock if not available
try:
    from .client import ChromaDBClient

    CHROMADB_AVAILABLE = True
    CHROMADB_CLIENT_CLASS: Optional[Type] = ChromaDBClient
except ImportError:
    CHROMADB_AVAILABLE = False
    CHROMADB_CLIENT_CLASS = None

from .collections import CollectionManager
from .factory import create_chromadb_client
from .mock_client import MockChromaDBClient

__all__ = [
    "CHROMADB_CLIENT_CLASS",
    "MockChromaDBClient",
    "CollectionManager",
    "create_chromadb_client",
    "CHROMADB_AVAILABLE",
]
