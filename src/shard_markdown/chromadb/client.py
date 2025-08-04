"""ChromaDB client wrapper with connection management."""

import socket
import time
from typing import Any

import chromadb
from chromadb.api import ClientAPI

from ..config.settings import ChromaDBConfig
from ..core.models import DocumentChunk, InsertResult
from ..utils.errors import ChromaDBError, NetworkError
from ..utils.logging import get_logger


logger = get_logger(__name__)


class ChromaDBClient:
    """ChromaDB client wrapper with connection management."""

    def __init__(self, config: ChromaDBConfig) -> None:
        """Initialize client with configuration.

        Args:
            config: ChromaDB configuration
        """
        self.config = config
        self.client: ClientAPI | None = None
        self._connection_validated = False

    def connect(self) -> bool:
        """Establish connection to ChromaDB instance.

        Returns:
            True if connection successful, False otherwise

        Raises:
            NetworkError: If connection fails due to network issues
            ChromaDBError: If ChromaDB-specific connection fails
        """
        try:
            # Test basic connectivity first
            self._test_connectivity()

            # Create ChromaDB client
            self.client = chromadb.HttpClient(
                host=self.config.host,
                port=self.config.port,
                ssl=self.config.ssl,
                headers=self._get_auth_headers(),
            )

            # Test connection with heartbeat
            self.client.heartbeat()
            self._connection_validated = True

            logger.info(
                f"Connected to ChromaDB at {self.config.host}:{self.config.port}"
            )
            return True

        except (NetworkError, ChromaDBError):
            raise
        except (OSError, ConnectionError, TimeoutError, ValueError) as e:
            raise ChromaDBError(
                f"Unexpected error connecting to ChromaDB: "
                f"{self.config.host}:{self.config.port}",
                error_code=1402,
                context={
                    "host": self.config.host,
                    "port": self.config.port,
                    "ssl": self.config.ssl,
                },
                cause=e,
            )

    def get_collection(self, name: str) -> chromadb.Collection | Any:
        """Get existing collection.

        Args:
            name: Collection name

        Returns:
            ChromaDB Collection instance

        Raises:
            ChromaDBError: If collection doesn't exist or connection not established
        """
        if not self._connection_validated or self.client is None:
            raise ChromaDBError(
                "ChromaDB connection not established",
                error_code=1400,
                context={"operation": "get_collection"},
            )

        try:
            collection = self.client.get_collection(name)
            logger.info("Retrieved existing collection: %s", name)
            return collection

        except (ValueError, KeyError, AttributeError, RuntimeError) as e:
            raise ChromaDBError(
                f"Collection '{name}' does not exist",
                error_code=1413,
                context={"collection_name": name},
                cause=e,
            ) from e

    def get_or_create_collection(
        self,
        name: str,
        create_if_missing: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> chromadb.Collection | Any:
        """Get existing or create new collection.

        Args:
            name: Collection name
            create_if_missing: Whether to create collection if it doesn't exist
            metadata: Optional metadata for new collections

        Returns:
            ChromaDB Collection instance

        Raises:
            ChromaDBError: If collection operations fail
        """
        if not self._connection_validated or self.client is None:
            raise ChromaDBError(
                "ChromaDB connection not established",
                error_code=1400,
                context={"operation": "get_or_create_collection"},
            )

        try:
            # Try to get existing collection
            return self.get_collection(name)

        except ChromaDBError as get_error:
            if not create_if_missing:
                raise get_error

            # Create new collection
            try:
                collection_metadata = metadata or {}
                collection_metadata.update(
                    {
                        "created_by": "shard-md-cli",
                        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "version": "1.0.0",
                    }
                )

                collection = self.client.create_collection(
                    name=name, metadata=collection_metadata
                )

                logger.info("Created new collection: %s", name)
                return collection

            except (ValueError, RuntimeError, OSError) as create_error:
                raise ChromaDBError(
                    f"Failed to create collection: {name}",
                    error_code=1414,
                    context={
                        "collection_name": name,
                        "get_error": str(get_error),
                        "create_error": str(create_error),
                    },
                    cause=create_error,
                ) from create_error

    def bulk_insert(
        self, collection: chromadb.Collection | Any, chunks: list[DocumentChunk]
    ) -> InsertResult:
        """Bulk insert chunks into collection.

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

            # Prepare data for insertion
            ids = [chunk.id or f"chunk_{i}" for i, chunk in enumerate(chunks)]
            documents = [chunk.content for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]

            # Validate data before insertion
            self._validate_insertion_data(ids, documents, metadatas)

            # Insert into collection
            collection.add(ids=ids, documents=documents, metadatas=metadatas)

            processing_time = time.time() - start_time

            logger.info(
                f"Inserted {len(chunks)} chunks into '{getattr(collection, 'name', 'unknown')}' "
                f"in {processing_time:.2f}s"
            )

            return InsertResult(
                success=True,
                chunks_inserted=len(chunks),
                processing_time=processing_time,
                collection_name=getattr(collection, "name", "unknown"),
            )

        except (ValueError, RuntimeError, OSError, TypeError) as e:
            processing_time = time.time() - start_time
            error_msg = str(e)

            logger.error(
                "Bulk insert failed after %.2fs: %s", processing_time, error_msg
            )

            return InsertResult(
                success=False,
                error=error_msg,
                processing_time=processing_time,
                collection_name=getattr(collection, "name", "unknown"),
            )

    def list_collections(self) -> list[dict[str, Any]]:
        """List all available collections.

        Returns:
            List of collection information dictionaries

        Raises:
            ChromaDBError: If listing fails
        """
        if not self._connection_validated or self.client is None:
            raise ChromaDBError(
                "ChromaDB connection not established",
                error_code=1400,
                context={"operation": "list_collections"},
            )

        try:
            collections = self.client.list_collections()

            collection_info = []
            for collection in collections:
                try:
                    info = {
                        "name": collection.name,
                        "metadata": collection.metadata,
                        "count": collection.count(),
                    }
                    collection_info.append(info)
                except (ValueError, RuntimeError, AttributeError) as e:
                    logger.warning(
                        "Failed to get info for collection %s: %s", collection.name, e
                    )
                    collection_info.append(
                        {
                            "name": collection.name,
                            "metadata": {},
                            "count": -1,
                            "error": str(e),
                        }
                    )

            logger.info("Listed %d collections", len(collection_info))
            return collection_info

        except (ValueError, RuntimeError, AttributeError) as e:
            raise ChromaDBError(
                "Failed to list collections",
                error_code=1420,
                context={"operation": "list_collections"},
                cause=e,
            ) from e

    def delete_collection(self, name: str) -> bool:
        """Delete a collection.

        Args:
            name: Collection name to delete

        Returns:
            True if deletion successful

        Raises:
            ChromaDBError: If deletion fails
        """
        if not self._connection_validated or self.client is None:
            raise ChromaDBError(
                "ChromaDB connection not established",
                error_code=1400,
                context={"operation": "delete_collection"},
            )

        try:
            self.client.delete_collection(name)
            logger.info("Deleted collection: %s", name)
            return True

        except (ValueError, RuntimeError, KeyError) as e:
            raise ChromaDBError(
                f"Failed to delete collection: {name}",
                error_code=1421,
                context={"collection_name": name},
                cause=e,
            ) from e

    def _test_connectivity(self) -> None:
        """Test basic network connectivity to ChromaDB.

        Raises:
            NetworkError: If connectivity test fails
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.timeout)
            result = sock.connect_ex((self.config.host, self.config.port))
            sock.close()

            if result != 0:
                raise NetworkError(
                    f"Cannot connect to ChromaDB server: "
                    f"{self.config.host}:{self.config.port}",
                    error_code=1601,
                    context={
                        "host": self.config.host,
                        "port": self.config.port,
                        "timeout": self.config.timeout,
                    },
                )

        except socket.gaierror as e:
            raise NetworkError(
                f"DNS resolution failed for ChromaDB host: {self.config.host}",
                error_code=1602,
                context={"host": self.config.host},
                cause=e,
            )
        except TimeoutError as e:
            raise NetworkError(
                f"Connection timeout to ChromaDB: "
                f"{self.config.host}:{self.config.port}",
                error_code=1603,
                context={
                    "host": self.config.host,
                    "port": self.config.port,
                    "timeout": self.config.timeout,
                },
                cause=e,
            )

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers if token is configured.

        Returns:
            Dictionary of headers
        """
        headers = {}
        if self.config.auth_token:
            headers["Authorization"] = f"Bearer {self.config.auth_token}"
        return headers

    def _validate_insertion_data(
        self, ids: list[str], documents: list[str], metadatas: list[dict[str, Any]]
    ) -> None:
        """Validate data before insertion.

        Args:
            ids: Document IDs
            documents: Document contents
            metadatas: Document metadata

        Raises:
            ChromaDBError: If validation fails
        """
        if len(set([len(ids), len(documents), len(metadatas)])) > 1:
            raise ChromaDBError(
                "Mismatched lengths in insertion data",
                error_code=1430,
                context={
                    "ids_count": len(ids),
                    "documents_count": len(documents),
                    "metadatas_count": len(metadatas),
                },
            )

        # Check for duplicate IDs
        if len(ids) != len(set(ids)):
            duplicates = [id_ for id_ in set(ids) if ids.count(id_) > 1]
            raise ChromaDBError(
                f"Duplicate IDs found in insertion data: {duplicates[:5]}",
                error_code=1431,
                context={"duplicate_ids": duplicates[:10]},
            )

        # Check for empty documents
        empty_docs = [i for i, doc in enumerate(documents) if not doc.strip()]
        if empty_docs:
            raise ChromaDBError(
                f"Empty documents found at indices: {empty_docs[:5]}",
                error_code=1432,
                context={"empty_document_indices": empty_docs[:10]},
            )
