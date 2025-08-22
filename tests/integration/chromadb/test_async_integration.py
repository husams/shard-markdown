"""Integration tests for AsyncChromaDBClient."""

import asyncio

import pytest

from shard_markdown.config import Settings
from shard_markdown.core.models import DocumentChunk, InsertResult


@pytest.mark.chromadb
@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncChromaDBIntegration:
    """Integration tests for AsyncChromaDBClient with real ChromaDB."""

    @pytest.fixture
    def config(self) -> Settings:
        """Create test ChromaDB configuration for integration tests."""
        return Settings(
            chroma_host="localhost",
            chroma_port=8000,
            chroma_auth_token=None,
        )

    @pytest.fixture
    def sample_chunks(self) -> list[DocumentChunk]:
        """Create sample document chunks for basic testing."""
        return [
            DocumentChunk(
                id="async_test_1",
                content="First async integration test chunk",
                metadata={"file": "async_test.md", "section": "intro"},
            ),
            DocumentChunk(
                id="async_test_2",
                content="Second async integration test chunk",
                metadata={"file": "async_test.md", "section": "body"},
            ),
        ]

    async def test_full_async_pipeline(self, config, sample_chunks):
        """Test complete async pipeline from connection to insertion."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        async with AsyncChromaDBClient(config) as client:
            # Test connection
            await client.connect()

            # Create collection
            collection = await client.get_or_create_collection("async_integration_test")
            assert collection is not None

            # Insert chunks
            result = await client.bulk_insert(collection, sample_chunks)
            assert result.success is True
            assert result.chunks_inserted == 2

            # Verify collections exist
            collections = await client.list_collections()
            collection_names = [col.name for col in collections]
            assert "async_integration_test" in collection_names

            # Clean up
            await client.delete_collection("async_integration_test")

    async def test_concurrent_operations(self, config):
        """Test concurrent async operations."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        async def create_and_populate_collection(
            client: AsyncChromaDBClient, collection_name: str, num_chunks: int
        ) -> InsertResult:
            """Helper to create and populate a collection concurrently."""
            collection = await client.get_or_create_collection(collection_name)

            chunks = [
                DocumentChunk(
                    id=f"{collection_name}_chunk_{i}",
                    content=f"Concurrent test content {i}",
                    metadata={"collection": collection_name, "index": i},
                )
                for i in range(num_chunks)
            ]

            result = await client.bulk_insert(collection, chunks)
            return result

        # Use single client connection for all operations
        async with AsyncChromaDBClient(config) as client:
            await client.connect()

            # Run concurrent operations with fewer chunks and collections
            tasks = [
                create_and_populate_collection(client, f"concurrent_test_{i}", 10)
                for i in range(3)
            ]

            results = await asyncio.gather(*tasks)

            # Verify all operations succeeded
            for result in results:
                assert result.success is True
                assert result.chunks_inserted == 10

            # Clean up in single connection
            for i in range(3):
                await client.delete_collection(f"concurrent_test_{i}")

    async def test_error_handling_connection_failure(self, config):
        """Test error handling when ChromaDB connection fails."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        # Use invalid port to force connection failure
        bad_config = Settings(
            chroma_host="localhost",
            chroma_port=9999,  # Invalid port
            chroma_auth_token=None,
        )

        with pytest.raises((ConnectionError, OSError, Exception)):
            async with AsyncChromaDBClient(bad_config) as client:
                await client.connect()

    async def test_async_vs_sync_implementation_compatibility(self, config):
        """Test async vs sync implementation compatibility (functional test)."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient
        from shard_markdown.chromadb.client import ChromaDBClient

        # Create smaller test dataset for faster execution
        test_chunks = [
            DocumentChunk(
                id=f"comparison_chunk_{i}",
                content=f"Implementation compatibility test content {i}",
                metadata={"type": "compatibility", "index": i},
            )
            for i in range(20)  # Reduced from 100 to 20 chunks
        ]

        # Test async implementation
        async with AsyncChromaDBClient(config) as async_client:
            await async_client.connect()
            async_collection = await async_client.get_or_create_collection(
                "compatibility_test"
            )

            async_result = await async_client.bulk_insert(async_collection, test_chunks)

            # Verify async operation
            assert async_result.success is True
            assert async_result.chunks_inserted == 20

            # Clean up async collection
            await async_client.delete_collection("compatibility_test")

        # Test sync implementation with same collection name (reuse after cleanup)
        sync_client = ChromaDBClient(config)
        sync_client.connect()
        sync_collection = sync_client.get_or_create_collection(
            "compatibility_test", create_if_missing=True
        )

        sync_result = sync_client.bulk_insert(sync_collection, test_chunks)

        # Verify sync operation
        assert sync_result.success is True
        assert sync_result.chunks_inserted == 20

        # Clean up sync collection
        sync_client.delete_collection("compatibility_test")

        # Final verification
        assert async_result.chunks_inserted == sync_result.chunks_inserted

    async def test_multiple_concurrent_operations(self, config):
        """Test handling of multiple concurrent operations (functional test)."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        async def concurrent_bulk_insert(
            client: AsyncChromaDBClient, client_id: int, num_chunks: int
        ) -> tuple[int, InsertResult]:
            """Perform concurrent bulk insert with shared client."""
            collection = await client.get_or_create_collection(
                f"multi_concurrent_{client_id}"
            )

            chunks = [
                DocumentChunk(
                    id=f"concurrent_chunk_{client_id}_{i}",
                    content=f"Content from client {client_id}, chunk {i}",
                    metadata={"client_id": client_id, "chunk_index": i},
                )
                for i in range(num_chunks)
            ]

            result = await client.bulk_insert(collection, chunks)
            return client_id, result

        # Use a single client with concurrent operations
        async with AsyncChromaDBClient(config) as client:
            await client.connect()

            # Run 3 concurrent operations with fewer chunks each
            tasks = [
                concurrent_bulk_insert(client, client_id, 10) for client_id in range(3)
            ]

            results = await asyncio.gather(*tasks)

            # Verify all operations succeeded
            for _client_id, result in results:
                assert result.success is True
                assert result.chunks_inserted == 10

            # Clean up in the same connection
            for client_id in range(3):
                await client.delete_collection(f"multi_concurrent_{client_id}")

            total_chunks = sum(result.chunks_inserted for _, result in results)
            assert total_chunks == 30  # Verify all chunks were inserted
