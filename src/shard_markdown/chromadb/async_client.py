"""Async ChromaDB client implementation using native AsyncHttpClient."""

import asyncio
import logging
import time

# ChromaDB imports with error handling
from typing import TYPE_CHECKING, Any, cast

from shard_markdown.config.settings import ChromaDBConfig
from shard_markdown.core.models import DocumentChunk, InsertResult


if TYPE_CHECKING:
    import chromadb
else:
    try:
        import chromadb
    except ImportError:
        chromadb = None  # type: ignore[misc]

try:
    import chromadb

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

logger = logging.getLogger(__name__)


class AsyncChromaDBClient:
    """Async ChromaDB client using native AsyncHttpClient API."""

    def __init__(
        self, config: ChromaDBConfig, max_concurrent_operations: int = 16
    ) -> None:
        """Initialize async ChromaDB client.

        Args:
            config: ChromaDB configuration
            max_concurrent_operations: Maximum concurrent operations (default: 16)
        """
        self.config = config
        self.client: Any = None
        self._connection_validated = False
        self._version_info: Any = None
        self._metadata_extractor: Any = None
        self.version_detector: Any = None
        self._semaphore = asyncio.Semaphore(max_concurrent_operations)

        # Import metadata extractor and version detector
        try:
            from shard_markdown.chromadb.version_detector import ChromaDBVersionDetector
            from shard_markdown.core.metadata import MetadataExtractor

            self._metadata_extractor = MetadataExtractor()
            self.version_detector = ChromaDBVersionDetector()
        except ImportError as e:
            logger.warning(f"Failed to import dependencies: {e}")

    async def __aenter__(self) -> "AsyncChromaDBClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        # Clean up resources if needed
        if self.client:
            # ChromaDB's AsyncHttpClient handles cleanup automatically
            pass

    async def connect(self) -> None:
        """Establish async connection to ChromaDB."""
        if not CHROMADB_AVAILABLE:
            raise RuntimeError(
                "ChromaDB is not available. Install with: pip install chromadb"
            )

        try:
            # Use ChromaDB's native AsyncHttpClient - MUST be awaited!
            self.client = await chromadb.AsyncHttpClient(
                host=self.config.host,
                port=self.config.port,
                ssl=getattr(self.config, "ssl", False),
                headers=self._get_auth_headers() if self.config.auth_token else None,
            )

            # Test connection by trying to get heartbeat
            await self._test_heartbeat()

            # Get version info if version detector is available
            if self.version_detector:
                self._version_info = await self._get_api_version_info()

            self._connection_validated = True
            logger.info(
                f"Connected to ChromaDB at {self.config.host}:{self.config.port}"
            )

        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise

    async def _test_heartbeat(self) -> None:
        """Test ChromaDB connection with heartbeat."""
        try:
            # ChromaDB AsyncHttpClient heartbeat check
            await self.client.heartbeat()
        except Exception as e:
            raise ConnectionError(f"ChromaDB heartbeat failed: {e}") from e

    async def _get_api_version_info(self) -> Any:
        """Get API version information."""
        try:
            if hasattr(self.client, "get_version"):
                return await self.client.get_version()
            return None
        except Exception as e:
            logger.warning(f"Could not retrieve version info: {e}")
            return None

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers."""
        if self.config.auth_token:
            return {"Authorization": f"Bearer {self.config.auth_token}"}
        return {}

    async def get_collection(self, name: str) -> Any:
        """Get existing collection by name.

        Args:
            name: Collection name

        Returns:
            ChromaDB collection object

        Raises:
            InvalidCollectionError: If collection doesn't exist
        """
        if not self._connection_validated:
            await self.connect()

        try:
            async with self._semaphore:
                collection = await self.client.get_collection(name)
                logger.debug(f"Retrieved collection: {name}")
                return collection
        except Exception as e:
            logger.error(f"Failed to get collection '{name}': {e}")
            raise

    async def get_or_create_collection(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
        embedding_function: str | None = None,
    ) -> Any:
        """Get or create collection with specified parameters.

        Args:
            name: Collection name
            metadata: Optional collection metadata
            embedding_function: Optional embedding function name

        Returns:
            ChromaDB collection object
        """
        if not self._connection_validated:
            await self.connect()

        try:
            async with self._semaphore:
                # Use ChromaDB's native async get_or_create_collection method
                collection_kwargs: dict[str, Any] = {"name": name}

                if metadata:
                    collection_kwargs["metadata"] = metadata

                if embedding_function and embedding_function != "default":
                    # Handle custom embedding functions if needed
                    # Note: ChromaDB expects actual embedding function objects,
                    # not string names. This is a placeholder for future enhancement.
                    logger.debug(f"Using embedding function: {embedding_function}")

                collection = await self.client.get_or_create_collection(
                    **collection_kwargs
                )
                logger.info(f"Retrieved/created collection: {name}")
                return collection

        except Exception as e:
            logger.error(f"Failed to get/create collection '{name}': {e}")
            raise

    async def bulk_insert(
        self, collection: Any, chunks: list[DocumentChunk]
    ) -> InsertResult:
        """Bulk insert chunks into collection using concurrent processing.

        Args:
            collection: Target ChromaDB collection
            chunks: List of document chunks to insert

        Returns:
            InsertResult with operation details
        """
        start_time = time.time()

        try:
            if not chunks:
                return InsertResult(
                    success=True,
                    chunks_inserted=0,
                    processing_time=0.0,
                    collection_name=getattr(collection, "name", "unknown"),
                )

            collection_name = getattr(collection, "name", "unknown")

            # Process chunks in concurrent batches for optimal performance
            batch_size = 100  # Optimal batch size for ChromaDB
            total_inserted = 0

            # Create batches for concurrent processing
            batches = [
                chunks[i : i + batch_size] for i in range(0, len(chunks), batch_size)
            ]

            # Process batches concurrently using asyncio.gather
            async def process_batch(batch_chunks: list[DocumentChunk]) -> int:
                """Process a batch of chunks."""
                async with self._semaphore:
                    # Prepare data for insertion
                    ids = [
                        chunk.id or f"chunk_{hash(chunk.content)}"
                        for chunk in batch_chunks
                    ]
                    documents = [chunk.content for chunk in batch_chunks]

                    # Sanitize metadata for ChromaDB compatibility
                    metadatas = []
                    for chunk in batch_chunks:
                        sanitized_metadata = (
                            self._metadata_extractor.sanitize_metadata_for_chromadb(
                                chunk.metadata
                            )
                            if self._metadata_extractor
                            else chunk.metadata
                        )
                        metadatas.append(sanitized_metadata)

                    # Add API version info to metadata if available
                    if self._version_info:
                        for metadata in metadatas:
                            metadata["api_version"] = getattr(
                                self._version_info, "version", "unknown"
                            )
                            chromadb_version = getattr(
                                self._version_info, "chromadb_version", None
                            )
                            if chromadb_version:
                                metadata["chromadb_version"] = chromadb_version

                    # Validate data before insertion
                    self._validate_insertion_data(ids, documents, metadatas)

                    # Insert batch using ChromaDB's native async add method
                    await collection.add(
                        ids=ids, documents=documents, metadatas=cast(Any, metadatas)
                    )

                    return len(batch_chunks)

            # Execute all batches concurrently
            batch_results = await asyncio.gather(
                *[process_batch(batch) for batch in batches]
            )

            total_inserted = sum(batch_results)
            processing_time = time.time() - start_time

            api_version = (
                getattr(self._version_info, "version", "unknown")
                if self._version_info
                else "unknown"
            )

            logger.info(
                f"Inserted {total_inserted} chunks into '{collection_name}' "
                f"in {processing_time:.2f}s using {api_version} API "
                f"(rate: {total_inserted / processing_time:.1f} chunks/s)"
            )

            return InsertResult(
                success=True,
                chunks_inserted=total_inserted,
                processing_time=processing_time,
                collection_name=collection_name,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)

            logger.error(
                "Async bulk insert failed after %.2fs: %s", processing_time, error_msg
            )

            return InsertResult(
                success=False,
                error=error_msg,
                processing_time=processing_time,
                collection_name=getattr(collection, "name", "unknown"),
            )

    def _validate_insertion_data(
        self, ids: list[str], documents: list[str], metadatas: list[dict[str, Any]]
    ) -> None:
        """Validate data before ChromaDB insertion."""
        if len(ids) != len(documents) or len(ids) != len(metadatas):
            raise ValueError(
                "Mismatched lengths: ids, documents, and metadatas must be same length"
            )

        if not ids:
            raise ValueError("Cannot insert empty data")

        # Validate IDs are unique within batch
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate IDs found in batch")

    async def list_collections(self) -> list[Any]:
        """List all collections.

        Returns:
            List of ChromaDB collection objects
        """
        if not self._connection_validated:
            await self.connect()

        try:
            async with self._semaphore:
                collections = await self.client.list_collections()
                collections_list = list(collections)  # Ensure return type is list[Any]
                logger.debug(f"Found {len(collections_list)} collections")
                return collections_list
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise

    async def delete_collection(self, name: str) -> None:
        """Delete collection by name.

        Args:
            name: Collection name to delete
        """
        if not self._connection_validated:
            await self.connect()

        try:
            async with self._semaphore:
                await self.client.delete_collection(name)
                logger.info(f"Deleted collection: {name}")
        except Exception as e:
            logger.error(f"Failed to delete collection '{name}': {e}")
            raise

    async def test_connection(self) -> bool:
        """Test ChromaDB connection.

        Returns:
            True if connection is successful
        """
        try:
            await self.connect()
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
