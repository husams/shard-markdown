"""ChromaDB integration with mock fallback."""

# Try to import real ChromaDB client, fallback to mock if not available
try:
    from .client import ChromaDBClient

    CHROMADB_AVAILABLE = True
except ImportError:
    ChromaDBClient = None
    CHROMADB_AVAILABLE = False

from .collections import CollectionManager
from .factory import create_chromadb_client
from .mock_client import MockChromaDBClient

__all__ = [
    "ChromaDBClient",
    "MockChromaDBClient",
    "CollectionManager",
    "create_chromadb_client",
    "CHROMADB_AVAILABLE",
]
