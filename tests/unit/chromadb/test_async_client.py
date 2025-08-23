"""Unit tests for AsyncChromaDBClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shard_markdown.config import Settings
from shard_markdown.core.models import DocumentChunk, InsertResult


class TestAsyncChromaDBClient:
    """Test AsyncChromaDBClient implementation."""

    @pytest.fixture
    def config(self) -> Settings:
        """Create test ChromaDB configuration."""
        return Settings(
            chroma_host="localhost",
            chroma_port=8000,
            chroma_auth_token=None,
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

    @pytest.fixture
    def mock_chromadb_async_client(self):
        """Consolidated fixture for ChromaDB async client mocking."""
        with patch("chromadb.AsyncHttpClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.heartbeat = AsyncMock(return_value=None)

            # Setup common mock methods
            mock_collection = AsyncMock()
            mock_collection.name = "test_collection"
            mock_collection.add = AsyncMock()

            mock_client.get_collection = AsyncMock(return_value=mock_collection)
            mock_client.get_or_create_collection = AsyncMock(
                return_value=mock_collection
            )
            mock_client.list_collections = AsyncMock(
                return_value=[MagicMock(), MagicMock()]
            )
            mock_client.delete_collection = AsyncMock()

            # Since chromadb.AsyncHttpClient is async, we need to mock it properly
            async def async_mock_client(*args, **kwargs):
                return mock_client

            mock_client_class.side_effect = async_mock_client

            # Return both the mock class and the mock client for flexibility
            yield mock_client_class, mock_client, mock_collection

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
    async def test_async_context_manager(self, config, mock_chromadb_async_client):
        """Test AsyncChromaDBClient works as async context manager."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        mock_client_class, mock_client, _ = mock_chromadb_async_client

        async with AsyncChromaDBClient(config) as client:
            assert client.client == mock_client
            mock_client_class.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_method(self, config, mock_chromadb_async_client):
        """Test async connect method."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        mock_client_class, mock_client, _ = mock_chromadb_async_client

        client = AsyncChromaDBClient(config)
        await client.connect()

        assert client.client == mock_client
        assert client._connection_validated
        mock_client_class.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_collection(self, config, mock_chromadb_async_client):
        """Test async get_collection method."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        _, mock_client, mock_collection = mock_chromadb_async_client

        client = AsyncChromaDBClient(config)
        await client.connect()

        collection = await client.get_collection("test_collection")

        assert collection == mock_collection
        mock_client.get_collection.assert_called_once_with("test_collection")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_or_create_collection(self, config, mock_chromadb_async_client):
        """Test async get_or_create_collection method."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        _, mock_client, mock_collection = mock_chromadb_async_client

        client = AsyncChromaDBClient(config)
        await client.connect()

        collection = await client.get_or_create_collection("test_collection")

        assert collection == mock_collection
        mock_client.get_or_create_collection.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_bulk_insert(self, config, sample_chunks, mock_chromadb_async_client):
        """Test async bulk_insert method."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        _, mock_client, mock_collection = mock_chromadb_async_client

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
    async def test_bulk_insert_empty_chunks(self, config, mock_chromadb_async_client):
        """Test bulk_insert with empty chunks list."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        _, mock_client, mock_collection = mock_chromadb_async_client

        client = AsyncChromaDBClient(config)
        await client.connect()

        result = await client.bulk_insert(mock_collection, [])

        assert isinstance(result, InsertResult)
        assert result.success is True
        assert result.chunks_inserted == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_batch_processing(
        self, config, mock_chromadb_async_client
    ):
        """Test concurrent processing of large chunk batches."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        # Create a large number of chunks to test batching
        large_chunks = [
            DocumentChunk(
                id=f"chunk_{i}",
                content=f"Test content {i}",
                metadata={"batch": i // 100},
            )
            for i in range(500)  # 500 chunks to test batching
        ]

        _, mock_client, mock_collection = mock_chromadb_async_client

        client = AsyncChromaDBClient(config)
        await client.connect()

        result = await client.bulk_insert(mock_collection, large_chunks)

        assert result.success is True
        assert result.chunks_inserted == 500
        # Should be called multiple times due to batching
        assert mock_collection.add.call_count > 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_collections(self, config, mock_chromadb_async_client):
        """Test async list_collections method."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        _, mock_client, _ = mock_chromadb_async_client

        client = AsyncChromaDBClient(config)
        await client.connect()

        collections = await client.list_collections()

        assert len(collections) == 2  # We set up 2 mock collections in fixture
        mock_client.list_collections.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_collection(self, config, mock_chromadb_async_client):
        """Test async delete_collection method."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        _, mock_client, _ = mock_chromadb_async_client

        client = AsyncChromaDBClient(config)
        await client.connect()

        await client.delete_collection("test_collection")

        mock_client.delete_collection.assert_called_once_with("test_collection")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_error_handling_chromadb_exceptions(
        self, config, mock_chromadb_async_client
    ):
        """Test proper handling of ChromaDB-specific exceptions."""
        from chromadb.errors import NotFoundError

        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        _, mock_client, _ = mock_chromadb_async_client

        # Override the get_collection to raise an error
        mock_client.get_collection = AsyncMock(
            side_effect=NotFoundError("Collection not found")
        )

        client = AsyncChromaDBClient(config)
        await client.connect()

        with pytest.raises(NotFoundError):
            await client.get_collection("nonexistent_collection")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_semaphore_concurrency_control(
        self, config, mock_chromadb_async_client
    ):
        """Test that semaphore properly controls concurrency."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        _, mock_client, _ = mock_chromadb_async_client

        client = AsyncChromaDBClient(config, max_concurrent_operations=2)
        await client.connect()

        # Test that semaphore is properly initialized
        assert client._semaphore._value == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_performance_tracking(
        self, config, sample_chunks, mock_chromadb_async_client
    ):
        """Test that performance metrics are properly tracked."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        _, mock_client, mock_collection = mock_chromadb_async_client

        client = AsyncChromaDBClient(config)
        await client.connect()

        result = await client.bulk_insert(mock_collection, sample_chunks)

        # Check that processing time is tracked
        assert result.processing_time > 0
        assert result.insertion_rate > 0
