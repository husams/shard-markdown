"""Unit tests for CollectionManager class."""

from unittest.mock import Mock

import pytest

from shard_markdown.chromadb.collections import CollectionManager
from shard_markdown.chromadb.protocol import ChromaDBClientProtocol
from shard_markdown.utils.errors import ChromaDBError


@pytest.fixture
def mock_client() -> Mock:
    """Create mock ChromaDB client."""
    return Mock(spec=ChromaDBClientProtocol)


@pytest.fixture
def collection_manager(mock_client: Mock) -> CollectionManager:
    """Create CollectionManager instance with mock client."""
    return CollectionManager(mock_client)


@pytest.fixture
def mock_collection() -> Mock:
    """Create mock collection object."""
    collection = Mock()
    collection.name = "test_collection"
    collection.metadata = {"description": "Test collection"}
    collection.count.return_value = 42
    return collection


class TestCollectionManager:
    """Test cases for CollectionManager class."""

    def test_init(self, mock_client: Mock) -> None:
        """Test CollectionManager initialization."""
        manager = CollectionManager(mock_client)
        assert manager.client == mock_client

    def test_create_collection_success(
        self,
        collection_manager: CollectionManager,
        mock_client: Mock,
        mock_collection: Mock,
    ) -> None:
        """Test successful collection creation."""
        mock_client.get_or_create_collection.return_value = mock_collection

        result = collection_manager.create_collection(
            "test_collection", "Test description"
        )

        assert result == mock_collection
        mock_client.get_or_create_collection.assert_called_once_with(
            "test_collection",
            create_if_missing=True,
            metadata={"description": "Test description"},
        )

    def test_create_collection_with_metadata(
        self,
        collection_manager: CollectionManager,
        mock_client: Mock,
        mock_collection: Mock,
    ) -> None:
        """Test collection creation with custom metadata."""
        custom_metadata = {"type": "document", "version": "1.0"}
        mock_client.get_or_create_collection.return_value = mock_collection

        result = collection_manager.create_collection(
            "test_collection", "Test description", custom_metadata
        )

        assert result == mock_collection
        expected_metadata = {
            "type": "document",
            "version": "1.0",
            "description": "Test description",
        }
        mock_client.get_or_create_collection.assert_called_once_with(
            "test_collection", create_if_missing=True, metadata=expected_metadata
        )

    def test_create_collection_no_description(
        self,
        collection_manager: CollectionManager,
        mock_client: Mock,
        mock_collection: Mock,
    ) -> None:
        """Test collection creation without description."""
        mock_client.get_or_create_collection.return_value = mock_collection

        result = collection_manager.create_collection("test_collection")

        assert result == mock_collection
        mock_client.get_or_create_collection.assert_called_once_with(
            "test_collection", create_if_missing=True, metadata={}
        )

    def test_create_collection_failure(
        self, collection_manager: CollectionManager, mock_client: Mock
    ) -> None:
        """Test collection creation failure."""
        mock_client.get_or_create_collection.side_effect = ValueError("Creation failed")

        with pytest.raises(ChromaDBError, match="Failed to create collection"):
            collection_manager.create_collection("test_collection")

    def test_create_collection_invalid_name_empty(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection creation with empty name."""
        with pytest.raises(ChromaDBError, match="Collection name cannot be empty"):
            collection_manager.create_collection("")

    def test_create_collection_invalid_name_whitespace(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection creation with whitespace-only name."""
        with pytest.raises(ChromaDBError, match="Collection name cannot be empty"):
            collection_manager.create_collection("   ")

    def test_create_collection_invalid_name_too_long(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection creation with name too long."""
        long_name = "a" * 64  # 64 characters, max is 63
        with pytest.raises(ChromaDBError, match="Collection name too long"):
            collection_manager.create_collection(long_name)

    def test_create_collection_invalid_name_invalid_chars(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection creation with invalid characters."""
        with pytest.raises(
            ChromaDBError, match="Collection name contains invalid characters"
        ):
            collection_manager.create_collection("test@collection!")

    def test_get_collection_success(
        self,
        collection_manager: CollectionManager,
        mock_client: Mock,
        mock_collection: Mock,
    ) -> None:
        """Test successful collection retrieval."""
        mock_client.get_collection.return_value = mock_collection

        result = collection_manager.get_collection("test_collection")

        assert result == mock_collection
        mock_client.get_collection.assert_called_once_with("test_collection")

    def test_get_collection_not_found(
        self, collection_manager: CollectionManager, mock_client: Mock
    ) -> None:
        """Test collection retrieval when collection doesn't exist."""
        mock_client.get_collection.side_effect = ValueError("Collection not found")

        with pytest.raises(
            ChromaDBError, match="Collection 'test_collection' not found"
        ):
            collection_manager.get_collection("test_collection")

    def test_list_collections_success(
        self, collection_manager: CollectionManager, mock_client: Mock
    ) -> None:
        """Test successful collection listing."""
        expected_collections = [
            {"name": "collection1", "count": 10, "metadata": {"type": "test"}},
            {"name": "collection2", "count": 25, "metadata": {"type": "production"}},
        ]
        mock_client.list_collections.return_value = expected_collections

        result = collection_manager.list_collections()

        assert result == expected_collections
        mock_client.list_collections.assert_called_once()

    def test_list_collections_failure(
        self, collection_manager: CollectionManager, mock_client: Mock
    ) -> None:
        """Test collection listing failure."""
        mock_client.list_collections.side_effect = RuntimeError("Listing failed")

        with pytest.raises(ChromaDBError, match="Failed to list collections"):
            collection_manager.list_collections()

    def test_delete_collection_success(
        self, collection_manager: CollectionManager, mock_client: Mock
    ) -> None:
        """Test successful collection deletion."""
        mock_client.delete_collection.return_value = True

        result = collection_manager.delete_collection("test_collection")

        assert result is True
        mock_client.delete_collection.assert_called_once_with("test_collection")

    def test_delete_collection_returns_none(
        self, collection_manager: CollectionManager, mock_client: Mock
    ) -> None:
        """Test collection deletion when client returns None."""
        mock_client.delete_collection.return_value = None

        result = collection_manager.delete_collection("test_collection")

        assert result is True
        mock_client.delete_collection.assert_called_once_with("test_collection")

    def test_delete_collection_failure(
        self, collection_manager: CollectionManager, mock_client: Mock
    ) -> None:
        """Test collection deletion failure."""
        mock_client.delete_collection.side_effect = ValueError("Deletion failed")

        with pytest.raises(ChromaDBError, match="Failed to delete collection"):
            collection_manager.delete_collection("test_collection")

    def test_collection_exists_true(
        self,
        collection_manager: CollectionManager,
        mock_client: Mock,
        mock_collection: Mock,
    ) -> None:
        """Test collection_exists returns True when collection exists."""
        mock_client.get_collection.return_value = mock_collection

        result = collection_manager.collection_exists("test_collection")

        assert result is True
        mock_client.get_collection.assert_called_once_with("test_collection")

    def test_collection_exists_false(
        self, collection_manager: CollectionManager, mock_client: Mock
    ) -> None:
        """Test collection_exists returns False when collection doesn't exist."""
        mock_client.get_collection.side_effect = ChromaDBError("Collection not found")

        result = collection_manager.collection_exists("test_collection")

        assert result is False
        mock_client.get_collection.assert_called_once_with("test_collection")

    def test_clear_collection_with_clear_method(
        self, collection_manager: CollectionManager, mock_client: Mock
    ) -> None:
        """Test collection clearing when client has clear_collection method."""
        mock_client.clear_collection = Mock()

        result = collection_manager.clear_collection("test_collection")

        assert result is True
        mock_client.clear_collection.assert_called_once_with("test_collection")

    def test_clear_collection_fallback_method(
        self,
        collection_manager: CollectionManager,
        mock_client: Mock,
        mock_collection: Mock,
    ) -> None:
        """Test collection clearing using fallback delete/recreate method."""
        # Mock client doesn't have clear_collection method
        mock_client.get_collection.return_value = mock_collection
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client.delete_collection.return_value = True

        result = collection_manager.clear_collection("test_collection")

        assert result is True
        mock_client.get_collection.assert_called_once_with("test_collection")
        mock_client.delete_collection.assert_called_once_with("test_collection")
        mock_client.get_or_create_collection.assert_called_once_with(
            "test_collection", create_if_missing=True, metadata=mock_collection.metadata
        )

    def test_clear_collection_failure(
        self, collection_manager: CollectionManager, mock_client: Mock
    ) -> None:
        """Test collection clearing failure."""
        mock_client.clear_collection = Mock()
        mock_client.clear_collection.side_effect = ValueError("Clear failed")

        with pytest.raises(ChromaDBError, match="Failed to clear collection"):
            collection_manager.clear_collection("test_collection")

    def test_get_collection_info_success(
        self,
        collection_manager: CollectionManager,
        mock_client: Mock,
        mock_collection: Mock,
    ) -> None:
        """Test successful collection info retrieval."""
        mock_client.get_collection.return_value = mock_collection

        result = collection_manager.get_collection_info("test_collection")

        expected_info = {
            "name": "test_collection",
            "count": 42,
            "metadata": {"description": "Test collection"},
        }
        assert result == expected_info
        mock_client.get_collection.assert_called_once_with("test_collection")

    def test_get_collection_info_no_count_method(
        self, collection_manager: CollectionManager, mock_client: Mock
    ) -> None:
        """Test collection info retrieval when collection has no count method."""
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        mock_collection.metadata = {"description": "Test collection"}
        del mock_collection.count  # Remove count method
        mock_client.get_collection.return_value = mock_collection

        result = collection_manager.get_collection_info("test_collection")

        expected_info = {
            "name": "test_collection",
            "count": 0,
            "metadata": {"description": "Test collection"},
        }
        assert result == expected_info

    def test_get_collection_info_no_metadata(
        self, collection_manager: CollectionManager, mock_client: Mock
    ) -> None:
        """Test collection info retrieval when collection has no metadata."""
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        mock_collection.count.return_value = 42
        del mock_collection.metadata  # Remove metadata attribute
        mock_client.get_collection.return_value = mock_collection

        result = collection_manager.get_collection_info("test_collection")

        expected_info = {"name": "test_collection", "count": 42, "metadata": {}}
        assert result == expected_info

    def test_get_collection_info_failure(
        self,
        collection_manager: CollectionManager,
        mock_client: Mock,
        mock_collection: Mock,
    ) -> None:
        """Test collection info retrieval failure."""
        mock_collection.count.side_effect = RuntimeError("Count failed")
        mock_client.get_collection.return_value = mock_collection

        with pytest.raises(ChromaDBError, match="Failed to get collection info"):
            collection_manager.get_collection_info("test_collection")

    def test_validate_collection_name_valid(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection name validation with valid names."""
        valid_names = [
            "test_collection",
            "Collection123",
            "my-collection",
            "collection.backup",
            "a" * 63,  # Exactly 63 characters
        ]

        for name in valid_names:
            # Should not raise any exception
            collection_manager._validate_collection_name(name)

    def test_validate_collection_name_invalid_empty(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection name validation with empty name."""
        with pytest.raises(ChromaDBError, match="Collection name cannot be empty"):
            collection_manager._validate_collection_name("")

    def test_validate_collection_name_invalid_whitespace(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection name validation with whitespace-only name."""
        with pytest.raises(ChromaDBError, match="Collection name cannot be empty"):
            collection_manager._validate_collection_name("   ")

    def test_validate_collection_name_invalid_too_long(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection name validation with name too long."""
        long_name = "a" * 64  # 64 characters, max is 63
        with pytest.raises(ChromaDBError, match="Collection name too long"):
            collection_manager._validate_collection_name(long_name)

    def test_validate_collection_name_invalid_characters(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection name validation with invalid characters."""
        invalid_names = [
            "test@collection",
            "collection!",
            "test collection",  # space
            "collection#1",
            "collection$",
            "collection%",
        ]

        for name in invalid_names:
            with pytest.raises(
                ChromaDBError, match="Collection name contains invalid characters"
            ):
                collection_manager._validate_collection_name(name)
