"""Tests for ChromaDB client functionality - Mock-Free Implementation."""

import shutil
import tempfile
from typing import Any

import pytest


# Use real ChromaDB for testing
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    pytest.skip("ChromaDB not available", allow_module_level=True)

from shard_markdown.chromadb.client import ChromaDBClient
from shard_markdown.config import Settings
from shard_markdown.core.models import DocumentChunk
from shard_markdown.utils.errors import ChromaDBError


@pytest.fixture
def temp_db_path():
    """Create a temporary directory for ChromaDB testing."""
    temp_dir = tempfile.mkdtemp(prefix="chromadb_test_")
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def embedded_chromadb(temp_db_path):
    """Create an embedded ChromaDB client for testing."""
    # Use persistent client with temp directory for isolation
    client = chromadb.PersistentClient(
        path=temp_db_path,
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True,
        ),
    )
    yield client
    # Cleanup - reset database
    try:
        client.reset()
    except Exception:  # noqa: S110
        pass  # Cleanup errors are expected and can be safely ignored


@pytest.fixture
def test_config() -> Settings:
    """Create test configuration for ChromaDB.

    Note: We'll use embedded ChromaDB, so host/port don't matter for most tests.
    """
    return Settings(
        chroma_host="localhost",
        chroma_port=8000,
        chroma_ssl=False,
        chroma_timeout=5.0,
        chroma_auth_token=None,
    )


@pytest.fixture
def client_with_embedded_db(test_config, embedded_chromadb):
    """Create a ChromaDBClient that uses embedded database.

    This is a simplified version that bypasses network connection
    and uses embedded ChromaDB directly.
    """
    client = ChromaDBClient(test_config)
    # Directly assign the embedded client for testing
    client.client = embedded_chromadb
    client._connection_validated = True
    return client


class TestChromaDBClientInit:
    """Test ChromaDB client initialization."""

    def test_init_with_config(self, test_config: Settings) -> None:
        """Test client initialization with configuration."""
        client = ChromaDBClient(test_config)

        assert client.config == test_config
        assert client.client is None
        assert client._connection_validated is False


class TestChromaDBClientCollections:
    """Test ChromaDB client collection operations with real database."""

    def test_get_collection_not_connected(self, test_config: Settings) -> None:
        """Test get_collection when not connected."""
        client = ChromaDBClient(test_config)

        with pytest.raises(ChromaDBError) as exc_info:
            client.get_collection("test_collection")

        assert exc_info.value.error_code == 1400
        assert "ChromaDB connection not established" in str(exc_info.value)

    def test_get_collection_success(
        self, client_with_embedded_db: ChromaDBClient
    ) -> None:
        """Test successful get_collection with real ChromaDB."""
        client = client_with_embedded_db

        # Create a real collection
        assert client.client is not None  # Type guard for mypy
        client.client.create_collection("test_collection")

        # Get the collection through our client
        result = client.get_collection("test_collection")

        assert result is not None
        assert result.name == "test_collection"

    def test_get_collection_not_exists(
        self, client_with_embedded_db: ChromaDBClient
    ) -> None:
        """Test get_collection when collection doesn't exist."""
        client = client_with_embedded_db

        # Try to get non-existent collection
        expected_match = "Collection 'nonexistent' does not exist"
        with pytest.raises(ChromaDBError, match=expected_match):
            client.get_collection("nonexistent")

    def test_get_or_create_collection_existing(
        self, client_with_embedded_db: ChromaDBClient
    ) -> None:
        """Test get_or_create_collection with existing collection."""
        client = client_with_embedded_db

        # Create a collection first
        assert client.client is not None  # Type guard for mypy
        client.client.create_collection("existing_collection")

        # Get or create should return the existing one
        result = client.get_or_create_collection("existing_collection")

        assert result is not None
        assert result.name == "existing_collection"

    def test_get_or_create_collection_create_new(
        self, client_with_embedded_db: ChromaDBClient
    ) -> None:
        """Test get_or_create_collection with new collection creation."""
        client = client_with_embedded_db

        # This collection doesn't exist yet
        result = client.get_or_create_collection(
            "new_collection", create_if_missing=True
        )

        assert result is not None
        assert result.name == "new_collection"

        # Verify it was actually created
        assert client.client is not None  # Type guard for mypy
        collections = client.client.list_collections()
        collection_names = [c.name for c in collections]
        assert "new_collection" in collection_names

    def test_list_collections_not_connected(self, test_config: Settings) -> None:
        """Test list_collections when not connected."""
        client = ChromaDBClient(test_config)

        with pytest.raises(ChromaDBError) as exc_info:
            client.list_collections()

        assert exc_info.value.error_code == 1400
        assert "ChromaDB connection not established" in str(exc_info.value)

    def test_list_collections_success(
        self, client_with_embedded_db: ChromaDBClient
    ) -> None:
        """Test successful list_collections with real ChromaDB."""
        client = client_with_embedded_db

        # Create some real collections
        assert client.client is not None  # Type guard for mypy
        client.client.create_collection(
            "collection1", metadata={"description": "Test collection 1"}
        )
        client.client.create_collection(
            "collection2", metadata={"description": "Test collection 2"}
        )

        # Add some documents to collections
        assert client.client is not None  # Type guard for mypy
        col1 = client.client.get_collection("collection1")
        col1.add(ids=["doc1", "doc2"], documents=["Test doc 1", "Test doc 2"])

        result = client.list_collections()

        assert len(result) >= 2

        # Find our test collections in results
        col1_info = next((c for c in result if c["name"] == "collection1"), None)
        col2_info = next((c for c in result if c["name"] == "collection2"), None)

        assert col1_info is not None
        assert col1_info["count"] == 2
        assert col2_info is not None
        assert col2_info["count"] == 0

    def test_delete_collection_not_connected(self, test_config: Settings) -> None:
        """Test delete_collection when not connected."""
        client = ChromaDBClient(test_config)

        with pytest.raises(ChromaDBError) as exc_info:
            client.delete_collection("test_collection")

        assert exc_info.value.error_code == 1400
        assert "ChromaDB connection not established" in str(exc_info.value)

    def test_delete_collection_success(
        self, client_with_embedded_db: ChromaDBClient
    ) -> None:
        """Test successful delete_collection with real ChromaDB."""
        client = client_with_embedded_db

        # Create a collection to delete
        assert client.client is not None  # Type guard for mypy
        client.client.create_collection("to_delete")

        # Verify it exists
        assert client.client is not None  # Type guard for mypy
        collections_before = [c.name for c in client.client.list_collections()]
        assert "to_delete" in collections_before

        # Delete it
        result = client.delete_collection("to_delete")

        assert result is True

        # Verify it's gone
        assert client.client is not None  # Type guard for mypy
        collections_after = [c.name for c in client.client.list_collections()]
        assert "to_delete" not in collections_after


class TestChromaDBClientInsertions:
    """Test ChromaDB client insertion operations with real database."""

    def test_bulk_insert_empty_chunks(
        self, client_with_embedded_db: ChromaDBClient
    ) -> None:
        """Test bulk_insert with empty chunk list."""
        client = client_with_embedded_db

        # Create a real collection
        assert client.client is not None  # Type guard for mypy
        collection = client.client.create_collection("test_collection")

        result = client.bulk_insert(collection, [])

        assert result.success is True
        assert result.chunks_inserted == 0
        assert result.collection_name == "test_collection"

    def test_bulk_insert_success(self, client_with_embedded_db: ChromaDBClient) -> None:
        """Test successful bulk_insert with real ChromaDB."""
        client = client_with_embedded_db

        # Create test chunks
        chunks = [
            DocumentChunk(
                id="chunk_1",
                content="Test content 1",
                metadata={"source": "test1.md", "chunk_index": 0},
                start_index=0,
                end_index=100,
            ),
            DocumentChunk(
                id="chunk_2",
                content="Test content 2",
                metadata={"source": "test2.md", "chunk_index": 1},
                start_index=100,
                end_index=200,
            ),
        ]

        # Create a real collection
        assert client.client is not None  # Type guard for mypy
        collection = client.client.create_collection("test_collection")

        # Perform bulk insert
        result = client.bulk_insert(collection, chunks)

        assert result.success is True
        assert result.chunks_inserted == 2
        assert result.collection_name == "test_collection"

        # Verify data was actually inserted
        stored_data = collection.get()
        assert len(stored_data["ids"]) == 2
        assert "chunk_1" in stored_data["ids"]
        assert "chunk_2" in stored_data["ids"]

        # Verify content
        doc_map = dict(zip(stored_data["ids"], stored_data["documents"], strict=False))
        assert doc_map["chunk_1"] == "Test content 1"
        assert doc_map["chunk_2"] == "Test content 2"

    def test_validate_insertion_data_mismatched_lengths(
        self, test_config: Settings
    ) -> None:
        """Test _validate_insertion_data with mismatched lengths."""
        client = ChromaDBClient(test_config)

        ids = ["id1", "id2"]
        documents = ["doc1"]  # Different length
        metadatas = [{"key": "value1"}, {"key": "value2"}]

        with pytest.raises(ChromaDBError) as exc_info:
            client._validate_insertion_data(ids, documents, metadatas)

        assert exc_info.value.error_code == 1430
        assert "Mismatched lengths" in str(exc_info.value)

    def test_validate_insertion_data_duplicate_ids(self, test_config: Settings) -> None:
        """Test _validate_insertion_data with duplicate IDs."""
        client = ChromaDBClient(test_config)

        ids = ["id1", "id1"]  # Duplicate IDs
        documents = ["doc1", "doc2"]
        metadatas = [{"key": "value1"}, {"key": "value2"}]

        with pytest.raises(ChromaDBError) as exc_info:
            client._validate_insertion_data(ids, documents, metadatas)

        assert exc_info.value.error_code == 1431
        assert "Duplicate IDs found" in str(exc_info.value)

    def test_validate_insertion_data_empty_documents(
        self, test_config: Settings
    ) -> None:
        """Test _validate_insertion_data with empty documents."""
        client = ChromaDBClient(test_config)

        ids = ["id1", "id2"]
        documents = ["doc1", "   "]  # Empty document (whitespace only)
        metadatas = [{"key": "value1"}, {"key": "value2"}]

        with pytest.raises(ChromaDBError) as exc_info:
            client._validate_insertion_data(ids, documents, metadatas)

        assert exc_info.value.error_code == 1432
        assert "Empty documents found" in str(exc_info.value)

    def test_validate_insertion_data_success(self, test_config: Settings) -> None:
        """Test _validate_insertion_data with valid data."""
        client = ChromaDBClient(test_config)

        ids = ["id1", "id2"]
        documents = ["doc1", "doc2"]
        metadatas = [{"key": "value1"}, {"key": "value2"}]

        # Should not raise any exception
        client._validate_insertion_data(ids, documents, metadatas)


class TestChromaDBClientQueries:
    """Test ChromaDB client query operations with real database."""

    def test_query_collection_with_real_data(
        self, client_with_embedded_db: ChromaDBClient
    ) -> None:
        """Test querying a collection with real ChromaDB."""
        client = client_with_embedded_db

        # Create and populate a collection
        assert client.client is not None  # Type guard for mypy
        collection = client.client.create_collection("query_test")

        # Add real documents
        collection.add(
            ids=["doc1", "doc2", "doc3"],
            documents=[
                "The quick brown fox jumps over the lazy dog",
                "Python is a great programming language",
                "ChromaDB is a vector database for AI applications",
            ],
            metadatas=[
                {"type": "phrase", "language": "en"},
                {"type": "tech", "language": "en"},
                {"type": "tech", "language": "en"},
            ],
        )

        # Perform real query
        results = collection.query(query_texts=["programming"], n_results=2)

        assert len(results["ids"][0]) <= 2
        assert "doc2" in results["ids"][0]  # Should find the Python document

    def test_collection_persistence(self, temp_db_path: str) -> None:
        """Test that collections persist across client instances."""
        # Create first client and add data
        client1 = chromadb.PersistentClient(path=temp_db_path)
        collection1 = client1.create_collection("persistent_test")
        collection1.add(ids=["persist1"], documents=["This data should persist"])

        # Create second client with same path
        client2 = chromadb.PersistentClient(path=temp_db_path)
        collection2 = client2.get_collection("persistent_test")

        # Verify data persisted
        data = collection2.get()
        assert len(data["ids"]) == 1
        assert data["ids"][0] == "persist1"
        assert data["documents"][0] == "This data should persist"


class TestChromaDBIntegration:
    """Integration tests using real ChromaDB operations."""

    def test_complete_workflow(self, client_with_embedded_db: ChromaDBClient) -> None:
        """Test complete workflow: create, insert, query, delete."""
        client = client_with_embedded_db

        # Step 1: Create collection
        collection = client.get_or_create_collection(
            "workflow_test", create_if_missing=True
        )
        assert collection is not None

        # Step 2: Insert chunks
        chunks = [
            DocumentChunk(
                id=f"chunk_{i}",
                content=f"Document content {i}",
                metadata={"index": i, "source": f"doc{i}.md"},
                start_index=i * 100,
                end_index=(i + 1) * 100,
            )
            for i in range(5)
        ]

        result = client.bulk_insert(collection, chunks)
        assert result.success
        assert result.chunks_inserted == 5

        # Step 3: Query the collection
        query_results = collection.query(query_texts=["Document content"], n_results=3)
        assert len(query_results["ids"][0]) == 3

        # Step 4: List collections
        collections = client.list_collections()
        assert any(c["name"] == "workflow_test" for c in collections)

        # Step 5: Delete collection
        deleted = client.delete_collection("workflow_test")
        assert deleted is True

        # Verify deletion
        collections_after = client.list_collections()
        assert not any(c["name"] == "workflow_test" for c in collections_after)

    def test_error_handling_with_real_chromadb(
        self, client_with_embedded_db: ChromaDBClient
    ) -> None:
        """Test error handling with real ChromaDB operations."""
        client = client_with_embedded_db

        # Test duplicate collection creation
        assert client.client is not None  # Type guard for mypy
        client.client.create_collection("duplicate_test")

        # This should handle the error gracefully
        # ChromaDB raises an InternalError for duplicate collections
        from chromadb.errors import InternalError

        with pytest.raises(InternalError):
            client.client.create_collection("duplicate_test")

        # Test invalid query
        collection = client.client.get_collection("duplicate_test")

        # Empty query should work but return no results
        results = collection.query(query_texts=[""], n_results=1)
        assert results is not None  # Should handle gracefully


# Performance comparison test (optional, can be run separately)
@pytest.mark.benchmark
class TestPerformanceComparison:
    """Compare performance of mock-free tests vs mocked tests."""

    def test_insert_performance(
        self, client_with_embedded_db: ChromaDBClient, benchmark: Any
    ) -> None:
        """Benchmark real ChromaDB insertions."""
        client = client_with_embedded_db
        assert client.client is not None  # Type guard for mypy
        collection = client.client.create_collection("perf_test")

        chunks = [
            DocumentChunk(
                id=f"perf_{i}",
                content=f"Performance test content {i}",
                metadata={"index": i},
                start_index=i * 100,
                end_index=(i + 1) * 100,
            )
            for i in range(10)
        ]

        def insert_chunks():
            return client.bulk_insert(collection, chunks)

        result = benchmark(insert_chunks)
        assert result.success

        # Clean up
        assert client.client is not None  # Type guard for mypy
        client.client.delete_collection("perf_test")
