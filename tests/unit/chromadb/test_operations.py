"""Unit tests for ChromaDBOperations class."""

import pytest
from unittest.mock import Mock, patch

from shard_markdown.chromadb.operations import ChromaDBOperations
from shard_markdown.chromadb.client import ChromaDBClient
from shard_markdown.utils.errors import ChromaDBError


@pytest.fixture
def mock_chromadb_client() -> Mock:
    """Fixture for a mocked ChromaDBClient."""
    client = Mock(spec=ChromaDBClient)
    client.client = Mock()
    client._connection_validated = True
    return client


@pytest.fixture
def operations(mock_chromadb_client: Mock) -> ChromaDBOperations:
    """Fixture for ChromaDBOperations."""
    return ChromaDBOperations(mock_chromadb_client)


class TestChromaDBOperations:
    """Test suite for ChromaDBOperations."""

    def test_initialization(self, operations: ChromaDBOperations, mock_chromadb_client: Mock):
        """Test that ChromaDBOperations initializes correctly."""
        assert operations.client == mock_chromadb_client

    def test_query_collection_not_connected(self, operations: ChromaDBOperations):
        """Test query_collection when client is not connected."""
        operations.client._connection_validated = False
        with pytest.raises(ChromaDBError, match="ChromaDB connection not established"):
            operations.query_collection("test_collection", "test query")

    def test_query_collection_success(self, operations: ChromaDBOperations, mock_chromadb_client: Mock):
        """Test successful query_collection."""
        mock_collection = Mock()
        mock_chromadb_client.client.get_collection.return_value = mock_collection
        mock_results = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "distances": [[0.1]],
            "metadatas": [[{"source": "test.md"}]]
        }
        mock_collection.query.return_value = mock_results

        results = operations.query_collection("test_collection", "test query")

        assert results["total_results"] == 1
        assert results["results"][0]["id"] == "id1"
        mock_chromadb_client.client.get_collection.assert_called_once_with("test_collection")
        mock_collection.query.assert_called_once()

    def test_query_collection_failure(self, operations: ChromaDBOperations, mock_chromadb_client: Mock):
        """Test query_collection failure."""
        mock_chromadb_client.client.get_collection.side_effect = ValueError("Test error")
        with pytest.raises(ChromaDBError, match="Failed to query collection"):
            operations.query_collection("test_collection", "test query")

    def test_get_document_not_connected(self, operations: ChromaDBOperations):
        """Test get_document when client is not connected."""
        operations.client._connection_validated = False
        with pytest.raises(ChromaDBError, match="ChromaDB connection not established"):
            operations.get_document("test_collection", "doc_id")

    def test_get_document_success(self, operations: ChromaDBOperations, mock_chromadb_client: Mock):
        """Test successful get_document."""
        mock_collection = Mock()
        mock_chromadb_client.client.get_collection.return_value = mock_collection
        mock_results = {
            "ids": ["doc1"],
            "documents": ["doc content"],
            "metadatas": [{"source": "test.md"}]
        }
        mock_collection.get.return_value = mock_results

        result = operations.get_document("test_collection", "doc1")

        assert result is not None
        assert result["id"] == "doc1"
        assert result["content"] == "doc content"
        mock_collection.get.assert_called_once_with(ids=["doc1"], include=['documents', 'metadatas'])

    def test_get_document_not_found(self, operations: ChromaDBOperations, mock_chromadb_client: Mock):
        """Test get_document when document is not found."""
        mock_collection = Mock()
        mock_chromadb_client.client.get_collection.return_value = mock_collection
        mock_collection.get.return_value = {"ids": []}

        result = operations.get_document("test_collection", "doc1")

        assert result is None

    def test_list_documents_success(self, operations: ChromaDBOperations, mock_chromadb_client: Mock):
        """Test successful list_documents."""
        mock_collection = Mock()
        mock_chromadb_client.client.get_collection.return_value = mock_collection
        mock_collection.count.return_value = 1
        mock_results = {
            "ids": ["doc1"],
            "documents": ["doc content"],
            "metadatas": [{"source": "test.md"}]
        }
        mock_collection.get.return_value = mock_results

        results = operations.list_documents("test_collection", include_metadata=True)

        assert results["total_documents"] == 1
        assert len(results["documents"]) == 1
        assert results["documents"][0]["id"] == "doc1"
        mock_collection.get.assert_called_once_with(limit=100, offset=0, include=['documents', 'metadatas'])

    def test_delete_documents_success(self, operations: ChromaDBOperations, mock_chromadb_client: Mock):
        """Test successful delete_documents."""
        mock_collection = Mock()
        mock_chromadb_client.client.get_collection.return_value = mock_collection

        results = operations.delete_documents("test_collection", ["doc1"])

        assert results["deleted_count"] == 1
        mock_collection.delete.assert_called_once_with(ids=["doc1"])

    def test_process_query_results(self, operations: ChromaDBOperations):
        """Test _process_query_results filtering and formatting."""
        raw_results = {
            "ids": [["id1", "id2", "id3"]],
            "documents": [["doc1", "doc2", "doc3"]],
            "distances": [[0.1, 0.5, 0.9]],
            "metadatas": [[{"s": "a"}, {"s": "b"}, {"s": "c"}]]
        }

        # similarity = 1 - distance. threshold = 0.6
        # id1: 1 - 0.1 = 0.9 (>= 0.6, keep)
        # id2: 1 - 0.5 = 0.5 (< 0.6, drop)
        # id3: 1 - 0.9 = 0.1 (< 0.6, drop)
        processed = operations._process_query_results(raw_results, 0.6, True)

        assert len(processed["results"]) == 1
        assert processed["results"][0]["id"] == "id1"
        assert processed["results"][0]["similarity_score"] == 0.9
