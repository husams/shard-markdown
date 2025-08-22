"""ChromaDB vector database storage implementation."""

import logging
from typing import Any

from ..config import Settings
from .base import StorageBackend


logger = logging.getLogger(__name__)


class VectorDBStorage(StorageBackend):
    """ChromaDB vector database storage implementation."""

    def __init__(self, host: str = "localhost", port: int = 8000):
        """Initialize VectorDB storage.

        Args:
            host: ChromaDB server host
            port: ChromaDB server port
        """
        self.host = host
        self.port = port
        self._client: Any | None = None
        self._settings: Settings | None = None

    def store(self, chunks: list[dict[str, Any]], collection: str) -> None:
        """Store chunks in ChromaDB collection.

        Args:
            chunks: List of chunk dictionaries to store
            collection: Name of the collection to store in
        """
        if not self.is_available():
            raise ConnectionError("ChromaDB is not available")

        try:
            from ..chromadb.client import ChromaDBClient
            from ..chromadb.collections import CollectionManager

            # Initialize client if needed
            if not self._client:
                # Create settings with our host/port
                if not self._settings:
                    self._settings = Settings()
                    self._settings.chroma_host = self.host
                    self._settings.chroma_port = self.port
                self._client = ChromaDBClient(self._settings)

            # Get or create collection
            manager = CollectionManager(self._client)

            # First try to get existing collection
            try:
                coll = manager.get_collection(collection)
            except Exception:
                # Create if doesn't exist
                coll = manager.create_collection(collection)

            # Prepare documents for storage
            documents = []
            metadatas = []
            ids = []

            for i, chunk in enumerate(chunks):
                # Handle chunk objects or dictionaries
                if hasattr(chunk, "content"):
                    content = chunk.content
                    metadata = chunk.metadata if hasattr(chunk, "metadata") else {}
                else:
                    content = chunk.get("content", str(chunk))
                    metadata = chunk.get("metadata", {})

                documents.append(content)
                metadatas.append(metadata)
                ids.append(f"{collection}_{i}")

            # Store in ChromaDB
            coll.add(documents=documents, metadatas=metadatas, ids=ids)

            logger.info(f"Stored {len(chunks)} chunks in collection '{collection}'")

        except Exception as e:
            logger.error(f"Failed to store chunks: {e}")
            raise

    def is_available(self) -> bool:
        """Check if ChromaDB is available.

        Returns:
            True if ChromaDB server is accessible
        """
        try:
            from ..chromadb.client import ChromaDBClient

            # Create settings with our host/port
            settings = Settings()
            settings.chroma_host = self.host
            settings.chroma_port = self.port

            client = ChromaDBClient(settings)
            # Try to connect - this will return True/False
            return client.connect()
        except Exception:
            return False
