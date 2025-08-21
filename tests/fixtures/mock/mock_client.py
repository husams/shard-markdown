"""Mock ChromaDB client for testing and development."""

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from shard_markdown.config import Settings
from shard_markdown.core.models import DocumentChunk, InsertResult
from shard_markdown.utils.logging import get_logger


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
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, Any]:
        """Get documents from collection."""
        if ids is not None:
            # Handle empty list case - return empty results
            if not ids:
                return {
                    "ids": [],
                    "documents": [],
                    "metadatas": [],
                }

            # Only return data for IDs that actually exist
            existing_ids = [id_ for id_ in ids if id_ in self.documents]
            return {
                "ids": existing_ids,
                "documents": [self.documents[id_]["document"] for id_ in existing_ids],
                "metadatas": [self.documents[id_]["metadata"] for id_ in existing_ids],
            }
        else:
            # Handle pagination
            all_docs = list(self.documents.values())
            start = offset or 0
            end = start + (limit or len(all_docs))
            docs_slice = all_docs[start:end]

            return {
                "ids": [doc["id"] for doc in docs_slice],
                "documents": [doc["document"] for doc in docs_slice],
                "metadatas": [doc["metadata"] for doc in docs_slice],
            }

    def query(
        self,
        query_texts: list[str],
        n_results: int = 10,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        """Mock query implementation."""
        # Simple mock: return first n_results documents
        docs = list(self.documents.values())[:n_results]

        # Build result based on what's included
        result = {
            "ids": [[doc["id"] for doc in docs]],
            "distances": [[0.5] * len(docs)],  # Mock distances
        }

        if include is None or "documents" in include:
            result["documents"] = [[doc["document"] for doc in docs]]

        if include is None or "metadatas" in include:
            result["metadatas"] = [[doc["metadata"] for doc in docs]]

        return result

    def delete(self, ids: list[str]) -> None:
        """Delete documents from collection."""
        for id_ in ids:
            if id_ in self.documents:
                del self.documents[id_]
                self._count -= 1
        logger.debug(f"Deleted {len(ids)} documents from mock collection {self.name}")


class MockChromaDBClientAdapter:
    """Adapter for MockChromaDBClient compatibility.

    Makes MockChromaDBClient compatible with operations that expect client.client.
    """

    def __init__(self, mock_client: "MockChromaDBClient") -> None:
        """Initialize adapter with mock client."""
        self._mock_client = mock_client

    def get_collection(self, name: str) -> MockCollection:
        """Get collection."""
        return self._mock_client.get_collection(name)

    def list_collections(self) -> list[Any]:
        """List collections."""
        # Convert to mock objects that have expected attributes
        collections = []
        for name, collection in self._mock_client.collections.items():
            # Create a mock collection object with expected attributes
            mock_coll = type(
                "MockCollectionObj",
                (),
                {
                    "name": name,
                    "metadata": collection.metadata,
                    "count": lambda c=collection: c.count(),
                },
            )()
            collections.append(mock_coll)
        return collections


class MockAsyncChromaDBClientAdapter:
    """Async adapter for MockAsyncChromaDBClient compatibility.

    Makes MockAsyncChromaDBClient compatible with operations that expect client.client.
    """

    def __init__(self, mock_client: "MockAsyncChromaDBClient") -> None:
        """Initialize adapter with mock client."""
        self._mock_client = mock_client

    async def get_collection(self, name: str) -> MockCollection:
        """Get collection."""
        return await self._mock_client.get_collection(name)

    async def list_collections(self) -> list[Any]:
        """List collections."""
        # Convert to mock objects that have expected attributes
        collections = []
        for name, collection in self._mock_client.collections.items():
            # Create a mock collection object with expected attributes
            mock_coll = type(
                "MockCollectionObj",
                (),
                {
                    "name": name,
                    "metadata": collection.metadata,
                    "count": lambda c=collection: c.count(),
                },
            )()
            collections.append(mock_coll)
        return collections


class MockChromaDBClient:
    """Mock ChromaDB client for testing and development."""

    def __init__(self, config: Settings | None = None) -> None:
        """Initialize mock client.

        Args:
            config: Configuration object (optional for mock)
        """
        # Use default config if not provided
        if config is None:
            config = Settings(chroma_host="localhost", chroma_port=8000)

        # Override client attributes for mock
        self.config = config
        self.collections: dict[str, MockCollection] = {}
        self._connection_validated = False

        # Create adapter that acts as the "real" client for operations
        self.client = MockChromaDBClientAdapter(self)

        # Use temp directory for storage to avoid polluting project directory
        import os
        import tempfile

        # Create a unique subdirectory for each process to avoid conflicts
        # This is especially important on Windows where file locking is stricter
        process_id = os.getpid()
        temp_dir = Path(tempfile.gettempdir()) / f"shard_markdown_mock_{process_id}"
        # Ensure parent directories exist with parents=True
        temp_dir.mkdir(parents=True, exist_ok=True)
        self.storage_path = temp_dir / "mock_chromadb_storage.json"
        self._temp_dir = temp_dir  # Store for cleanup
        self._load_storage()

    def __del__(self) -> None:
        """Clean up temporary directory on destruction."""
        try:
            # Clean up the temp directory if it exists
            if hasattr(self, "_temp_dir") and self._temp_dir.exists():
                import shutil

                shutil.rmtree(self._temp_dir, ignore_errors=True)
        except Exception as e:  # noqa: S110
            # Log cleanup errors but don't raise - we don't want cleanup to fail
            logger.debug(f"Failed to clean up temp directory: {e}")

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
            # If collection exists, return it (ignoring metadata parameter)
            return self.get_collection(name)
        except ValueError:
            # Collection doesn't exist
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
        """Bulk insert chunks into collection.

        Implements batching to match the real ChromaDB client behavior.
        """
        start_time = time.time()

        try:
            if not chunks:
                return InsertResult(
                    success=True,
                    chunks_inserted=0,
                    processing_time=0.0,
                    collection_name=(
                        collection.name if hasattr(collection, "name") else "unknown"
                    ),
                )

            # Match the real client's batch size
            batch_size = 100
            total_inserted = 0

            for batch_start in range(0, len(chunks), batch_size):
                batch_end = min(batch_start + batch_size, len(chunks))
                batch_chunks = chunks[batch_start:batch_end]

                ids = [
                    chunk.id or f"chunk_{batch_start + i}"
                    for i, chunk in enumerate(batch_chunks)
                ]
                documents = [chunk.content for chunk in batch_chunks]
                metadatas = [chunk.metadata for chunk in batch_chunks]

                collection.add(ids, documents, metadatas)
                total_inserted += len(batch_chunks)

                # Log progress for large batches (matching real client)
                if len(chunks) > batch_size:
                    logger.debug(
                        f"Mock: Inserted batch {batch_start // batch_size + 1} "
                        f"({total_inserted}/{len(chunks)} chunks)"
                    )

            self._save_storage()

            processing_time = time.time() - start_time
            logger.info(
                f"Mock bulk insert: {total_inserted} chunks in {processing_time:.2f}s"
            )

            return InsertResult(
                success=True,
                chunks_inserted=total_inserted,
                processing_time=processing_time,
                collection_name=(
                    collection.name if hasattr(collection, "name") else "unknown"
                ),
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Mock bulk insert failed: {e}")

            return InsertResult(
                success=False,
                error=str(e),
                processing_time=processing_time,
                collection_name=(
                    collection.name if hasattr(collection, "name") else "unknown"
                ),
            )

    def _load_storage(self) -> None:
        """Load collections from storage file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, encoding="utf-8") as f:
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

            except (OSError, json.JSONDecodeError, ValueError, PermissionError) as e:
                logger.warning("Failed to load mock storage: %s", e)
                # Initialize empty collections on error
                self.collections = {}

    def _save_storage(self) -> None:
        """Save collections to storage file."""
        try:
            data = {}
            for name, collection in self.collections.items():
                data[name] = {
                    "metadata": collection.metadata,
                    "documents": collection.documents,
                }

            # Ensure directory exists before saving
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug("Saved mock collections to storage")

        except (OSError, ValueError, PermissionError) as e:
            logger.warning("Failed to save mock storage: %s", e)


class MockAsyncChromaDBClient:
    """Mock async ChromaDB client for testing and development."""

    def __init__(
        self,
        config: Settings | None = None,
        max_concurrent_operations: int = 16,
    ) -> None:
        """Initialize mock async client.

        Args:
            config: Configuration object (optional for mock)
            max_concurrent_operations: Maximum concurrent operations
        """
        # Use default config if not provided
        if config is None:
            config = Settings(chroma_host="localhost", chroma_port=8000)

        # Override client attributes for mock
        self.config = config
        self.collections: dict[str, MockCollection] = {}
        self._connection_validated = False
        self._semaphore = asyncio.Semaphore(max_concurrent_operations)

        # Create async adapter that acts as the "real" client for operations
        self.client = MockAsyncChromaDBClientAdapter(self)

        # Use temp directory for storage to avoid polluting project directory
        import os
        import tempfile

        # Create a unique subdirectory for each process to avoid conflicts
        # This is especially important on Windows where file locking is stricter
        process_id = os.getpid()
        temp_dir = (
            Path(tempfile.gettempdir()) / f"shard_markdown_async_mock_{process_id}"
        )
        # Ensure parent directories exist with parents=True
        temp_dir.mkdir(parents=True, exist_ok=True)
        self.storage_path = temp_dir / "mock_async_chromadb_storage.json"
        self._temp_dir = temp_dir  # Store for cleanup
        # Load storage synchronously during initialization
        self._load_storage_sync()

    def __del__(self) -> None:
        """Clean up temporary directory on destruction."""
        try:
            # Clean up the temp directory if it exists
            if hasattr(self, "_temp_dir") and self._temp_dir.exists():
                import shutil

                shutil.rmtree(self._temp_dir, ignore_errors=True)
        except Exception as e:  # noqa: S110
            # Log cleanup errors but don't raise - we don't want cleanup to fail
            logger.debug(f"Failed to clean up async temp directory: {e}")

    async def __aenter__(self) -> "MockAsyncChromaDBClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        # Clean up resources if needed
        pass

    async def connect(self) -> None:
        """Mock async connection - always succeeds."""
        # Simulate connection delay
        await asyncio.sleep(0.001)
        self._connection_validated = True
        logger.info("Mock async ChromaDB client connected successfully")

    async def test_connection(self) -> bool:
        """Test mock async connection."""
        # Simulate test delay
        await asyncio.sleep(0.001)
        return self._connection_validated

    async def get_collection(self, name: str) -> MockCollection:
        """Get existing collection."""
        async with self._semaphore:
            # Simulate async operation
            await asyncio.sleep(0.001)
            if name not in self.collections:
                raise ValueError(f"Collection '{name}' does not exist")
            return self.collections[name]

    async def create_collection(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> MockCollection:
        """Create new collection."""
        async with self._semaphore:
            # Simulate async operation
            await asyncio.sleep(0.001)
            if name in self.collections:
                raise ValueError(f"Collection '{name}' already exists")

            collection = MockCollection(name, metadata)
            self.collections[name] = collection
            await self._save_storage()
            logger.info(f"Created mock async collection: {name}")
            return collection

    async def get_or_create_collection(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
        embedding_function: str | None = None,
    ) -> MockCollection:
        """Get existing or create new collection."""
        async with self._semaphore:
            # Simulate async operation
            await asyncio.sleep(0.001)
            try:
                # If collection exists, return it (ignoring metadata and
                # embedding_function parameters)
                return await self.get_collection(name)
            except ValueError:
                # Collection doesn't exist, create it
                return await self.create_collection(name, metadata)

    async def list_collections(self) -> list[Any]:
        """List all collections."""
        async with self._semaphore:
            # Simulate async operation
            await asyncio.sleep(0.001)
            # Convert to mock objects that have expected attributes
            collections = []
            for name, collection in self.collections.items():
                # Create a mock collection object with expected attributes
                mock_coll = type(
                    "MockCollectionObj",
                    (),
                    {
                        "name": name,
                        "metadata": collection.metadata,
                        "count": lambda c=collection: c.count(),
                    },
                )()
                collections.append(mock_coll)
            return collections

    async def delete_collection(self, name: str) -> None:
        """Delete collection."""
        async with self._semaphore:
            # Simulate async operation
            await asyncio.sleep(0.001)
            if name not in self.collections:
                raise ValueError(f"Collection '{name}' does not exist")
            del self.collections[name]
            await self._save_storage()
            logger.info(f"Deleted mock async collection: {name}")

    async def bulk_insert(
        self, collection: Any, chunks: list[DocumentChunk]
    ) -> InsertResult:
        """Bulk insert chunks into collection.

        Implements batching to match the real ChromaDB client behavior.
        """
        async with self._semaphore:
            start_time = time.time()

            try:
                if not chunks:
                    return InsertResult(
                        success=True,
                        chunks_inserted=0,
                        processing_time=0.0,
                        collection_name=(
                            collection.name
                            if hasattr(collection, "name")
                            else "unknown"
                        ),
                    )

                # Match the real client's batch size
                batch_size = 100
                total_inserted = 0

                for batch_start in range(0, len(chunks), batch_size):
                    batch_end = min(batch_start + batch_size, len(chunks))
                    batch_chunks = chunks[batch_start:batch_end]

                    # Simulate async processing delay
                    await asyncio.sleep(0.001)

                    ids = [
                        chunk.id or f"chunk_{batch_start + i}"
                        for i, chunk in enumerate(batch_chunks)
                    ]
                    documents = [chunk.content for chunk in batch_chunks]
                    metadatas = [chunk.metadata for chunk in batch_chunks]

                    collection.add(ids, documents, metadatas)
                    total_inserted += len(batch_chunks)

                    # Log progress for large batches (matching real client)
                    if len(chunks) > batch_size:
                        batch_num = batch_start // batch_size + 1
                        logger.debug(
                            f"Mock async: Inserted batch {batch_num} "
                            f"({total_inserted}/{len(chunks)} chunks)"
                        )

                await self._save_storage()

                processing_time = time.time() - start_time
                logger.info(
                    f"Mock async bulk insert: {total_inserted} chunks "
                    f"in {processing_time:.2f}s"
                )

                return InsertResult(
                    success=True,
                    chunks_inserted=total_inserted,
                    processing_time=processing_time,
                    collection_name=(
                        collection.name if hasattr(collection, "name") else "unknown"
                    ),
                )

            except Exception as e:
                processing_time = time.time() - start_time
                logger.error(f"Mock async bulk insert failed: {e}")

                return InsertResult(
                    success=False,
                    error=str(e),
                    processing_time=processing_time,
                    collection_name=(
                        collection.name if hasattr(collection, "name") else "unknown"
                    ),
                )

    def _load_storage_sync(self) -> None:
        """Load collections from storage file synchronously (for initialization)."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, encoding="utf-8") as f:
                    data = json.load(f)

                for name, collection_data in data.items():
                    collection = MockCollection(
                        name, collection_data.get("metadata", {})
                    )
                    collection.documents = collection_data.get("documents", {})
                    collection._count = len(collection.documents)
                    self.collections[name] = collection

                logger.debug(
                    f"Loaded {len(self.collections)} mock async collections "
                    "from storage"
                )

            except (OSError, json.JSONDecodeError, ValueError, PermissionError) as e:
                logger.warning("Failed to load mock async storage: %s", e)
                # Initialize empty collections on error
                self.collections = {}

    async def _save_storage(self) -> None:
        """Save collections to storage file asynchronously."""
        try:
            data = {}
            for name, collection in self.collections.items():
                data[name] = {
                    "metadata": collection.metadata,
                    "documents": collection.documents,
                }

            # Ensure directory exists before saving
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Simulate async file operation
            await asyncio.sleep(0.001)

            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug("Saved mock async collections to storage")

        except (OSError, ValueError, PermissionError) as e:
            logger.warning("Failed to save mock async storage: %s", e)


# Function to create mock client instead of real one for testing
def create_mock_client(config: Any = None) -> MockChromaDBClient:
    """Create a mock ChromaDB client for testing."""
    return MockChromaDBClient(config)


def create_async_mock_client(
    config: Any = None, max_concurrent_operations: int = 16
) -> MockAsyncChromaDBClient:
    """Create a mock async ChromaDB client for testing."""
    return MockAsyncChromaDBClient(config, max_concurrent_operations)
