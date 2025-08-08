"""Collection management operations."""

from typing import Any

from ..utils.errors import ChromaDBError
from ..utils.logging import get_logger
from .protocol import ChromaDBClientProtocol


logger = get_logger(__name__)


class CollectionManager:
    """High-level collection management operations."""

    def __init__(self, client: ChromaDBClientProtocol) -> None:
        """Initialize collection manager.

        Args:
            client: ChromaDB client instance (real or mock)
        """
        self.client = client

    def create_collection(
        self,
        name: str,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Create a new collection with validation.

        Args:
            name: Collection name
            description: Optional description
            metadata: Optional additional metadata

        Returns:
            Created ChromaDB Collection

        Raises:
            ChromaDBError: If creation fails
        """
        # Validate collection name
        self._validate_collection_name(name)

        # Prepare metadata
        collection_metadata = metadata or {}
        if description:
            collection_metadata["description"] = description

        try:
            # Use get_or_create_collection with create_if_missing=True
            collection = self.client.get_or_create_collection(
                name, create_if_missing=True, metadata=collection_metadata
            )
            logger.info(
                f"Created collection '{name}' with metadata: {collection_metadata}"
            )
            return collection

        except (ValueError, RuntimeError, KeyError, AttributeError) as e:
            raise ChromaDBError(
                f"Failed to create collection '{name}': {str(e)}",
                error_code=1420,
                context={"name": name, "metadata": collection_metadata},
                cause=e,
            ) from e

    def get_collection(self, name: str) -> Any:
        """Get existing collection.

        Args:
            name: Collection name

        Returns:
            ChromaDB Collection

        Raises:
            ChromaDBError: If collection doesn't exist
        """
        try:
            return self.client.get_collection(name)

        except (ValueError, RuntimeError, KeyError, AttributeError) as e:
            raise ChromaDBError(
                f"Collection '{name}' not found: {str(e)}",
                error_code=1421,
                context={"name": name},
                cause=e,
            ) from e

    def list_collections(self) -> list[dict[str, Any]]:
        """List all collections with metadata.

        Returns:
            List of collection information dictionaries

        Raises:
            ChromaDBError: If listing fails
        """
        try:
            collections_data = self.client.list_collections()
            return collections_data

        except (ValueError, RuntimeError, KeyError, AttributeError) as e:
            raise ChromaDBError(
                f"Failed to list collections: {str(e)}",
                error_code=1422,
                context={"operation": "list_collections"},
                cause=e,
            ) from e

    def delete_collection(self, name: str) -> bool:
        """Delete a collection.

        Args:
            name: Collection name to delete

        Returns:
            True if deleted successfully

        Raises:
            ChromaDBError: If deletion fails
        """
        try:
            result = self.client.delete_collection(name)
            logger.info("Deleted collection '%s'", name)
            return result if result is not None else True

        except (ValueError, RuntimeError, KeyError, AttributeError) as e:
            raise ChromaDBError(
                f"Failed to delete collection '{name}': {str(e)}",
                error_code=1423,
                context={"name": name},
                cause=e,
            ) from e

    def collection_exists(self, name: str) -> bool:
        """Check if a collection exists.

        Args:
            name: Collection name to check

        Returns:
            True if collection exists, False otherwise
        """
        try:
            # Try to list collections and check if name is in the list
            # This is more reliable than trying to get a collection that might not exist
            collections = self.list_collections()
            return any(col["name"] == name for col in collections)
        except ChromaDBError:
            # If we can't list collections, fall back to trying to get the collection
            try:
                self.get_collection(name)
                return True
            except ChromaDBError:
                return False

    def clear_collection(self, name: str) -> bool:
        """Clear all documents from a collection.

        Args:
            name: Collection name to clear

        Returns:
            True if cleared successfully

        Raises:
            ChromaDBError: If clearing fails
        """
        try:
            # For mock client, this might not be implemented
            if hasattr(self.client, "clear_collection"):
                self.client.clear_collection(name)
            else:
                # Fallback: delete and recreate collection
                collection = self.get_collection(name)
                metadata = getattr(collection, "metadata", {})
                self.delete_collection(name)
                self.create_collection(name, metadata=metadata)

            logger.info("Cleared collection '%s'", name)
            return True

        except (ValueError, RuntimeError, KeyError, AttributeError) as e:
            raise ChromaDBError(
                f"Failed to clear collection '{name}': {str(e)}",
                error_code=1424,
                context={"name": name},
                cause=e,
            ) from e

    def get_collection_info(self, name: str) -> dict[str, Any]:
        """Get detailed information about a collection.

        Args:
            name: Collection name

        Returns:
            Dictionary with collection information

        Raises:
            ChromaDBError: If collection doesn't exist
        """
        collection = self.get_collection(name)

        try:
            count = collection.count() if hasattr(collection, "count") else 0
            metadata = getattr(collection, "metadata", {})

            return {"name": name, "count": count, "metadata": metadata}

        except (ValueError, RuntimeError, KeyError, AttributeError) as e:
            raise ChromaDBError(
                f"Failed to get collection info for '{name}': {str(e)}",
                error_code=1425,
                context={"name": name},
                cause=e,
            ) from e

    def _validate_collection_name(self, name: str) -> None:
        """Validate collection name.

        Args:
            name: Collection name to validate

        Raises:
            ChromaDBError: If name is invalid
        """
        if not name or not name.strip():
            raise ChromaDBError(
                "Collection name cannot be empty",
                error_code=1411,
                context={"name": name},
            )

        if len(name.strip()) > 63:
            raise ChromaDBError(
                f"Collection name too long: {name} (max 63 characters)",
                error_code=1412,
                context={"name": name, "length": len(name.strip())},
            )

        # Check for invalid characters (basic validation)
        invalid_chars = set(name) - set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        )
        if invalid_chars:
            raise ChromaDBError(
                f"Collection name contains invalid characters: {invalid_chars}",
                error_code=1413,
                context={"name": name, "invalid_chars": list(invalid_chars)},
            )
