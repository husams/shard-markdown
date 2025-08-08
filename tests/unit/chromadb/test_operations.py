"""Tests for ChromaDB operations module."""

from unittest.mock import Mock

import pytest

from shard_markdown.chromadb.operations import ChromaDBOperations
from shard_markdown.utils.errors import ChromaDBError


class TestChromaDBOperations:
    """Test cases for ChromaDBOperations class."""

    @pytest.fixture
    def mock_client(self):
        """Create mock ChromaDB client."""
        client = Mock()
        client._connection_validated = True
        client.client = Mock()
        return client

    @pytest.fixture
    def operations(self, mock_client):
        """Create ChromaDBOperations instance with mock client."""
        return ChromaDBOperations(mock_client)

    def test_init(self, mock_client):
        """Test operations initialization."""
        ops = ChromaDBOperations(mock_client)
        assert ops.client == mock_client

    def test_query_collection_success(self, operations, mock_client):
        """Test successful collection query."""
        # Setup mock collection
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["doc1", "doc2"]],
            "documents": [["text1", "text2"]],
            "metadatas": [[{"key": "value1"}, {"key": "value2"}]],
            "distances": [[0.1, 0.2]],
        }
        mock_client.client.get_collection.return_value = mock_collection

        # Perform query
        result = operations.query_collection(
            collection_name="test_collection",
            query_text="test query",
            limit=2,
            similarity_threshold=0.5,
            include_metadata=True,
        )

        # Verify results
        assert result["collection_name"] == "test_collection"
        assert result["query"] == "test query"
        assert result["total_results"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["id"] == "doc1"
        assert result["results"][0]["similarity_score"] == 0.9  # 1 - 0.1
        mock_client.client.get_collection.assert_called_once_with("test_collection")
        mock_collection.query.assert_called_once()

    def test_query_collection_no_connection(self, mock_client):
        """Test query fails when connection not established."""
        mock_client._connection_validated = False
        ops = ChromaDBOperations(mock_client)

        with pytest.raises(ChromaDBError, match="ChromaDB connection not established"):
            ops.query_collection("test_collection", "test query")

    def test_query_collection_no_client(self, mock_client):
        """Test query fails when client is None."""
        mock_client.client = None
        ops = ChromaDBOperations(mock_client)

        with pytest.raises(ChromaDBError, match="ChromaDB connection not established"):
            ops.query_collection("test_collection", "test query")

    def test_query_collection_empty_results(self, operations, mock_client):
        """Test query with no results."""
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        mock_client.client.get_collection.return_value = mock_collection

        result = operations.query_collection(
            collection_name="test_collection",
            query_text="test query",
            limit=10,
        )

        assert result["total_results"] == 0
        assert result["results"] == []

    def test_query_collection_with_threshold(self, operations, mock_client):
        """Test query with similarity threshold filtering."""
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["doc1", "doc2", "doc3"]],
            "documents": [["text1", "text2", "text3"]],
            "metadatas": [[{"key": "value1"}, {"key": "value2"}, {"key": "value3"}]],
            "distances": [[0.1, 0.3, 0.8]],  # scores: 0.9, 0.7, 0.2
        }
        mock_client.client.get_collection.return_value = mock_collection

        result = operations.query_collection(
            collection_name="test_collection",
            query_text="test query",
            limit=10,
            similarity_threshold=0.5,  # Should filter out doc3
        )

        assert result["total_results"] == 2  # Only doc1 and doc2
        assert len(result["results"]) == 2
        assert result["results"][0]["similarity_score"] == 0.9
        assert result["results"][1]["similarity_score"] == 0.7

    def test_query_collection_without_metadata(self, operations, mock_client):
        """Test query without including metadata."""
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["doc1"]],
            "documents": [["text1"]],
            "metadatas": [[{"key": "value1"}]],
            "distances": [[0.1]],
        }
        mock_client.client.get_collection.return_value = mock_collection

        result = operations.query_collection(
            collection_name="test_collection",
            query_text="test query",
            include_metadata=False,
        )

        assert result["total_results"] == 1
        assert "metadata" not in result["results"][0]

    def test_query_collection_exception(self, operations, mock_client):
        """Test query handles exceptions properly."""
        mock_client.client.get_collection.side_effect = RuntimeError(
            "Connection failed"
        )

        with pytest.raises(ChromaDBError, match="Failed to query collection"):
            operations.query_collection("test_collection", "test query")

    def test_get_document(self, operations, mock_client):
        """Test getting a single document."""
        mock_collection = Mock()
        mock_collection.get.return_value = {
            "ids": ["doc1"],
            "documents": ["document text"],
            "metadatas": [{"title": "Test Doc"}],
        }
        mock_client.client.get_collection.return_value = mock_collection

        result = operations.get_document(
            collection_name="test_collection",
            document_id="doc1",
        )

        assert result["id"] == "doc1"
        assert result["content"] == "document text"
        assert result["metadata"]["title"] == "Test Doc"

    def test_get_document_not_found(self, operations, mock_client):
        """Test getting non-existent document."""
        mock_collection = Mock()
        mock_collection.get.return_value = {
            "ids": [],
            "documents": [],
            "metadatas": [],
        }
        mock_client.client.get_collection.return_value = mock_collection

        result = operations.get_document(
            collection_name="test_collection",
            document_id="nonexistent",
        )

        assert result is None

    def test_get_document_no_connection(self, mock_client):
        """Test get document fails without connection."""
        mock_client._connection_validated = False
        ops = ChromaDBOperations(mock_client)

        with pytest.raises(ChromaDBError, match="ChromaDB connection not established"):
            ops.get_document("test_collection", "doc1")

    def test_list_documents(self, operations, mock_client):
        """Test listing documents in collection."""
        mock_collection = Mock()
        mock_collection.get.return_value = {
            "ids": ["doc1", "doc2", "doc3"],
            "documents": ["text1", "text2", "text3"],
            "metadatas": [{"a": "1"}, {"a": "2"}, {"a": "3"}],
        }
        mock_collection.count.return_value = 3
        mock_client.client.get_collection.return_value = mock_collection

        result = operations.list_documents(
            collection_name="test_collection",
            limit=10,
            offset=0,
            include_metadata=True,
        )

        assert result["collection_name"] == "test_collection"
        assert result["total_documents"] == 3
        assert len(result["documents"]) == 3
        assert result["documents"][0]["id"] == "doc1"

    def test_list_documents_empty_collection(self, operations, mock_client):
        """Test listing documents in empty collection."""
        mock_collection = Mock()
        mock_collection.get.return_value = {
            "ids": [],
            "documents": [],
            "metadatas": [],
        }
        mock_collection.count.return_value = 0
        mock_client.client.get_collection.return_value = mock_collection

        result = operations.list_documents("test_collection")

        assert result["total_documents"] == 0
        assert result["documents"] == []

    def test_delete_documents(self, operations, mock_client):
        """Test deleting documents."""
        mock_collection = Mock()
        mock_collection.delete.return_value = None
        mock_client.client.get_collection.return_value = mock_collection

        result = operations.delete_documents(
            collection_name="test_collection",
            document_ids=["doc1", "doc2"],
        )

        assert result["deleted_count"] == 2
        assert result["deleted_ids"] == ["doc1", "doc2"]
        mock_collection.delete.assert_called_once_with(ids=["doc1", "doc2"])

    def test_delete_documents_empty_list(self, operations, mock_client):
        """Test deleting with empty document list."""
        mock_collection = Mock()
        mock_client.client.get_collection.return_value = mock_collection

        result = operations.delete_documents(
            collection_name="test_collection",
            document_ids=[],
        )

        assert result["deleted_count"] == 0
        assert result["deleted_ids"] == []

    def test_delete_documents_exception(self, operations, mock_client):
        """Test delete documents handles exceptions."""
        mock_collection = Mock()
        mock_collection.delete.side_effect = RuntimeError("Delete failed")
        mock_client.client.get_collection.return_value = mock_collection

        with pytest.raises(ChromaDBError, match="Failed to delete documents"):
            operations.delete_documents(
                collection_name="test_collection",
                document_ids=["doc1"],
            )

    def test_delete_documents_no_connection(self, mock_client):
        """Test delete fails without connection."""
        mock_client._connection_validated = False
        ops = ChromaDBOperations(mock_client)

        with pytest.raises(ChromaDBError, match="ChromaDB connection not established"):
            ops.delete_documents("test_collection", ["doc1"])

    def test_process_query_results(self, operations):
        """Test internal query results processing."""
        raw_results = {
            "ids": [["id1", "id2"]],
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"key": "val1"}, {"key": "val2"}]],
            "distances": [[0.1, 0.3]],
        }

        processed = operations._process_query_results(
            raw_results,
            similarity_threshold=0.5,
            include_metadata=True,
        )

        assert len(processed["results"]) == 2
        assert processed["results"][0]["id"] == "id1"
        assert processed["results"][0]["similarity_score"] == 0.9
        assert processed["results"][0]["content"] == "doc1"
        assert processed["results"][0]["metadata"]["key"] == "val1"

    def test_process_query_results_with_threshold(self, operations):
        """Test processing results with similarity threshold."""
        raw_results = {
            "ids": [["id1", "id2", "id3"]],
            "documents": [["doc1", "doc2", "doc3"]],
            "metadatas": [[{"k": "v1"}, {"k": "v2"}, {"k": "v3"}]],
            "distances": [[0.1, 0.4, 0.8]],  # scores: 0.9, 0.6, 0.2
        }

        processed = operations._process_query_results(
            raw_results,
            similarity_threshold=0.7,  # Filter out id2 and id3
            include_metadata=True,
        )

        assert len(processed["results"]) == 1
        assert processed["results"][0]["id"] == "id1"
        assert processed["results"][0]["similarity_score"] == 0.9

    def test_process_query_results_without_metadata(self, operations):
        """Test processing results without metadata."""
        raw_results = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "metadatas": [[{"key": "val"}]],
            "distances": [[0.2]],
        }

        processed = operations._process_query_results(
            raw_results,
            similarity_threshold=0.0,
            include_metadata=False,
        )

        assert len(processed["results"]) == 1
        assert "metadata" not in processed["results"][0]
        assert processed["results"][0]["id"] == "id1"
        assert processed["results"][0]["content"] == "doc1"

    def test_list_documents_no_connection(self, mock_client):
        """Test list documents fails without connection."""
        mock_client._connection_validated = False
        ops = ChromaDBOperations(mock_client)

        with pytest.raises(ChromaDBError, match="ChromaDB connection not established"):
            ops.list_documents("test_collection")
