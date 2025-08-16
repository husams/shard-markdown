"""Unit tests for ChromaDB client wrapper."""

import socket
from unittest.mock import Mock, patch

import pytest

from shard_markdown.chromadb.client import ChromaDBClient
from shard_markdown.config.settings import ChromaDBConfig
from shard_markdown.core.models import DocumentChunk, InsertResult
from shard_markdown.utils.errors import ChromaDBError, NetworkError


@pytest.fixture
def mock_config() -> ChromaDBConfig:
    """Create mock ChromaDB configuration."""
    return ChromaDBConfig(
        host="localhost",
        port=8000,
        ssl=False,
        timeout=5.0,
        auth_token=None,
    )


@pytest.fixture
def client(mock_config: ChromaDBConfig) -> ChromaDBClient:
    """Create ChromaDB client instance."""
    return ChromaDBClient(mock_config)


@pytest.fixture
def sample_chunks() -> list[DocumentChunk]:
    """Create sample document chunks for testing."""
    return [
        DocumentChunk(
            id="chunk_1",
            content="Sample content 1",
            metadata={"source": "test1.md", "chunk_index": 0},
        ),
        DocumentChunk(
            id="chunk_2",
            content="Sample content 2",
            metadata={"source": "test2.md", "chunk_index": 1},
        ),
    ]


class TestChromaDBClient:
    """Test cases for ChromaDBClient class."""

    def test_init(self, mock_config: ChromaDBConfig) -> None:
        """Test client initialization."""
        client = ChromaDBClient(mock_config)
        assert client.config == mock_config
        assert client.client is None
        assert client._connection_validated is False

    @patch("builtins.__import__")
    @patch("shard_markdown.chromadb.client.ChromaDBVersionDetector")
    @patch("shard_markdown.chromadb.client.socket.socket")
    def test_connect_success(
        self,
        mock_socket: Mock,
        mock_version_detector_class: Mock,
        mock_import: Mock,
        client: ChromaDBClient,
    ) -> None:
        """Test successful connection."""
        # Mock socket connection
        mock_sock_instance = Mock()
        mock_socket.return_value = mock_sock_instance
        mock_sock_instance.connect_ex.return_value = 0

        # Mock version detector instance and its detect_api_version method
        from shard_markdown.chromadb.version_detector import APIVersionInfo

        mock_version_info = APIVersionInfo(
            version="v2",
            heartbeat_endpoint="http://localhost:8000/api/v2/heartbeat",
            version_endpoint="http://localhost:8000/api/v2/version",
            detection_time=1234567890.0,
        )

        # Create a mock instance for the version detector
        mock_version_detector_instance = Mock()
        mock_version_detector_instance.detect_api_version.return_value = (
            mock_version_info
        )
        mock_version_detector_class.return_value = mock_version_detector_instance

        # Re-initialize the client's version_detector with our mock
        client.version_detector = mock_version_detector_instance

        # Mock ChromaDB client
        mock_chromadb = Mock()
        mock_client_instance = Mock()
        mock_chromadb.HttpClient.return_value = mock_client_instance
        mock_import.return_value = mock_chromadb

        result = client.connect()

        assert result is True
        assert client._connection_validated is True
        assert client.client == mock_client_instance
        mock_client_instance.heartbeat.assert_called_once()

    @patch("shard_markdown.chromadb.client.socket.socket")
    def test_connect_network_error(
        self, mock_socket: Mock, client: ChromaDBClient
    ) -> None:
        """Test connection failure due to network error."""
        mock_sock_instance = Mock()
        mock_socket.return_value = mock_sock_instance
        mock_sock_instance.connect_ex.return_value = 1  # Connection failed

        with pytest.raises(NetworkError):
            client.connect()

    @patch("shard_markdown.chromadb.client.socket.socket")
    def test_connect_dns_error(self, mock_socket: Mock, client: ChromaDBClient) -> None:
        """Test connection failure due to DNS error."""
        mock_sock_instance = Mock()
        mock_socket.return_value = mock_sock_instance
        mock_sock_instance.connect_ex.side_effect = socket.gaierror("DNS error")

        with pytest.raises(NetworkError):
            client.connect()

    def test_get_collection_not_connected(self, client: ChromaDBClient) -> None:
        """Test get_collection when not connected."""
        expected_match = "ChromaDB connection not established"
        with pytest.raises(ChromaDBError, match=expected_match):
            client.get_collection("test_collection")

    def test_get_collection_success(self, client: ChromaDBClient) -> None:
        """Test successful collection retrieval."""
        # Set up connected state
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_collection.return_value = mock_collection
        client.client = mock_client
        client._connection_validated = True

        result = client.get_collection("test_collection")

        assert result == mock_collection
        mock_client.get_collection.assert_called_once_with("test_collection")

    def test_get_collection_not_exists(self, client: ChromaDBClient) -> None:
        """Test get_collection when collection doesn't exist."""
        # Set up connected state
        mock_client = Mock()
        mock_client.get_collection.side_effect = ValueError("Collection not found")
        client.client = mock_client
        client._connection_validated = True

        expected_match = "Collection 'test_collection' does not exist"
        with pytest.raises(ChromaDBError, match=expected_match):
            client.get_collection("test_collection")

    def test_get_or_create_collection_existing(self, client: ChromaDBClient) -> None:
        """Test get_or_create_collection with existing collection."""
        # Set up connected state
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_collection.return_value = mock_collection
        client.client = mock_client
        client._connection_validated = True

        result = client.get_or_create_collection("test_collection")

        assert result == mock_collection
        mock_client.get_collection.assert_called_once_with("test_collection")

    @patch("time.strftime")
    def test_get_or_create_collection_create_new(
        self, mock_strftime: Mock, client: ChromaDBClient
    ) -> None:
        """Test get_or_create_collection with new collection creation."""
        mock_strftime.return_value = "2024-01-01T00:00:00Z"

        # Set up connected state
        mock_client = Mock()
        mock_client.get_collection.side_effect = ValueError("Collection not found")
        mock_new_collection = Mock()
        mock_client.create_collection.return_value = mock_new_collection
        client.client = mock_client
        client._connection_validated = True

        result = client.get_or_create_collection(
            "test_collection", create_if_missing=True
        )

        assert result == mock_new_collection
        mock_client.create_collection.assert_called_once()

    def test_bulk_insert_empty_chunks(self, client: ChromaDBClient) -> None:
        """Test bulk_insert with empty chunk list."""
        mock_collection = Mock()
        mock_collection.name = "test_collection"

        result = client.bulk_insert(mock_collection, [])

        assert isinstance(result, InsertResult)
        assert result.success is True
        assert result.chunks_inserted == 0
        assert result.collection_name == "test_collection"

    def test_bulk_insert_success(
        self, client: ChromaDBClient, sample_chunks: list[DocumentChunk]
    ) -> None:
        """Test successful bulk insert."""
        mock_collection = Mock()
        mock_collection.name = "test_collection"

        result = client.bulk_insert(mock_collection, sample_chunks)

        assert isinstance(result, InsertResult)
        assert result.success is True
        assert result.chunks_inserted == 2
        assert result.collection_name == "test_collection"
        mock_collection.add.assert_called_once()

    def test_bulk_insert_failure(
        self, client: ChromaDBClient, sample_chunks: list[DocumentChunk]
    ) -> None:
        """Test bulk insert failure."""
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        mock_collection.add.side_effect = ValueError("Insert failed")

        result = client.bulk_insert(mock_collection, sample_chunks)

        assert isinstance(result, InsertResult)
        assert result.success is False
        assert result.error == "Insert failed"
        assert result.collection_name == "test_collection"

    def test_bulk_insert_batch_processing(self, client: ChromaDBClient) -> None:
        """Test bulk insert with batch processing using simple chunks."""
        # Create simple test chunks (more than batch size of 100)
        chunks = []
        for i in range(150):  # 150 chunks to trigger batch processing
            chunks.append(
                DocumentChunk(
                    id=f"chunk_{i}",
                    content=f"Content for chunk {i}",
                    metadata={"index": i, "type": "test"},
                    start_position=i * 10,
                    end_position=(i + 1) * 10,
                )
            )

        mock_collection = Mock()
        mock_collection.name = "batch_test_collection"

        result = client.bulk_insert(mock_collection, chunks)

        assert isinstance(result, InsertResult)
        assert result.success is True
        assert result.chunks_inserted == 150
        assert result.collection_name == "batch_test_collection"

        # Should call add twice (batch_size = 100, so 100 + 50)
        assert mock_collection.add.call_count == 2

    def test_bulk_insert_metadata_sanitization(self, client: ChromaDBClient) -> None:
        """Test bulk insert with metadata sanitization."""
        # Create chunks with various metadata types
        chunks = [
            DocumentChunk(
                id="chunk_1",
                content="Content 1",
                metadata={"string_val": "test", "int_val": 42, "float_val": 3.14},
                start_position=0,
                end_position=10,
            ),
            DocumentChunk(
                id="chunk_2",
                content="Content 2",
                metadata={"bool_val": True, "none_val": None, "list_val": ["a", "b"]},
                start_position=10,
                end_position=20,
            ),
        ]

        mock_collection = Mock()
        mock_collection.name = "metadata_test"

        result = client.bulk_insert(mock_collection, chunks)

        assert isinstance(result, InsertResult)
        assert result.success is True
        assert result.chunks_inserted == 2

        # Verify metadata was processed through sanitization
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        assert "metadatas" in call_args[1]

    def test_bulk_insert_api_version_injection(self, client: ChromaDBClient) -> None:
        """Test API version information is added to metadata."""
        # Create a simple chunk
        chunk = DocumentChunk(
            id="version_test_chunk",
            content="Test content",
            metadata={"original": "data"},
            start_position=0,
            end_position=10,
        )

        mock_collection = Mock()
        mock_collection.name = "version_test"

        # Mock version info on client
        mock_version_info = Mock()
        mock_version_info.version = "0.5.0"
        mock_version_info.chromadb_version = "0.4.24"
        client._version_info = mock_version_info

        result = client.bulk_insert(mock_collection, [chunk])

        assert isinstance(result, InsertResult)
        assert result.success is True
        assert result.chunks_inserted == 1

        # Verify API version was added to metadata
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        metadatas = call_args[1]["metadatas"]
        assert len(metadatas) == 1
        assert "api_version" in metadatas[0]
        assert "chromadb_version" in metadatas[0]

    def test_bulk_insert_id_generation(self, client: ChromaDBClient) -> None:
        """Test automatic ID generation for chunks without IDs."""
        # Create chunks without IDs
        chunks = [
            DocumentChunk(
                content="Content without ID 1",
                metadata={"type": "test"},
                start_position=0,
                end_position=10,
            ),
            DocumentChunk(
                content="Content without ID 2",
                metadata={"type": "test"},
                start_position=10,
                end_position=20,
            ),
        ]

        mock_collection = Mock()
        mock_collection.name = "id_gen_test"

        result = client.bulk_insert(mock_collection, chunks)

        assert isinstance(result, InsertResult)
        assert result.success is True
        assert result.chunks_inserted == 2

        # Verify IDs were generated
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        ids = call_args[1]["ids"]
        assert len(ids) == 2
        assert all(id.startswith("chunk_") for id in ids)

    def test_bulk_insert_validation_error(self, client: ChromaDBClient) -> None:
        """Test bulk insert with data validation errors."""
        # Create chunk that will cause validation error
        chunk = DocumentChunk(
            id="",  # Empty ID should cause validation error
            content="Test content",
            metadata={"test": "data"},
            start_position=0,
            end_position=10,
        )

        mock_collection = Mock()
        mock_collection.name = "validation_test"

        # Mock validation to raise error
        with patch.object(client, "_validate_insertion_data") as mock_validate:
            mock_validate.side_effect = ValueError("Invalid ID")

            result = client.bulk_insert(mock_collection, [chunk])

        assert isinstance(result, InsertResult)
        assert result.success is False
        assert result.error == "Invalid ID"
        assert result.collection_name == "validation_test"

    def test_bulk_insert_collection_error(self, client: ChromaDBClient) -> None:
        """Test bulk insert with collection operation errors."""
        chunk = DocumentChunk(
            id="error_test_chunk",
            content="Test content",
            metadata={"test": "data"},
            start_position=0,
            end_position=10,
        )

        mock_collection = Mock()
        mock_collection.name = "error_test"
        mock_collection.add.side_effect = RuntimeError("Collection error")

        result = client.bulk_insert(mock_collection, [chunk])

        assert isinstance(result, InsertResult)
        assert result.success is False
        assert result.error == "Collection error"
        assert result.collection_name == "error_test"

    def test_bulk_insert_mixed_chunk_sizes(self, client: ChromaDBClient) -> None:
        """Test bulk insert with chunks of varying content sizes."""
        chunks = [
            DocumentChunk(
                id="small_chunk",
                content="Small",
                metadata={"size": "small"},
                start_position=0,
                end_position=5,
            ),
            DocumentChunk(
                id="medium_chunk",
                content="Medium content with more text to test different sizes",
                metadata={"size": "medium"},
                start_position=5,
                end_position=55,
            ),
            DocumentChunk(
                id="large_chunk",
                content="Large content " * 50,  # Repeat to make larger
                metadata={"size": "large"},
                start_position=55,
                end_position=755,
            ),
        ]

        mock_collection = Mock()
        mock_collection.name = "mixed_size_test"

        result = client.bulk_insert(mock_collection, chunks)

        assert isinstance(result, InsertResult)
        assert result.success is True
        assert result.chunks_inserted == 3
        assert result.processing_time > 0

    def test_list_collections_not_connected(self, client: ChromaDBClient) -> None:
        """Test list_collections when not connected."""
        expected_match = "ChromaDB connection not established"
        with pytest.raises(ChromaDBError, match=expected_match):
            client.list_collections()

    def test_list_collections_success(self, client: ChromaDBClient) -> None:
        """Test successful collection listing."""
        # Set up connected state
        mock_client = Mock()
        mock_collection1 = Mock()
        mock_collection1.name = "collection1"
        mock_collection1.metadata = {"type": "test"}
        mock_collection1.count.return_value = 10

        mock_collection2 = Mock()
        mock_collection2.name = "collection2"
        mock_collection2.metadata = {"type": "production"}
        mock_collection2.count.return_value = 25

        mock_client.list_collections.return_value = [
            mock_collection1,
            mock_collection2,
        ]
        client.client = mock_client
        client._connection_validated = True

        result = client.list_collections()

        assert len(result) == 2
        assert result[0]["name"] == "collection1"
        assert result[0]["count"] == 10
        assert result[1]["name"] == "collection2"
        assert result[1]["count"] == 25

    def test_list_collections_with_error(self, client: ChromaDBClient) -> None:
        """Test list_collections with partial errors."""
        # Set up connected state
        mock_client = Mock()
        mock_collection1 = Mock()
        mock_collection1.name = "collection1"
        mock_collection1.metadata = {"type": "test"}
        mock_collection1.count.return_value = 10

        mock_collection2 = Mock()
        mock_collection2.name = "collection2"
        mock_collection2.count.side_effect = RuntimeError("Count failed")

        mock_client.list_collections.return_value = [
            mock_collection1,
            mock_collection2,
        ]
        client.client = mock_client
        client._connection_validated = True

        result = client.list_collections()

        assert len(result) == 2
        assert result[0]["name"] == "collection1"
        assert result[0]["count"] == 10
        assert result[1]["name"] == "collection2"
        assert result[1]["count"] == -1
        assert "error" in result[1]

    def test_delete_collection_not_connected(self, client: ChromaDBClient) -> None:
        """Test delete_collection when not connected."""
        expected_match = "ChromaDB connection not established"
        with pytest.raises(ChromaDBError, match=expected_match):
            client.delete_collection("test_collection")

    def test_delete_collection_success(self, client: ChromaDBClient) -> None:
        """Test successful collection deletion."""
        # Set up connected state
        mock_client = Mock()
        client.client = mock_client
        client._connection_validated = True

        result = client.delete_collection("test_collection")

        assert result is True
        mock_client.delete_collection.assert_called_once_with("test_collection")

    def test_delete_collection_failure(self, client: ChromaDBClient) -> None:
        """Test collection deletion failure."""
        # Set up connected state
        mock_client = Mock()
        mock_client.delete_collection.side_effect = ValueError("Delete failed")
        client.client = mock_client
        client._connection_validated = True

        with pytest.raises(ChromaDBError, match="Failed to delete collection"):
            client.delete_collection("test_collection")

    def test_get_auth_headers_no_token(self, client: ChromaDBClient) -> None:
        """Test auth headers without token."""
        headers = client._get_auth_headers()
        assert headers == {}

    def test_get_auth_headers_with_token(self, mock_config: ChromaDBConfig) -> None:
        """Test auth headers with token."""
        mock_config.auth_token = "test_token"  # noqa: S105
        client = ChromaDBClient(mock_config)
        headers = client._get_auth_headers()
        assert headers == {"Authorization": "Bearer test_token"}

    def test_validate_insertion_data_success(self, client: ChromaDBClient) -> None:
        """Test successful insertion data validation."""
        ids = ["id1", "id2"]
        documents = ["doc1", "doc2"]
        metadatas = [{"key": "value1"}, {"key": "value2"}]

        # Should not raise any exception
        client._validate_insertion_data(ids, documents, metadatas)

    def test_validate_insertion_data_mismatched_lengths(
        self, client: ChromaDBClient
    ) -> None:
        """Test validation with mismatched data lengths."""
        ids = ["id1", "id2"]
        documents = ["doc1"]  # Different length
        metadatas = [{"key": "value1"}, {"key": "value2"}]

        expected_match = "Mismatched lengths in insertion data"
        with pytest.raises(ChromaDBError, match=expected_match):
            client._validate_insertion_data(ids, documents, metadatas)

    def test_validate_insertion_data_duplicate_ids(
        self, client: ChromaDBClient
    ) -> None:
        """Test validation with duplicate IDs."""
        ids = ["id1", "id1"]  # Duplicate ID
        documents = ["doc1", "doc2"]
        metadatas = [{"key": "value1"}, {"key": "value2"}]

        expected_match = "Duplicate IDs found in insertion data"
        with pytest.raises(ChromaDBError, match=expected_match):
            client._validate_insertion_data(ids, documents, metadatas)

    def test_validate_insertion_data_empty_documents(
        self, client: ChromaDBClient
    ) -> None:
        """Test validation with empty documents."""
        ids = ["id1", "id2"]
        documents = ["doc1", ""]  # Empty document
        metadatas = [{"key": "value1"}, {"key": "value2"}]

        expected_match = "Empty documents found at indices"
        with pytest.raises(ChromaDBError, match=expected_match):
            client._validate_insertion_data(ids, documents, metadatas)
