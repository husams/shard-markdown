"""Tests for ChromaDB client functionality."""

from unittest.mock import Mock, patch

import pytest

from shard_markdown.chromadb.client import ChromaDBClient
from shard_markdown.config import Settings
from shard_markdown.core.models import DocumentChunk
from shard_markdown.utils.errors import ChromaDBError, NetworkError


@pytest.fixture
def mock_config() -> Settings:
    """Create a mock ChromaDB configuration."""
    return Settings(
        chroma_host="localhost",
        chroma_port=8000,
        chroma_ssl=False,
        chroma_timeout=5.0,
        chroma_auth_token=None,
    )


@pytest.fixture
def client(mock_config: Settings) -> ChromaDBClient:
    """Create a ChromaDB client instance."""
    return ChromaDBClient(mock_config)


class TestChromaDBClientInit:
    """Test ChromaDB client initialization."""

    def test_init_with_config(self, mock_config: Settings) -> None:
        """Test client initialization with configuration."""
        client = ChromaDBClient(mock_config)

        assert client.config == mock_config
        assert client.client is None
        assert client._connection_validated is False


class TestChromaDBClientConnection:
    """Test ChromaDB client connection methods."""

    @patch("builtins.__import__")
    @patch("shard_markdown.chromadb.client.ChromaDBVersionDetector")
    @patch("shard_markdown.chromadb.client.check_socket_connectivity")
    def test_connect_success(
        self,
        mock_check_connectivity: Mock,
        mock_version_detector_class: Mock,
        mock_import: Mock,
        client: ChromaDBClient,
    ) -> None:
        """Test successful connection."""
        # Mock socket connectivity
        mock_check_connectivity.return_value = True

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
        mock_check_connectivity.assert_called_once_with(
            client.config.chroma_host,
            client.config.chroma_port,
            client.config.chroma_timeout,
        )

    @patch("shard_markdown.chromadb.client.check_socket_connectivity")
    def test_connect_network_error(
        self, mock_check_connectivity: Mock, client: ChromaDBClient
    ) -> None:
        """Test connection failure due to network error."""
        mock_check_connectivity.return_value = False

        with pytest.raises(NetworkError) as exc_info:
            client.connect()

        assert "Cannot connect to ChromaDB server" in str(exc_info.value)
        assert exc_info.value.error_code == 1601
        mock_check_connectivity.assert_called_once_with(
            client.config.chroma_host,
            client.config.chroma_port,
            client.config.chroma_timeout,
        )

    @patch("shard_markdown.chromadb.client.check_socket_connectivity")
    def test_connect_dns_error(
        self, mock_check_connectivity: Mock, client: ChromaDBClient
    ) -> None:
        """Test connection failure due to DNS error."""
        # Mock socket connectivity check to simulate DNS error
        mock_check_connectivity.return_value = False

        with pytest.raises(NetworkError):
            client.connect()

        mock_check_connectivity.assert_called_once_with(
            client.config.chroma_host,
            client.config.chroma_port,
            client.config.chroma_timeout,
        )

    def test_get_api_version_info_not_connected(self, client: ChromaDBClient) -> None:
        """Test get_api_version_info when not connected."""
        result = client.get_api_version_info()
        assert result is None

    def test_get_collection_not_connected(self, client: ChromaDBClient) -> None:
        """Test get_collection when not connected."""
        with pytest.raises(ChromaDBError) as exc_info:
            client.get_collection("test_collection")

        assert exc_info.value.error_code == 1400
        assert "ChromaDB connection not established" in str(exc_info.value)

    def test_get_collection_success(self, client: ChromaDBClient) -> None:
        """Test successful get_collection."""
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

        assert result.success is True
        assert result.chunks_inserted == 0
        assert result.collection_name == "test_collection"

    def test_bulk_insert_success(self, client: ChromaDBClient) -> None:
        """Test successful bulk_insert."""
        # Create test chunks
        chunks = [
            DocumentChunk(
                id="chunk_1",
                content="Test content 1",
                metadata={"source": "test1.md"},
                start_index=0,
                end_index=100,
            ),
            DocumentChunk(
                id="chunk_2",
                content="Test content 2",
                metadata={"source": "test2.md"},
                start_index=100,
                end_index=200,
            ),
        ]

        # Mock collection
        mock_collection = Mock()
        mock_collection.name = "test_collection"

        # Mock metadata extractor
        mock_extractor = Mock()
        mock_extractor.sanitize_metadata_for_chromadb.side_effect = lambda x: x
        client._metadata_extractor = mock_extractor

        result = client.bulk_insert(mock_collection, chunks)

        assert result.success is True
        assert result.chunks_inserted == 2
        assert result.collection_name == "test_collection"
        mock_collection.add.assert_called_once()

    def test_list_collections_not_connected(self, client: ChromaDBClient) -> None:
        """Test list_collections when not connected."""
        with pytest.raises(ChromaDBError) as exc_info:
            client.list_collections()

        assert exc_info.value.error_code == 1400
        assert "ChromaDB connection not established" in str(exc_info.value)

    def test_list_collections_success(self, client: ChromaDBClient) -> None:
        """Test successful list_collections."""
        # Set up connected state
        mock_client = Mock()
        mock_collection1 = Mock()
        mock_collection1.name = "collection1"
        mock_collection1.metadata = {"description": "Test collection 1"}
        mock_collection1.count.return_value = 10

        mock_collection2 = Mock()
        mock_collection2.name = "collection2"
        mock_collection2.metadata = {"description": "Test collection 2"}
        mock_collection2.count.return_value = 20

        mock_client.list_collections.return_value = [mock_collection1, mock_collection2]
        client.client = mock_client
        client._connection_validated = True

        result = client.list_collections()

        assert len(result) == 2
        assert result[0]["name"] == "collection1"
        assert result[0]["count"] == 10
        assert result[1]["name"] == "collection2"
        assert result[1]["count"] == 20

    def test_delete_collection_not_connected(self, client: ChromaDBClient) -> None:
        """Test delete_collection when not connected."""
        with pytest.raises(ChromaDBError) as exc_info:
            client.delete_collection("test_collection")

        assert exc_info.value.error_code == 1400
        assert "ChromaDB connection not established" in str(exc_info.value)

    def test_delete_collection_success(self, client: ChromaDBClient) -> None:
        """Test successful delete_collection."""
        # Set up connected state
        mock_client = Mock()
        client.client = mock_client
        client._connection_validated = True

        result = client.delete_collection("test_collection")

        assert result is True
        mock_client.delete_collection.assert_called_once_with("test_collection")

    def test_test_connection_success(self, client: ChromaDBClient) -> None:
        """Test successful test_connection."""
        # Mock version detector
        mock_detector = Mock()
        mock_detector.test_connection.return_value = True
        client.version_detector = mock_detector

        result = client.test_connection()

        assert result is True
        mock_detector.test_connection.assert_called_once_with(client._version_info)

    def test_test_connection_failure(self, client: ChromaDBClient) -> None:
        """Test test_connection failure."""
        # Mock version detector to raise exception
        mock_detector = Mock()
        mock_detector.test_connection.side_effect = Exception("Connection failed")
        client.version_detector = mock_detector

        result = client.test_connection()

        assert result is False

    def test_validate_insertion_data_mismatched_lengths(
        self, client: ChromaDBClient
    ) -> None:
        """Test _validate_insertion_data with mismatched lengths."""
        ids = ["id1", "id2"]
        documents = ["doc1"]  # Different length
        metadatas = [{"key": "value1"}, {"key": "value2"}]

        with pytest.raises(ChromaDBError) as exc_info:
            client._validate_insertion_data(ids, documents, metadatas)

        assert exc_info.value.error_code == 1430
        assert "Mismatched lengths" in str(exc_info.value)

    def test_validate_insertion_data_duplicate_ids(
        self, client: ChromaDBClient
    ) -> None:
        """Test _validate_insertion_data with duplicate IDs."""
        ids = ["id1", "id1"]  # Duplicate IDs
        documents = ["doc1", "doc2"]
        metadatas = [{"key": "value1"}, {"key": "value2"}]

        with pytest.raises(ChromaDBError) as exc_info:
            client._validate_insertion_data(ids, documents, metadatas)

        assert exc_info.value.error_code == 1431
        assert "Duplicate IDs found" in str(exc_info.value)

    def test_validate_insertion_data_empty_documents(
        self, client: ChromaDBClient
    ) -> None:
        """Test _validate_insertion_data with empty documents."""
        ids = ["id1", "id2"]
        documents = ["doc1", "   "]  # Empty document (whitespace only)
        metadatas = [{"key": "value1"}, {"key": "value2"}]

        with pytest.raises(ChromaDBError) as exc_info:
            client._validate_insertion_data(ids, documents, metadatas)

        assert exc_info.value.error_code == 1432
        assert "Empty documents found" in str(exc_info.value)

    def test_validate_insertion_data_success(self, client: ChromaDBClient) -> None:
        """Test _validate_insertion_data with valid data."""
        ids = ["id1", "id2"]
        documents = ["doc1", "doc2"]
        metadatas = [{"key": "value1"}, {"key": "value2"}]

        # Should not raise any exception
        client._validate_insertion_data(ids, documents, metadatas)
