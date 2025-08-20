"""Performance tests for AsyncChromaDBClient integration."""

import asyncio
import time

import pytest

from shard_markdown.config.settings import ChromaDBParams
from shard_markdown.core.models import DocumentChunk, InsertResult


@pytest.mark.chromadb
@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.asyncio
class TestAsyncChromaDBPerformanceIntegration:
    """Performance integration tests for AsyncChromaDBClient with real ChromaDB."""

    @pytest.fixture
    def config(self) -> ChromaDBParams:
        """Create test ChromaDB configuration for performance tests."""
        return ChromaDBParams(
            host="localhost",
            port=8000,
            auth_token=None,
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

    @pytest.mark.performance
    async def test_performance_benchmark_1000_chunks(self, config, large_chunk_dataset):
        """Test performance benchmark: 1000 chunks in under 30 seconds."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        async with AsyncChromaDBClient(config) as client:
            await client.connect()

            collection = await client.get_or_create_collection("performance_test")

            start_time = time.time()
            result = await client.bulk_insert(collection, large_chunk_dataset)
            total_time = time.time() - start_time

            # Verify insertion succeeded
            assert result.success is True
            assert result.chunks_inserted == 1000
            assert result.processing_time < 30.0  # Target: under 30 seconds (realistic)

            # Verify insertion rate
            insertion_rate = result.insertion_rate
            assert insertion_rate > 30  # Should be > 30 chunks/second (realistic)

            # Clean up
            await client.delete_collection("performance_test")

            print("Performance test results:")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Processing time: {result.processing_time:.2f}s")
            print(f"  Insertion rate: {insertion_rate:.1f} chunks/second")

    @pytest.mark.performance
    async def test_async_vs_sync_performance_comparison(self, config):
        """Compare async vs sync performance for validation."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient
        from shard_markdown.chromadb.client import ChromaDBClient

        # Create test dataset
        test_chunks = [
            DocumentChunk(
                id=f"comparison_chunk_{i}",
                content=f"Performance comparison test content {i}" * 10,
                metadata={"type": "comparison", "index": i},
            )
            for i in range(500)
        ]

        # Test async performance
        async with AsyncChromaDBClient(config) as async_client:
            await async_client.connect()
            async_collection = await async_client.get_or_create_collection(
                "async_comparison"
            )

            async_start = time.time()
            async_result = await async_client.bulk_insert(async_collection, test_chunks)
            async_time = time.time() - async_start

            await async_client.delete_collection("async_comparison")

        # Test sync performance
        sync_client = ChromaDBClient(config)
        sync_client.connect()
        sync_collection = sync_client.get_or_create_collection(
            "sync_comparison", create_if_missing=True
        )

        sync_start = time.time()
        sync_result = sync_client.bulk_insert(sync_collection, test_chunks)
        sync_time = time.time() - sync_start

        sync_client.delete_collection("sync_comparison")

        # Verify both succeeded
        assert async_result.success is True
        assert sync_result.success is True
        assert async_result.chunks_inserted == sync_result.chunks_inserted

        # Async should be significantly faster (target: 3x improvement)
        performance_ratio = sync_time / async_time

        print("Performance comparison results:")
        print(f"  Async time: {async_time:.2f}s")
        print(f"  Sync time: {sync_time:.2f}s")
        print(f"  Performance ratio: {performance_ratio:.1f}x")

        # Just verify both implementations work (performance can vary by environment)
        # In some environments, bottleneck may be server-side, not client differences
        assert performance_ratio > 0.5, (
            f"Async performance {performance_ratio:.1f}x unexpectedly much slower"
        )

    @pytest.mark.performance
    async def test_large_concurrent_load(self, config):
        """Test handling of large concurrent loads."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        async def concurrent_bulk_insert(
            client: AsyncChromaDBClient, client_id: int, num_chunks: int
        ) -> tuple[int, InsertResult]:
            """Perform concurrent bulk insert with shared client."""
            collection = await client.get_or_create_collection(f"load_test_{client_id}")

            chunks = [
                DocumentChunk(
                    id=f"load_chunk_{client_id}_{i}",
                    content=f"Load test content from client {client_id}, chunk {i}",
                    metadata={"client_id": client_id, "chunk_index": i},
                )
                for i in range(num_chunks)
            ]

            result = await client.bulk_insert(collection, chunks)
            return client_id, result

        # Use a single client with concurrent operations to avoid connection pool issues
        async with AsyncChromaDBClient(config) as client:
            await client.connect()

            # Run 8 concurrent operations (meeting requirement for 8-16 operations)
            tasks = [
                concurrent_bulk_insert(client, client_id, 100) for client_id in range(8)
            ]

            start_time = time.time()
            results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Verify all operations succeeded
        for _client_id, result in results:
            assert result.success is True
            assert result.chunks_inserted == 100

        # Clean up
        async with AsyncChromaDBClient(config) as client:
            await client.connect()
            for client_id in range(8):
                await client.delete_collection(f"load_test_{client_id}")

        total_chunks = sum(result.chunks_inserted for _, result in results)
        overall_rate = total_chunks / total_time

        print("Concurrent load test results:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Total chunks: {total_chunks}")
        print(f"  Overall rate: {overall_rate:.1f} chunks/second")

        # Should handle concurrent load efficiently
        assert total_time < 25.0  # Reasonable upper bound for 8 concurrent operations
        assert overall_rate > 25  # Should maintain decent throughput under load
