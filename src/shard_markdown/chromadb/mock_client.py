"""Mock ChromaDB client for testing and development."""

import json
import time
from pathlib import Path
from typing import Any

from ..config.settings import ChromaDBConfig
from ..core.models import DocumentChunk, InsertResult
from ..utils.logging import get_logger


logger = get_logger(__name__)


class MockCollection:
    """Mock ChromaDB collection for testing."""

    def __init__(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """Initialize mock collection.

        Args:
            name: Collection name
            metadata: Optional metadata
        """
        self.name = name
        self.metadata = metadata or {}
        self.documents: dict[str, dict[str, Any]] = {}
        self._count = 0

    def add(
        self, ids: list[str], documents: list[str], metadatas: list[dict[str, Any]]
    ) -> None:
        """Add documents to mock collection."""
        for id_, doc, meta in zip(ids, documents, metadatas, strict=False):
            self.documents[id_] = {
                "document": doc,
                "metadata": meta,
                "id": id_,
            }
            self._count += 1

    def count(self) -> int:
        """Get document count."""
        return self._count

    def get(
        self,
        ids: list[str] | None = None,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get documents from collection."""
        if ids:
            return {
                "ids": ids,
                "documents": [
                    self.documents[id_]["document"]
                    for id_ in ids
                    if id_ in self.documents
                ],
                "metadatas": [
                    self.documents[id_]["metadata"]
                    for id_ in ids
                    if id_ in self.documents
                ],
            }
        else:
            return {
                "ids": list(self.documents.keys()),
                "documents": [doc["document"] for doc in self.documents.values()],
                "metadatas": [doc["metadata"] for doc in self.documents.values()],
            }

    def query(self, query_texts: list[str], n_results: int = 10) -> dict[str, Any]:
        """Mock query implementation."""
        # Simple mock: return first n_results documents
        docs = list(self.documents.values())[:n_results]
        return {
            "ids": [[doc["id"] for doc in docs]],
            "documents": [[doc["document"] for doc in docs]],
            "metadatas": [[doc["metadata"] for doc in docs]],
            "distances": [[0.5] * len(docs)],  # Mock distances
        }


class MockChromaDBClient:
    """Mock ChromaDB client for testing and development."""

    def __init__(self, config: ChromaDBConfig | None = None) -> None:
        """Initialize mock client.

        Args:
            config: Configuration object (optional for mock)
        """
        # Use default config if not provided
        if config is None:
            config = ChromaDBConfig(host="localhost", port=8000)

        # Override client attributes for mock
        self.config = config
        self.collections: dict[str, MockCollection] = {}
        self._connection_validated = False

        # Use temp directory for storage to avoid polluting project directory
        import tempfile

        temp_dir = Path(tempfile.gettempdir()) / "shard_markdown_mock"
        temp_dir.mkdir(exist_ok=True)
        self.storage_path = temp_dir / "mock_chromadb_storage.json"
        self._load_storage()

    def connect(self) -> bool:
        """Mock connection - always succeeds."""
        self._connection_validated = True
        logger.info("Mock ChromaDB client connected successfully")
        return True

    def heartbeat(self) -> bool:
        """Mock heartbeat."""
        return True

    def get_collection(self, name: str) -> MockCollection:
        """Get existing collection."""
        if name not in self.collections:
            raise ValueError(f"Collection '{name}' does not exist")
        return self.collections[name]

    def create_collection(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> MockCollection:
        """Create new collection."""
        if name in self.collections:
            raise ValueError(f"Collection '{name}' already exists")

        collection = MockCollection(name, metadata)
        self.collections[name] = collection
        self._save_storage()
        logger.info(f"Created mock collection: {name}")
        return collection

    def get_or_create_collection(
        self,
        name: str,
        create_if_missing: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> MockCollection:
        """Get existing or create new collection."""
        try:
            return self.get_collection(name)
        except ValueError:
            if create_if_missing:
                return self.create_collection(name, metadata)
            raise

    def list_collections(self) -> list[dict[str, Any]]:
        """List all collections."""
        collections_info = []
        for name, collection in self.collections.items():
            info = {
                "name": name,
                "count": collection.count(),
                "metadata": collection.metadata,
            }
            collections_info.append(info)
        return collections_info

    def delete_collection(self, name: str) -> bool:
        """Delete collection."""
        if name in self.collections:
            del self.collections[name]
            self._save_storage()
            logger.info(f"Deleted mock collection: {name}")
            return True
        return False

    def bulk_insert(self, collection: Any, chunks: list[DocumentChunk]) -> InsertResult:
        """Bulk insert chunks into collection."""
        start_time = time.time()

        try:
            ids = [chunk.id or f"chunk_{i}" for i, chunk in enumerate(chunks)]
            documents = [chunk.content for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]

            collection.add(ids, documents, metadatas)
            self._save_storage()

            processing_time = time.time() - start_time
            logger.info(
                f"Mock bulk insert: {len(chunks)} chunks in {processing_time:.2f}s"
            )

            return InsertResult(
                success=True,
                chunks_inserted=len(chunks),
                processing_time=processing_time,
                collection_name=collection.name,
            )

        except (ValueError, RuntimeError, OSError) as e:
            processing_time = time.time() - start_time
            logger.error("Mock bulk insert failed: %s", e)

            return InsertResult(
                success=False,
                error=str(e),
                processing_time=processing_time,
                collection_name=collection.name,
            )

    def _load_storage(self) -> None:
        """Load collections from storage file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)

                for name, collection_data in data.items():
                    collection = MockCollection(
                        name, collection_data.get("metadata", {})
                    )
                    collection.documents = collection_data.get("documents", {})
                    collection._count = len(collection.documents)
                    self.collections[name] = collection

                logger.debug(
                    f"Loaded {len(self.collections)} mock collections from storage"
                )

            except (OSError, json.JSONDecodeError, ValueError) as e:
                logger.warning("Failed to load mock storage: %s", e)

    def _save_storage(self) -> None:
        """Save collections to storage file."""
        try:
            data = {}
            for name, collection in self.collections.items():
                data[name] = {
                    "metadata": collection.metadata,
                    "documents": collection.documents,
                }

            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug("Saved mock collections to storage")

        except (OSError, ValueError) as e:
            logger.warning("Failed to save mock storage: %s", e)


# Function to create mock client instead of real one for testing
def create_mock_client(config: Any = None) -> MockChromaDBClient:
    """Create a mock ChromaDB client for testing."""
    return MockChromaDBClient(config)
