"""Protocol for ChromaDB client interface."""

from typing import Protocol

from ..core.models import DocumentChunk, InsertResult
from ..types import ChromaClientProtocol, ChromaCollectionProtocol, MetadataDict


class ChromaDBClientProtocol(Protocol):
    """Protocol defining the interface for ChromaDB clients.

    This protocol ensures both real and mock ChromaDB clients
    implement the same interface for type safety.
    """

    # Internal attributes that ChromaDBOperations needs
    _connection_validated: bool
    client: ChromaClientProtocol | None  # The actual ChromaDB client instance

    def connect(self) -> bool:
        """Establish connection to ChromaDB instance.

        Returns:
            True if connection successful, False otherwise
        """
        ...

    def get_collection(self, name: str) -> ChromaCollectionProtocol:
        """Get existing collection.

        Args:
            name: Collection name

        Returns:
            Collection object

        Raises:
            Exception: If collection doesn't exist
        """
        ...

    def get_or_create_collection(
        self,
        name: str,
        create_if_missing: bool = False,
        metadata: MetadataDict | None = None,
    ) -> ChromaCollectionProtocol:
        """Get existing or create new collection.

        Args:
            name: Collection name
            create_if_missing: Whether to create collection if it doesn't exist
            metadata: Optional metadata for new collections

        Returns:
            Collection object
        """
        ...

    def bulk_insert(
        self, collection: ChromaCollectionProtocol, chunks: list[DocumentChunk]
    ) -> InsertResult:
        """Bulk insert chunks into collection.

        Args:
            collection: Target collection
            chunks: List of document chunks to insert

        Returns:
            InsertResult with operation details
        """
        ...

    def list_collections(self) -> list[MetadataDict]:
        """List all available collections.

        Returns:
            List of collection information dictionaries
        """
        ...

    def delete_collection(self, name: str) -> bool | None:
        """Delete a collection.

        Args:
            name: Collection name to delete

        Returns:
            True if deletion successful, or None for mock implementation
        """
        ...
