"""Protocol for ChromaDB client interface."""

from typing import Any, Dict, List, Optional, Protocol, Union

from ..core.models import DocumentChunk, InsertResult


class ChromaDBClientProtocol(Protocol):
    """Protocol defining the interface for ChromaDB clients.

    This protocol ensures both real and mock ChromaDB clients
    implement the same interface for type safety.
    """

    def connect(self) -> bool:
        """Establish connection to ChromaDB instance.

        Returns:
            True if connection successful, False otherwise
        """
        ...

    def get_collection(self, name: str) -> Any:
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
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Get existing or create new collection.

        Args:
            name: Collection name
            create_if_missing: Whether to create collection if it doesn't exist
            metadata: Optional metadata for new collections

        Returns:
            Collection object
        """
        ...

    def bulk_insert(self, collection: Any, chunks: List[DocumentChunk]) -> InsertResult:
        """Bulk insert chunks into collection.

        Args:
            collection: Target collection
            chunks: List of document chunks to insert

        Returns:
            InsertResult with operation details
        """
        ...

    def list_collections(self) -> List[Dict[str, Any]]:
        """List all available collections.

        Returns:
            List of collection information dictionaries
        """
        ...

    def delete_collection(self, name: str) -> Union[bool, None]:
        """Delete a collection.

        Args:
            name: Collection name to delete

        Returns:
            True if deletion successful, or None for mock implementation
        """
        ...
