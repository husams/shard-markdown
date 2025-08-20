"""Unit tests for ChromaDBOperations class."""

import uuid
from typing import Any

import pytest

from shard_markdown.chromadb.operations import ChromaDBOperations
from shard_markdown.config.settings import ChromaDBParams
from shard_markdown.core.models import DocumentChunk
from shard_markdown.utils.errors import ChromaDBError
from tests.fixtures.mock import MockChromaDBClient


@pytest.fixture
def mock_chromadb_client() -> MockChromaDBClient:
    """Fixture for a MockChromaDBClient."""
    client = MockChromaDBClient(ChromaDBParams(host="localhost", port=8000))
    # Simulate connection
    client.connect()
    return client


@pytest.fixture
def operations(mock_chromadb_client: MockChromaDBClient) -> ChromaDBOperations:
    """Fixture for ChromaDBOperations with mock client."""
    return ChromaDBOperations(mock_chromadb_client)


@pytest.fixture
def populated_collection() -> dict[str, Any]:
    """Create a collection with sample data for testing."""
    # Create a fresh client for each test to avoid conflicts
    client = MockChromaDBClient(ChromaDBParams(host="localhost", port=8000))
    client.connect()

    collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
    collection = client.create_collection(collection_name)

    # Add sample documents
    sample_chunks = [
        DocumentChunk(
            id="doc1",
            content="This is the first document about testing",
            metadata={"source": "test1.md", "section": "intro"},
        ),
        DocumentChunk(
            id="doc2",
            content="This is the second document with different content",
            metadata={"source": "test2.md", "section": "main"},
        ),
        DocumentChunk(
            id="doc3",
            content="Third document with some testing information",
            metadata={"source": "test3.md", "section": "conclusion"},
        ),
    ]

    client.bulk_insert(collection, sample_chunks)

    return {
        "client": client,
        "collection": collection,
        "collection_name": collection_name,
    }


class TestChromaDBOperations:
    """Test suite for ChromaDBOperations."""

    @pytest.mark.unit
    def test_initialization(
        self, operations: ChromaDBOperations, mock_chromadb_client: MockChromaDBClient
    ) -> None:
        """Test that ChromaDBOperations initializes correctly."""
        assert operations.client == mock_chromadb_client

    @pytest.mark.unit
    def test_query_collection_not_connected(self) -> None:
        """Test query_collection when client is not connected."""
        # Create client without connecting
        client = MockChromaDBClient(ChromaDBParams(host="localhost", port=8000))
        operations = ChromaDBOperations(client)

        with pytest.raises(ChromaDBError, match="ChromaDB connection not established"):
            operations.query_collection("test_collection", "test query")

    @pytest.mark.unit
    def test_query_collection_success(
        self, populated_collection: dict[str, Any]
    ) -> None:
        """Test successful query_collection with mock data."""
        client = populated_collection["client"]
        collection_name = populated_collection["collection_name"]
        operations = ChromaDBOperations(client)

        results = operations.query_collection(collection_name, "testing document")

        assert "total_results" in results
        assert "results" in results
        assert results["total_results"] >= 0
        assert isinstance(results["results"], list)

        # With mock data, we should get some results
        if results["total_results"] > 0:
            result = results["results"][0]
            assert "id" in result
            assert "content" in result
            assert "metadata" in result
            assert "similarity_score" in result

    @pytest.mark.unit
    def test_query_collection_nonexistent(self, operations: ChromaDBOperations) -> None:
        """Test query_collection with non-existent collection."""
        with pytest.raises(ChromaDBError, match="Failed to query collection"):
            operations.query_collection("nonexistent_collection", "test query")

    @pytest.mark.unit
    def test_get_document_not_connected(self) -> None:
        """Test get_document when client is not connected."""
        client = MockChromaDBClient(ChromaDBParams(host="localhost", port=8000))
        operations = ChromaDBOperations(client)

        with pytest.raises(ChromaDBError, match="ChromaDB connection not established"):
            operations.get_document("test_collection", "doc_id")

    @pytest.mark.unit
    def test_get_document_success(self, populated_collection: dict[str, Any]) -> None:
        """Test successful get_document with mock data."""
        client = populated_collection["client"]
        collection_name = populated_collection["collection_name"]
        operations = ChromaDBOperations(client)

        result = operations.get_document(collection_name, "doc1")

        assert result is not None
        assert result["id"] == "doc1"
        assert "content" in result
        assert "metadata" in result
        assert result["content"] == "This is the first document about testing"

    @pytest.mark.unit
    def test_get_document_not_found(self, populated_collection: dict[str, Any]) -> None:
        """Test get_document when document is not found."""
        client = populated_collection["client"]
        collection_name = populated_collection["collection_name"]
        operations = ChromaDBOperations(client)

        result = operations.get_document(collection_name, "nonexistent_doc")
        assert result is None

    @pytest.mark.unit
    def test_list_documents_success(self, populated_collection: dict[str, Any]) -> None:
        """Test successful list_documents with mock data."""
        client = populated_collection["client"]
        collection_name = populated_collection["collection_name"]
        operations = ChromaDBOperations(client)

        results = operations.list_documents(collection_name, include_metadata=True)

        assert "total_documents" in results
        assert "documents" in results
        assert results["total_documents"] == 3  # We added 3 documents
        assert len(results["documents"]) == 3

        # Check first document structure
        doc = results["documents"][0]
        assert "id" in doc
        assert "content" in doc
        assert "metadata" in doc

    @pytest.mark.unit
    def test_list_documents_with_pagination(
        self, populated_collection: dict[str, Any]
    ) -> None:
        """Test list_documents with pagination."""
        client = populated_collection["client"]
        collection_name = populated_collection["collection_name"]
        operations = ChromaDBOperations(client)

        results = operations.list_documents(
            collection_name, limit=2, offset=0, include_metadata=True
        )

        assert results["total_documents"] == 3
        assert len(results["documents"]) == 2

    @pytest.mark.unit
    def test_delete_documents_success(
        self, populated_collection: dict[str, Any]
    ) -> None:
        """Test successful delete_documents with mock data."""
        client = populated_collection["client"]
        collection_name = populated_collection["collection_name"]
        operations = ChromaDBOperations(client)

        # First verify document exists
        result = operations.get_document(collection_name, "doc1")
        assert result is not None

        # Delete the document
        delete_results = operations.delete_documents(collection_name, ["doc1"])
        assert delete_results["deleted_count"] == 1

        # Verify document is gone
        result = operations.get_document(collection_name, "doc1")
        assert result is None

    @pytest.mark.unit
    def test_delete_documents_nonexistent(
        self, populated_collection: dict[str, Any]
    ) -> None:
        """Test delete_documents with non-existent document IDs."""
        client = populated_collection["client"]
        collection_name = populated_collection["collection_name"]
        operations = ChromaDBOperations(client)

        delete_results = operations.delete_documents(
            collection_name, ["nonexistent1", "nonexistent2"]
        )
        # Mock should still report attempted deletion
        assert delete_results["deleted_count"] == 2

    @pytest.mark.unit
    def test_process_query_results(self, operations: ChromaDBOperations) -> None:
        """Test _process_query_results filtering and formatting."""
        raw_results = {
            "ids": [["id1", "id2", "id3"]],
            "documents": [["doc1", "doc2", "doc3"]],
            "distances": [[0.1, 0.5, 0.9]],
            "metadatas": [[{"s": "a"}, {"s": "b"}, {"s": "c"}]],
        }

        # similarity = 1 - distance. threshold = 0.6
        # id1: 1 - 0.1 = 0.9 (>= 0.6, keep)
        # id2: 1 - 0.5 = 0.5 (< 0.6, drop)
        # id3: 1 - 0.9 = 0.1 (< 0.6, drop)
        processed = operations._process_query_results(raw_results, 0.6, True)

        assert len(processed["results"]) == 1
        assert processed["results"][0]["id"] == "id1"
        assert processed["results"][0]["similarity_score"] == 0.9

    @pytest.mark.unit
    def test_operations_with_real_mock_workflow(
        self, mock_chromadb_client: MockChromaDBClient
    ) -> None:
        """Test complete workflow using mock client to increase coverage."""
        operations = ChromaDBOperations(mock_chromadb_client)

        # Create collection
        collection = mock_chromadb_client.create_collection(
            "workflow_test", metadata={"description": "Test workflow"}
        )

        # Add documents via bulk insert
        chunks = [
            DocumentChunk(
                id="workflow_doc1",
                content="First workflow document with some content",
                metadata={"type": "workflow", "step": 1},
            ),
            DocumentChunk(
                id="workflow_doc2",
                content="Second workflow document with different content",
                metadata={"type": "workflow", "step": 2},
            ),
        ]

        insert_result = mock_chromadb_client.bulk_insert(collection, chunks)
        assert insert_result.success
        assert insert_result.chunks_inserted == 2

        # Query the documents
        query_results = operations.query_collection(
            "workflow_test", "workflow document", limit=5, similarity_threshold=0.0
        )

        assert query_results["total_results"] >= 0

        # List all documents
        list_results = operations.list_documents("workflow_test")
        assert list_results["total_documents"] == 2

        # Get specific document
        doc_result = operations.get_document("workflow_test", "workflow_doc1")
        assert doc_result is not None
        assert doc_result["id"] == "workflow_doc1"

        # Delete one document
        delete_result = operations.delete_documents("workflow_test", ["workflow_doc1"])
        assert delete_result["deleted_count"] == 1

        # Verify deletion
        doc_result = operations.get_document("workflow_test", "workflow_doc1")
        assert doc_result is None

        # List should now show only 1 document
        list_results = operations.list_documents("workflow_test")
        assert list_results["total_documents"] == 1
