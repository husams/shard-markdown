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
    def large_chunk_dataset(self) -> list[DocumentChunk]:
        """Create a large dataset of chunks for performance testing."""
        chunks = []
        for i in range(1000):
            chunk = DocumentChunk(
                id=f"perf_chunk_{i}",
                content=f"This is performance test chunk number {i}. "
                * 10,  # ~400 chars each
                metadata={
                    "file": f"test_file_{i // 100}.md",
                    "section": f"section_{i % 10}",
                    "chunk_index": i,
                    "test_type": "performance",
                },
            )
            chunks.append(chunk)
        return chunks

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
            collection_name: str, num_chunks: int
        ) -> InsertResult:
            """Helper to create and populate a collection concurrently."""
            async with AsyncChromaDBClient(config) as client:
                await client.connect()

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

        # Run multiple concurrent operations
        tasks = [
            create_and_populate_collection(f"concurrent_test_{i}", 50) for i in range(4)
        ]

        results = await asyncio.gather(*tasks)

        # Verify all operations succeeded
        for result in results:
            assert result.success is True
            assert result.chunks_inserted == 50

        # Clean up
        async with AsyncChromaDBClient(config) as client:
            await client.connect()
            for i in range(4):
                await client.delete_collection(f"concurrent_test_{i}")

    async def test_bulk_insert_large_dataset(self, config, large_chunk_dataset):
        """Test bulk insertion of large dataset (functional test)."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        async with AsyncChromaDBClient(config) as client:
            await client.connect()

            collection = await client.get_or_create_collection("bulk_insert_test")

            result = await client.bulk_insert(collection, large_chunk_dataset)

            # Verify insertion succeeded (functional verification only)
            assert result.success is True
            assert result.chunks_inserted == 1000
            assert result.processing_time > 0  # Just verify timing is recorded
            assert result.insertion_rate > 0  # Just verify rate is calculated

            # Clean up
            await client.delete_collection("bulk_insert_test")

    async def test_memory_usage_sustained_operations(self, config):
        """Test memory usage during sustained async operations."""
        import os

        import psutil

        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        async with AsyncChromaDBClient(config) as client:
            await client.connect()

            # Perform multiple sustained operations
            for batch in range(5):
                collection_name = f"memory_test_{batch}"
                collection = await client.get_or_create_collection(collection_name)

                chunks = [
                    DocumentChunk(
                        id=f"memory_chunk_{batch}_{i}",
                        content=f"Memory test content for batch {batch}, chunk {i}" * 5,
                        metadata={"batch": batch, "chunk": i},
                    )
                    for i in range(200)
                ]

                result = await client.bulk_insert(collection, chunks)
                assert result.success is True

                # Clean up immediately to test memory release
                await client.delete_collection(collection_name)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        # Memory growth should be within 15% overhead as per requirements
        max_allowed_growth = initial_memory * 0.15
        assert memory_growth <= max_allowed_growth, (
            f"Memory growth {memory_growth:.1f}MB exceeds 15% limit "
            f"{max_allowed_growth:.1f}MB"
        )

        print("Memory usage test results:")
        print(f"  Initial memory: {initial_memory:.1f}MB")
        print(f"  Final memory: {final_memory:.1f}MB")
        print(
            f"  Memory growth: {memory_growth:.1f}MB "
            f"({memory_growth / initial_memory * 100:.1f}%)"
        )

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

        # Create test dataset
        test_chunks = [
            DocumentChunk(
                id=f"comparison_chunk_{i}",
                content=f"Implementation compatibility test content {i}" * 10,
                metadata={"type": "compatibility", "index": i},
            )
            for i in range(100)  # Smaller dataset for functional testing
        ]

        # Test async implementation
        async with AsyncChromaDBClient(config) as async_client:
            await async_client.connect()
            async_collection = await async_client.get_or_create_collection(
                "async_compatibility"
            )

            async_result = await async_client.bulk_insert(async_collection, test_chunks)
            await async_client.delete_collection("async_compatibility")

        # Test sync implementation
        sync_client = ChromaDBClient(config)
        sync_client.connect()
        sync_collection = sync_client.get_or_create_collection(
            "sync_compatibility", create_if_missing=True
        )

        sync_result = sync_client.bulk_insert(sync_collection, test_chunks)
        sync_client.delete_collection("sync_compatibility")

        # Verify both implementations work correctly
        assert async_result.success is True
        assert sync_result.success is True
        assert async_result.chunks_inserted == sync_result.chunks_inserted
        assert async_result.chunks_inserted == 100

    async def test_multiple_concurrent_operations(self, config):
        """Test handling of multiple concurrent operations (functional test)."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        async def concurrent_bulk_insert(
            client: AsyncChromaDBClient, client_id: int, num_chunks: int
        ) -> tuple[int, InsertResult]:
            """Perform concurrent bulk insert with shared client."""
            collection = await client.get_or_create_collection(
                f"concurrent_test_{client_id}"
            )

            chunks = [
                DocumentChunk(
                    id=f"concurrent_chunk_{client_id}_{i}",
                    content=(
                        f"Concurrent test content from client {client_id}, chunk {i}"
                    ),
                    metadata={"client_id": client_id, "chunk_index": i},
                )
                for i in range(num_chunks)
            ]

            result = await client.bulk_insert(collection, chunks)
            return client_id, result

        # Use a single client with concurrent operations
        async with AsyncChromaDBClient(config) as client:
            await client.connect()

            # Run 4 concurrent operations (functional test)
            tasks = [
                concurrent_bulk_insert(client, client_id, 25) for client_id in range(4)
            ]

            results = await asyncio.gather(*tasks)

        # Verify all operations succeeded
        for _client_id, result in results:
            assert result.success is True
            assert result.chunks_inserted == 25

        # Clean up
        async with AsyncChromaDBClient(config) as client:
            await client.connect()
            for client_id in range(4):
                await client.delete_collection(f"concurrent_test_{client_id}")

        total_chunks = sum(result.chunks_inserted for _, result in results)
        assert total_chunks == 100  # Verify all chunks were inserted
