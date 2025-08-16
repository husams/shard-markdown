"""Unit tests for AsyncChromaDBClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shard_markdown.config.settings import ChromaDBConfig
from shard_markdown.core.models import DocumentChunk, InsertResult


class TestAsyncChromaDBClient:
    """Test AsyncChromaDBClient implementation."""

    @pytest.fixture
    def config(self) -> ChromaDBConfig:
        """Create test ChromaDB configuration."""
        import os

        # Use environment variables from CI or default to 8000 for consistency
        host = os.getenv("CHROMA_HOST", "localhost")
        port = int(os.getenv("CHROMA_PORT", "8000"))
        return ChromaDBConfig(
            host=host,
            port=port,
            auth_token=None,
        )

    @pytest.fixture
    def sample_chunks(self) -> list[DocumentChunk]:
        """Create sample document chunks for testing."""
        return [
            DocumentChunk(
                id="chunk_1",
                content="First test chunk content",
                metadata={"file": "test1.md", "section": "intro"},
            ),
            DocumentChunk(
                id="chunk_2",
                content="Second test chunk content",
                metadata={"file": "test2.md", "section": "body"},
            ),
        ]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_client_initialization(self, config):
        """Test AsyncChromaDBClient can be initialized."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        client = AsyncChromaDBClient(config)
        assert client.config == config
        assert client.client is None
        assert not client._connection_validated

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_context_manager(self, config):
        """Test AsyncChromaDBClient works as async context manager."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)

            # Since chromadb.AsyncHttpClient is async, we need to mock it properly
            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            async with AsyncChromaDBClient(config) as client:
                assert client.client == mock_client
                mock_client_class.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_method(self, config):
        """Test async connect method."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)

            # Since chromadb.AsyncHttpClient is async, we need to mock it properly
            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            assert client.client == mock_client
            assert client._connection_validated
            mock_client_class.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_collection(self, config):
        """Test async get_collection method."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)
            mock_collection = MagicMock()
            mock_client.get_collection = AsyncMock(return_value=mock_collection)

            # Since chromadb.AsyncHttpClient is async, we need to mock it properly
            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            collection = await client.get_collection("test_collection")

            assert collection == mock_collection
            mock_client.get_collection.assert_called_once_with("test_collection")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_or_create_collection(self, config):
        """Test async get_or_create_collection method."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)
            mock_collection = MagicMock()
            mock_client.get_or_create_collection = AsyncMock(
                return_value=mock_collection
            )

            # Since chromadb.AsyncHttpClient is async, we need to mock it properly
            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            collection = await client.get_or_create_collection("test_collection")

            assert collection == mock_collection
            mock_client.get_or_create_collection.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_insert(self, config, sample_chunks):
        """Test async bulk_insert method."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)
            mock_collection = AsyncMock()
            mock_collection.name = "test_collection"
            mock_collection.add = AsyncMock()

            # Since chromadb.AsyncHttpClient is async, we need to mock it properly
            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            result = await client.bulk_insert(mock_collection, sample_chunks)

            assert isinstance(result, InsertResult)
            assert result.success is True
            assert result.chunks_inserted == 2
            assert result.collection_name == "test_collection"
            mock_collection.add.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_insert_empty_chunks(self, config):
        """Test bulk_insert with empty chunks list."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)
            mock_collection = AsyncMock()
            mock_collection.name = "test_collection"

            # Since chromadb.AsyncHttpClient is async, we need to mock it properly
            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            result = await client.bulk_insert(mock_collection, [])

            assert isinstance(result, InsertResult)
            assert result.success is True
            assert result.chunks_inserted == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_insert_batch_processing(self, config):
        """Test async bulk insert with batch processing using simple chunks."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        # Create simple test chunks (more than batch size of 100)
        chunks = []
        for i in range(150):  # 150 chunks to trigger batch processing
            chunks.append(
                DocumentChunk(
                    id=f"async_chunk_{i}",
                    content=f"Async content for chunk {i}",
                    metadata={"index": i, "type": "async_test"},
                    start_position=i * 10,
                    end_position=(i + 1) * 10,
                )
            )

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)
            mock_collection = AsyncMock()
            mock_collection.name = "async_batch_test"
            mock_collection.add = AsyncMock()

            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            result = await client.bulk_insert(mock_collection, chunks)

            assert isinstance(result, InsertResult)
            assert result.success is True
            assert result.chunks_inserted == 150
            assert result.collection_name == "async_batch_test"

            # Should call add twice for batching (100 + 50)
            assert mock_collection.add.call_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_insert_metadata_sanitization(self, config):
        """Test async bulk insert with metadata sanitization."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        # Create chunks with various metadata types
        chunks = [
            DocumentChunk(
                id="async_chunk_1",
                content="Async content 1",
                metadata={"string_val": "test", "int_val": 42, "float_val": 3.14},
                start_position=0,
                end_position=10,
            ),
            DocumentChunk(
                id="async_chunk_2",
                content="Async content 2",
                metadata={"bool_val": True, "none_val": None, "list_val": ["a", "b"]},
                start_position=10,
                end_position=20,
            ),
        ]

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)
            mock_collection = AsyncMock()
            mock_collection.name = "async_metadata_test"
            mock_collection.add = AsyncMock()

            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            result = await client.bulk_insert(mock_collection, chunks)

            assert isinstance(result, InsertResult)
            assert result.success is True
            assert result.chunks_inserted == 2

            # Verify metadata was processed through sanitization
            mock_collection.add.assert_called_once()
            call_args = mock_collection.add.call_args
            assert "metadatas" in call_args[1]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_insert_api_version_injection(self, config):
        """Test API version information is added to metadata in async mode."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        # Create a simple chunk
        chunk = DocumentChunk(
            id="async_version_chunk",
            content="Async test content",
            metadata={"original": "async_data"},
            start_position=0,
            end_position=10,
        )

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)
            mock_collection = AsyncMock()
            mock_collection.name = "async_version_test"
            mock_collection.add = AsyncMock()

            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            # Mock version info on client
            from unittest.mock import Mock

            mock_version_info = Mock()
            mock_version_info.version = "0.5.0"
            mock_version_info.chromadb_version = "0.4.24"
            client._version_info = mock_version_info

            result = await client.bulk_insert(mock_collection, [chunk])

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

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_insert_id_generation(self, config):
        """Test automatic ID generation for chunks without IDs in async mode."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        # Create chunks without IDs
        chunks = [
            DocumentChunk(
                content="Async content without ID 1",
                metadata={"type": "async_test"},
                start_position=0,
                end_position=10,
            ),
            DocumentChunk(
                content="Async content without ID 2",
                metadata={"type": "async_test"},
                start_position=10,
                end_position=20,
            ),
        ]

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)
            mock_collection = AsyncMock()
            mock_collection.name = "async_id_gen_test"
            mock_collection.add = AsyncMock()

            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            result = await client.bulk_insert(mock_collection, chunks)

            assert isinstance(result, InsertResult)
            assert result.success is True
            assert result.chunks_inserted == 2

            # Verify IDs were generated (using hash-based generation for async)
            mock_collection.add.assert_called_once()
            call_args = mock_collection.add.call_args
            ids = call_args[1]["ids"]
            assert len(ids) == 2
            assert all(id.startswith("chunk_") for id in ids)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_insert_validation_error(self, config):
        """Test async bulk insert with data validation errors."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        # Create chunk that will cause validation error
        chunk = DocumentChunk(
            id="",  # Empty ID should cause validation error
            content="Async test content",
            metadata={"test": "async_data"},
            start_position=0,
            end_position=10,
        )

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)
            mock_collection = AsyncMock()
            mock_collection.name = "async_validation_test"

            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            # Mock validation to raise error
            with patch.object(client, "_validate_insertion_data") as mock_validate:
                mock_validate.side_effect = ValueError("Invalid async ID")

                result = await client.bulk_insert(mock_collection, [chunk])

            assert isinstance(result, InsertResult)
            assert result.success is False
            assert result.error == "Invalid async ID"
            assert result.collection_name == "async_validation_test"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_insert_collection_error(self, config):
        """Test async bulk insert with collection operation errors."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        chunk = DocumentChunk(
            id="async_error_chunk",
            content="Async test content",
            metadata={"test": "async_data"},
            start_position=0,
            end_position=10,
        )

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)
            mock_collection = AsyncMock()
            mock_collection.name = "async_error_test"
            mock_collection.add = AsyncMock(
                side_effect=RuntimeError("Async collection error")
            )

            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            result = await client.bulk_insert(mock_collection, [chunk])

            assert isinstance(result, InsertResult)
            assert result.success is False
            assert result.error == "Async collection error"
            assert result.collection_name == "async_error_test"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_insert_semaphore_control(self, config):
        """Test that semaphore properly controls concurrent batch processing."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        # Create moderate number of chunks to test semaphore
        chunks = []
        for i in range(250):  # 250 chunks = 3 batches of 100
            chunks.append(
                DocumentChunk(
                    id=f"semaphore_chunk_{i}",
                    content=f"Semaphore test content {i}",
                    metadata={"batch_test": True, "index": i},
                    start_position=i * 10,
                    end_position=(i + 1) * 10,
                )
            )

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)
            mock_collection = AsyncMock()
            mock_collection.name = "semaphore_test"
            mock_collection.add = AsyncMock()

            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            result = await client.bulk_insert(mock_collection, chunks)

            assert isinstance(result, InsertResult)
            assert result.success is True
            assert result.chunks_inserted == 250

            # Should call add 3 times for batching (100 + 100 + 50)
            assert mock_collection.add.call_count == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_collections(self, config):
        """Test async list_collections method."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)
            mock_collections = [MagicMock(), MagicMock()]
            mock_client.list_collections = AsyncMock(return_value=mock_collections)

            # Since chromadb.AsyncHttpClient is async, we need to mock it properly
            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            collections = await client.list_collections()

            assert collections == mock_collections
            mock_client.list_collections.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_collection(self, config):
        """Test async delete_collection method."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)
            mock_client.delete_collection = AsyncMock()

            # Since chromadb.AsyncHttpClient is async, we need to mock it properly
            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            await client.delete_collection("test_collection")

            mock_client.delete_collection.assert_called_once_with("test_collection")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_error_handling_chromadb_exceptions(self, config):
        """Test proper handling of ChromaDB-specific exceptions."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)
            # Simulate ChromaDB exception
            from chromadb.errors import NotFoundError

            mock_client.get_collection = AsyncMock(
                side_effect=NotFoundError("Collection not found")
            )

            # Since chromadb.AsyncHttpClient is async, we need to mock it properly
            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            with pytest.raises(NotFoundError):
                await client.get_collection("nonexistent_collection")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_semaphore_concurrency_control(self, config):
        """Test that semaphore properly controls concurrency."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)

            # Since chromadb.AsyncHttpClient is async, we need to mock it properly
            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config, max_concurrent_operations=2)
            await client.connect()

            # Test that semaphore is properly initialized
            assert client._semaphore._value == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_performance_tracking(self, config, sample_chunks):
        """Test that performance metrics are properly tracked."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)
            mock_collection = AsyncMock()
            mock_collection.name = "test_collection"
            mock_collection.add = AsyncMock()

            # Since chromadb.AsyncHttpClient is async, we need to mock it properly
            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            client = AsyncChromaDBClient(config)
            await client.connect()

            result = await client.bulk_insert(mock_collection, sample_chunks)

            # Check that processing time is tracked
            assert result.processing_time > 0
            assert result.insertion_rate > 0
