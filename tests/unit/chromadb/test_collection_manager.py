"""Unit tests for CollectionManager class."""

import pytest

from shard_markdown.chromadb.collections import CollectionManager
from shard_markdown.config.settings import ChromaDBConfig
from shard_markdown.utils.errors import ChromaDBError
from tests.fixtures.mock import MockChromaDBClient


def _create_fresh_mock_client() -> MockChromaDBClient:
    """Create a fresh mock client for each test."""
    # Use a unique process identifier to avoid storage conflicts
    import os
    import time

    unique_id = f"{os.getpid()}_{int(time.time() * 1000000)}"

    client = MockChromaDBClient(ChromaDBConfig(host="localhost", port=8000))
    client.connect()
    # Clear any existing collections from shared storage
    client.collections.clear()
    return client


@pytest.fixture
def mock_client() -> MockChromaDBClient:
    """Create mock ChromaDB client."""
    return _create_fresh_mock_client()


@pytest.fixture
def collection_manager() -> CollectionManager:
    """Create CollectionManager instance with fresh mock client."""
    client = _create_fresh_mock_client()
    return CollectionManager(client)


class TestCollectionManager:
    """Test cases for CollectionManager class."""

    def test_init(self, mock_client: MockChromaDBClient) -> None:
        """Test CollectionManager initialization."""
        manager = CollectionManager(mock_client)
        assert manager.client == mock_client

    def test_create_collection_success(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test successful collection creation."""
        result = collection_manager.create_collection(
            "test_collection", "Test description"
        )

        assert result.name == "test_collection"
        assert result.metadata["description"] == "Test description"
        assert "test_collection" in collection_manager.client.collections

    def test_create_collection_with_metadata(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection creation with custom metadata."""
        custom_metadata = {"type": "document", "version": "1.0"}

        result = collection_manager.create_collection(
            "test_collection", "Test description", custom_metadata
        )

        assert result.name == "test_collection"
        # Check that the actual metadata contains all expected keys
        assert result.metadata["description"] == "Test description"
        assert result.metadata["type"] == "document"
        assert result.metadata["version"] == "1.0"

    def test_create_collection_no_description(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection creation without description."""
        result = collection_manager.create_collection("test_collection")

        assert result.name == "test_collection"
        assert result.metadata == {}

    def test_create_collection_already_exists(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection creation when collection already exists."""
        # Create collection first
        first_result = collection_manager.create_collection("test_collection")

        # Creating again should return the same collection (get_or_create behavior)
        second_result = collection_manager.create_collection("test_collection")
        assert first_result == second_result

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
        self, collection_manager: CollectionManager
    ) -> None:
        """Test successful collection retrieval."""
        # Create collection first
        created_collection = collection_manager.create_collection("test_collection")

        result = collection_manager.get_collection("test_collection")

        assert result == created_collection

    def test_get_collection_not_found(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection retrieval when collection doesn't exist."""
        with pytest.raises(
            ChromaDBError, match="Collection 'test_collection' not found"
        ):
            collection_manager.get_collection("test_collection")

    def test_list_collections_success(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test successful collection listing."""
        # Create some collections
        collection_manager.create_collection("collection1", metadata={"type": "test"})
        collection_manager.create_collection(
            "collection2", metadata={"type": "production"}
        )

        result = collection_manager.list_collections()

        assert len(result) == 2
        # Check that both collections are present (order may vary)
        names = [c["name"] for c in result]
        assert "collection1" in names
        assert "collection2" in names

    def test_list_collections_empty(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test listing collections when none exist."""
        result = collection_manager.list_collections()
        assert result == []

    def test_delete_collection_success(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test successful collection deletion."""
        # Create collection first
        collection_manager.create_collection("test_collection")

        result = collection_manager.delete_collection("test_collection")

        assert result is True
        assert "test_collection" not in collection_manager.client.collections

    def test_delete_collection_not_exists(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test deleting collection that doesn't exist."""
        # Mock client returns False for non-existent collection
        result = collection_manager.delete_collection("nonexistent")
        assert result is False  # Mock client returns False for non-existent

    def test_collection_exists_true(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection_exists returns True when collection exists."""
        # Create collection first
        collection_manager.create_collection("test_collection")

        result = collection_manager.collection_exists("test_collection")

        assert result is True

    def test_collection_exists_false(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection_exists returns False when collection doesn't exist."""
        result = collection_manager.collection_exists("test_collection")
        assert result is False

    def test_clear_collection_fallback_method(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection clearing using delete/recreate method."""
        # Create collection with metadata
        original_collection = collection_manager.create_collection(
            "test_collection", metadata={"description": "Test collection"}
        )

        result = collection_manager.clear_collection("test_collection")

        assert result is True
        # Collection should still exist but be empty
        assert "test_collection" in collection_manager.client.collections
        new_collection = collection_manager.client.get_collection("test_collection")
        assert new_collection.count() == 0
        assert new_collection.metadata == original_collection.metadata

    def test_clear_collection_not_exists(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test clearing collection that doesn't exist."""
        with pytest.raises(ChromaDBError, match="Collection 'nonexistent' not found"):
            collection_manager.clear_collection("nonexistent")

    def test_get_collection_info_success(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test successful collection info retrieval."""
        # Create collection with metadata
        collection_manager.create_collection(
            "test_collection", metadata={"description": "Test collection"}
        )

        result = collection_manager.get_collection_info("test_collection")

        expected_info = {
            "name": "test_collection",
            "count": 0,
            "metadata": {"description": "Test collection"},
        }
        assert result == expected_info

    def test_get_collection_info_with_documents(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test collection info retrieval with documents."""
        from shard_markdown.core.models import DocumentChunk

        # Create collection and add some documents
        collection_manager.create_collection(
            "test_collection", metadata={"description": "Test collection"}
        )

        # Get the created collection and add documents
        collection = collection_manager.client.get_collection("test_collection")

        # Add test documents
        chunks = [
            DocumentChunk(
                id="doc1", content="Test document 1", metadata={"source": "test1.md"}
            ),
            DocumentChunk(
                id="doc2", content="Test document 2", metadata={"source": "test2.md"}
            ),
        ]
        collection_manager.client.bulk_insert(collection, chunks)

        result = collection_manager.get_collection_info("test_collection")

        expected_info = {
            "name": "test_collection",
            "count": 2,
            "metadata": {"description": "Test collection"},
        }
        assert result == expected_info

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

    def test_collection_manager_workflow(
        self, collection_manager: CollectionManager
    ) -> None:
        """Test complete workflow to increase mock client coverage."""
        from shard_markdown.core.models import DocumentChunk

        # Create collection
        collection = collection_manager.create_collection(
            "workflow_test",
            "Workflow test collection",
            {"version": "1.0", "type": "test"},
        )
        assert collection.name == "workflow_test"

        # Verify it exists
        assert collection_manager.collection_exists("workflow_test")

        # Get collection info
        info = collection_manager.get_collection_info("workflow_test")
        assert info["count"] == 0
        assert info["metadata"]["description"] == "Workflow test collection"

        # Add documents via bulk insert
        chunks = [
            DocumentChunk(
                id="workflow_doc1",
                content="First workflow document",
                metadata={"type": "workflow", "step": 1},
            ),
            DocumentChunk(
                id="workflow_doc2",
                content="Second workflow document",
                metadata={"type": "workflow", "step": 2},
            ),
        ]

        insert_result = collection_manager.client.bulk_insert(collection, chunks)
        assert insert_result.success
        assert insert_result.chunks_inserted == 2

        # Check updated info
        info = collection_manager.get_collection_info("workflow_test")
        assert info["count"] == 2

        # List collections
        collections = collection_manager.list_collections()
        assert len(collections) == 1
        assert collections[0]["name"] == "workflow_test"
        assert collections[0]["count"] == 2

        # Clear collection
        assert collection_manager.clear_collection("workflow_test")

        # Verify cleared
        info = collection_manager.get_collection_info("workflow_test")
        assert info["count"] == 0

        # Delete collection
        assert collection_manager.delete_collection("workflow_test")

        # Verify deleted
        assert not collection_manager.collection_exists("workflow_test")
