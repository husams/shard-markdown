"""Async ChromaDB client protocol definition."""

from typing import Any, Protocol

from shard_markdown.core.models import DocumentChunk, InsertResult


class AsyncChromaDBClientProtocol(Protocol):
    """Protocol for async ChromaDB client implementations."""

    async def connect(self) -> None:
        """Establish connection to ChromaDB.

        Raises:
            ConnectionError: If connection fails
        """
        ...

    async def get_collection(self, name: str) -> Any:
        """Get existing collection by name.

        Args:
            name: Collection name

        Returns:
            ChromaDB collection object

        Raises:
            InvalidCollectionError: If collection doesn't exist
        """
        ...

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
        ...

    async def bulk_insert(
        self, collection: Any, chunks: list[DocumentChunk]
    ) -> InsertResult:
        """Bulk insert chunks into collection.

        Args:
            collection: Target ChromaDB collection
            chunks: List of document chunks to insert

        Returns:
            InsertResult with operation details
        """
        ...

    async def list_collections(self) -> list[Any]:
        """List all collections.

        Returns:
            List of ChromaDB collection objects
        """
        ...

    async def delete_collection(self, name: str) -> None:
        """Delete collection by name.

        Args:
            name: Collection name to delete

        Raises:
            InvalidCollectionError: If collection doesn't exist
        """
        ...
