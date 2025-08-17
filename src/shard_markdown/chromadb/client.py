"""ChromaDB client wrapper with connection management and version detection."""

import socket
import time
from typing import Any, cast

from ..config.settings import ChromaDBConfig
from ..core.metadata import MetadataExtractor
from ..core.models import DocumentChunk, InsertResult
from ..utils.errors import ChromaDBError, NetworkError
from ..utils.logging import get_logger
from .version_detector import APIVersionInfo, ChromaDBVersionDetector


# Import ChromaDB exceptions for better error handling
try:
    from chromadb.errors import (
        InvalidArgumentError,
        NotFoundError,
        UniqueConstraintError,
    )

    CHROMADB_AVAILABLE = True
except ImportError:
    # Fallback if chromadb is not installed or older version
    CHROMADB_AVAILABLE = False

    class InvalidArgumentError(ValueError):  # type: ignore[no-redef]
        """Fallback InvalidArgumentError exception."""

        pass

    class NotFoundError(Exception):  # type: ignore[no-redef]
        """Fallback NotFoundError exception."""

        pass

    class UniqueConstraintError(Exception):  # type: ignore[no-redef]
        """Fallback UniqueConstraintError exception."""

        pass


# Import httpx exceptions for HTTP error handling
try:
    from httpx import HTTPStatusError

    HTTPX_AVAILABLE = True
except ImportError:
    # Fallback if httpx is not installed
    HTTPX_AVAILABLE = False

    class HTTPStatusError(Exception):  # type: ignore[no-redef]
        """Fallback HTTPStatusError exception."""

        pass


logger = get_logger(__name__)


class ChromaDBClient:
    """ChromaDB client wrapper with connection management and version detection."""

    def __init__(self, config: ChromaDBConfig) -> None:
        """Initialize client with configuration.

        Args:
            config: ChromaDB configuration
        """
        self.config = config
        self.client: Any | None = None  # ClientAPI when connected
        self._connection_validated = False
        self._version_info: APIVersionInfo | None = None

        # Initialize metadata extractor for sanitization
        self._metadata_extractor = MetadataExtractor()

        # Initialize version detector
        self.version_detector = ChromaDBVersionDetector(
            host=config.host,
            port=config.port,
            timeout=config.timeout,
            max_retries=3,  # Fewer retries for client operations
        )

    def connect(self) -> bool:
        """Establish connection to ChromaDB instance with version detection.

        Returns:
            True if connection successful, False otherwise

        Raises:
            NetworkError: If connection fails due to network issues
            ChromaDBError: If ChromaDB-specific connection fails
        """
        try:
            # Test basic connectivity first
            self._test_connectivity()

            # Detect API version and endpoints
            logger.info("Detecting ChromaDB API version...")
            self._version_info = self.version_detector.detect_api_version()

            logger.info(
                f"Detected ChromaDB API version: {self._version_info.version} "
                f"(ChromaDB {self._version_info.chromadb_version or 'unknown'})"
            )

            # Create ChromaDB client with version-specific settings
            import chromadb

            client_settings = self._get_client_settings()
            self.client = chromadb.HttpClient(**client_settings)

            # Test connection with heartbeat - use version-aware approach
            self._test_heartbeat()
            self._connection_validated = True

            logger.info(
                f"Connected to ChromaDB at {self.config.host}:{self.config.port} "
                f"using {self._version_info.version} API"
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
                    "detected_version": self._version_info.version
                    if self._version_info
                    else None,
                },
                cause=e,
            ) from e

    def get_api_version_info(self) -> APIVersionInfo | None:
        """Get detected API version information.

        Returns:
            API version info or None if not detected yet
        """
        return self._version_info

    def get_collection(self, name: str) -> Any:  # chromadb.Collection
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

        except Exception as e:
            # Check if it's a "collection doesn't exist" error from ChromaDB
            error_msg = str(e).lower()
            if "does not exist" in error_msg or "not found" in error_msg:
                raise ChromaDBError(
                    f"Collection '{name}' does not exist",
                    error_code=1413,
                    context={
                        "collection_name": name,
                        "api_version": self._version_info.version
                        if self._version_info
                        else None,
                    },
                    cause=e,
                ) from e
            # For other errors, re-raise with different error code
            raise ChromaDBError(
                f"Failed to get collection '{name}': {str(e)}",
                error_code=1499,
                context={
                    "collection_name": name,
                    "api_version": self._version_info.version
                    if self._version_info
                    else None,
                    "original_error": str(e),
                },
                cause=e,
            ) from e

    def get_or_create_collection(
        self,
        name: str,
        create_if_missing: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> Any:  # Returns chromadb.Collection when connected
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
            # Try to get existing collection using the raw client
            # to avoid double-wrapping errors
            collection = self.client.get_collection(name)
            logger.info("Retrieved existing collection: %s", name)
            return collection

        except Exception as get_error:
            # Check if it's a "not found" error - handle both ChromaDB native errors
            # and our wrapped errors
            error_msg = str(get_error).lower()

            # Also check the actual error type and its attributes
            is_not_found = False

            # Check error message patterns
            if (
                "does not exist" in error_msg
                or "not found" in error_msg
                or "404" in error_msg
                or "invalidcollection" in error_msg  # ChromaDB specific error
            ):
                is_not_found = True

            # Check for HTTPStatusError with 400/404 status
            if HTTPX_AVAILABLE and isinstance(get_error, HTTPStatusError):
                if get_error.response.status_code in (400, 404):
                    is_not_found = True
            elif hasattr(get_error, "response"):
                status_code = getattr(get_error.response, "status_code", None)
                if status_code in (400, 404):
                    is_not_found = True

            # If we should create the collection and it doesn't exist
            if create_if_missing and is_not_found:
                # Create new collection since it doesn't exist
                try:
                    # ChromaDB 0.5.x compatibility: avoid passing any metadata
                    # The server has issues with client version mismatch
                    logger.debug(
                        f"Creating collection '{name}' without metadata for "
                        f"ChromaDB 0.5.x compatibility"
                    )

                    # Create the collection with retry logic for transient failures
                    max_retries = 3
                    retry_delay = 1.0

                    for attempt in range(max_retries):
                        try:
                            collection = self.client.create_collection(
                                name=name
                                # Omit metadata for ChromaDB 0.5.x compatibility
                            )
                            break  # Success, exit retry loop
                        except Exception as retry_error:
                            if attempt < max_retries - 1:
                                logger.warning(
                                    f"Collection creation attempt {attempt + 1} "
                                    f"failed: {retry_error}. Retrying in "
                                    f"{retry_delay}s..."
                                )
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                            else:
                                # Final attempt failed, raise the error
                                raise retry_error

                    logger.info(
                        f"Successfully created new collection: {name} "
                        f"(id: {getattr(collection, 'id', 'unknown')})"
                    )
                    return collection

                except Exception as create_error:
                    # Log detailed error information for debugging
                    logger.error(
                        f"Failed to create collection '{name}': "
                        f"Type: {type(create_error).__name__}, "
                        f"Message: {str(create_error)}"
                    )

                    # Check if it's a UniqueConstraintError (collection already exists)
                    # This can happen in race conditions
                    is_already_exists = "already exists" in str(create_error).lower()
                    if CHROMADB_AVAILABLE:
                        is_already_exists = is_already_exists or isinstance(
                            create_error, UniqueConstraintError
                        )

                    if is_already_exists:
                        # Try to get the collection again - it might have been created
                        # by another process in a race condition
                        try:
                            collection = self.client.get_collection(name)
                            logger.info(
                                f"Collection '{name}' already exists (race condition), "
                                "retrieved successfully"
                            )
                            return collection
                        except Exception as retry_error:
                            # If we still can't get it, raise the original error
                            logger.debug(
                                f"Failed to get collection after race condition: "
                                f"{retry_error}"
                            )

                    # Extract more specific error details
                    error_details = {
                        "collection_name": name,
                        "error_type": type(create_error).__name__,
                        "get_error": str(get_error),
                        "create_error": str(create_error),
                        "api_version": self._version_info.version
                        if self._version_info
                        else None,
                    }

                    # Add HTTP status code if available
                    if HTTPX_AVAILABLE and isinstance(create_error, HTTPStatusError):
                        error_details["http_status"] = str(
                            create_error.response.status_code
                        )
                        error_details["http_response"] = str(
                            create_error.response.text
                        )[:500]
                        error_details["request_url"] = str(create_error.request.url)

                    # Add client state information for debugging
                    error_details["client_connected"] = str(self._connection_validated)
                    error_details["host"] = self.config.host
                    error_details["port"] = str(self.config.port)

                    raise ChromaDBError(
                        f"Failed to create collection '{name}': {str(create_error)}",
                        error_code=1414,
                        context=error_details,
                        cause=create_error,
                    ) from create_error

            # Not creating or different error - re-raise
            if not isinstance(get_error, ChromaDBError):
                raise ChromaDBError(
                    f"Failed to get collection: {name}",
                    error_code=1413,
                    context={
                        "collection_name": name,
                        "api_version": self._version_info.version
                        if self._version_info
                        else None,
                    },
                    cause=get_error,
                ) from get_error
            raise get_error

    def bulk_insert(
        self,
        collection: Any,
        chunks: list[DocumentChunk],  # chromadb.Collection
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

            # Batch size for ChromaDB inserts (to avoid payload size limits)
            batch_size = 100  # Process chunks in batches of 100

            total_inserted = 0
            collection_name = getattr(collection, "name", "unknown")

            # Process chunks in batches
            for batch_start in range(0, len(chunks), batch_size):
                batch_end = min(batch_start + batch_size, len(chunks))
                batch_chunks = chunks[batch_start:batch_end]

                # Prepare data for insertion
                ids = [
                    chunk.id or f"chunk_{batch_start + i}"
                    for i, chunk in enumerate(batch_chunks)
                ]
                documents = [chunk.content for chunk in batch_chunks]

                # Sanitize metadata for ChromaDB compatibility
                metadatas = []
                for chunk in batch_chunks:
                    sanitized_metadata = (
                        self._metadata_extractor.sanitize_metadata_for_chromadb(
                            chunk.metadata
                        )
                    )
                    metadatas.append(sanitized_metadata)

                # Add API version info to metadata
                if self._version_info:
                    for metadata in metadatas:
                        metadata["api_version"] = self._version_info.version
                        if self._version_info.chromadb_version:
                            metadata["chromadb_version"] = (
                                self._version_info.chromadb_version
                            )

                # Validate data before insertion
                self._validate_insertion_data(ids, documents, metadatas)

                # Insert batch into collection
                collection.add(
                    ids=ids, documents=documents, metadatas=cast(Any, metadatas)
                )

                total_inserted += len(batch_chunks)

                # Log progress for large batches
                if len(chunks) > batch_size:
                    logger.debug(
                        f"Inserted batch {batch_start // batch_size + 1} "
                        f"({total_inserted}/{len(chunks)} chunks)"
                    )

            processing_time = time.time() - start_time

            api_version = (
                self._version_info.version if self._version_info else "unknown"
            )
            logger.info(
                f"Inserted {total_inserted} chunks into '{collection_name}' "
                f"in {processing_time:.2f}s using {api_version} API"
            )

            return InsertResult(
                success=True,
                chunks_inserted=total_inserted,
                processing_time=processing_time,
                collection_name=collection_name,
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
                context={
                    "operation": "list_collections",
                    "api_version": self._version_info.version
                    if self._version_info
                    else None,
                },
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
                context={
                    "collection_name": name,
                    "api_version": self._version_info.version
                    if self._version_info
                    else None,
                },
                cause=e,
            ) from e

    def test_connection(self) -> bool:
        """Test connection to ChromaDB with version detection.

        Returns:
            True if connection test successful
        """
        try:
            return self.version_detector.test_connection(self._version_info)
        except Exception as e:
            logger.debug(f"Connection test failed: {e}")
            return False

    def _get_client_settings(self) -> dict[str, Any]:
        """Get client settings based on detected API version.

        Returns:
            Dict of client settings
        """
        settings = {
            "host": self.config.host,
            "port": self.config.port,
            "ssl": self.config.ssl,
            "headers": self._get_auth_headers(),
        }

        # Add version-specific settings if needed
        if self._version_info:
            # Future: Add version-specific client configurations here
            pass

        return settings

    def _test_heartbeat(self) -> None:
        """Test heartbeat with version-aware approach.

        Raises:
            ChromaDBError: If heartbeat fails
        """
        try:
            if self.client:
                # Standard ChromaDB client heartbeat
                self.client.heartbeat()
            else:
                # Fallback to version detector
                if not self.version_detector.test_connection(self._version_info):
                    raise ChromaDBError(
                        "Heartbeat test failed",
                        error_code=1403,
                        context={
                            "host": self.config.host,
                            "port": self.config.port,
                            "api_version": self._version_info.version
                            if self._version_info
                            else None,
                        },
                    )
        except Exception as e:
            if not isinstance(e, ChromaDBError):
                raise ChromaDBError(
                    f"Heartbeat failed: {e}",
                    error_code=1403,
                    context={
                        "host": self.config.host,
                        "port": self.config.port,
                        "api_version": self._version_info.version
                        if self._version_info
                        else None,
                    },
                    cause=e,
                ) from e
            raise

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
            ) from e
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
            ) from e

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
        if len({len(ids), len(documents), len(metadatas)}) > 1:
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
