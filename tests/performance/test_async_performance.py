"""Performance tests for AsyncChromaDBClient."""

import asyncio
import os
import time

import psutil
import pytest

from shard_markdown.config.settings import ChromaDBConfig
from shard_markdown.core.models import DocumentChunk, InsertResult


@pytest.mark.performance
@pytest.mark.asyncio
class TestAsyncChromaDBPerformance:
    """Performance benchmarks for AsyncChromaDBClient."""

    @pytest.fixture
    def config(self) -> ChromaDBConfig:
        """Create test ChromaDB configuration for performance tests."""
        return ChromaDBConfig(
            host="localhost",
            port=8000,
            auth_token=None,
        )

    def create_chunk_dataset(
        self, num_chunks: int, content_size: int = 400
    ) -> list[DocumentChunk]:
        """Create a dataset of chunks for performance testing.

        Args:
            num_chunks: Number of chunks to create
            content_size: Approximate size of each chunk content in characters

        Returns:
            List of DocumentChunk objects
        """
        base_content = "This is performance test content. " * (content_size // 34)

        chunks = []
        for i in range(num_chunks):
            chunk = DocumentChunk(
                id=f"perf_chunk_{i}",
                content=f"{base_content} Chunk {i}",
                metadata={
                    "file": f"performance_test_{i // 100}.md",
                    "section": f"section_{i % 20}",
                    "chunk_index": i,
                    "test_type": "performance",
                    "size_category": "medium" if content_size < 1000 else "large",
                },
            )
            chunks.append(chunk)
        return chunks

    @pytest.mark.parametrize(
        "chunk_count,target_time",
        [
            (100, 1.0),  # 100 chunks in under 1 second
            (500, 2.0),  # 500 chunks in under 2 seconds
            (1000, 3.0),  # 1000 chunks in under 3 seconds (main requirement)
            (2000, 6.0),  # 2000 chunks in under 6 seconds (scalability test)
        ],
    )
    async def test_bulk_insert_performance_targets(
        self, config: ChromaDBConfig, chunk_count: int, target_time: float
    ) -> None:
        """Test bulk insert performance against specific targets."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        chunks = self.create_chunk_dataset(chunk_count)

        async with AsyncChromaDBClient(config) as client:
            await client.connect()

            collection_name = f"perf_test_{chunk_count}"
            collection = await client.get_or_create_collection(collection_name)

            start_time = time.time()
            result = await client.bulk_insert(collection, chunks)
            actual_time = time.time() - start_time

            # Clean up
            await client.delete_collection(collection_name)

            # Assertions
            assert result.success is True
            assert result.chunks_inserted == chunk_count
            assert actual_time < target_time, (
                f"Performance target missed: {actual_time:.2f}s > {target_time:.2f}s "
                f"for {chunk_count} chunks"
            )

            insertion_rate = chunk_count / actual_time
            expected_min_rate = chunk_count / target_time

            print(f"Performance results for {chunk_count} chunks:")
            print(f"  Time: {actual_time:.2f}s (target: <{target_time:.2f}s)")
            print(
                f"  Rate: {insertion_rate:.1f} chunks/s (min: {expected_min_rate:.1f})"
            )
            print(f"  Processing time: {result.processing_time:.2f}s")

    async def test_concurrent_performance_scaling(self, config: ChromaDBConfig) -> None:
        """Test performance scaling with concurrent operations."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        async def concurrent_insert_task(
            task_id: int, num_chunks: int
        ) -> tuple[int, InsertResult, float]:
            """Perform concurrent insert task."""
            chunks = self.create_chunk_dataset(num_chunks)

            async with AsyncChromaDBClient(
                config, max_concurrent_operations=8
            ) as client:
                await client.connect()

                collection_name = f"concurrent_perf_{task_id}"
                collection = await client.get_or_create_collection(collection_name)

                start_time = time.time()
                result = await client.bulk_insert(collection, chunks)
                task_time = time.time() - start_time

                # Clean up
                await client.delete_collection(collection_name)

                return task_id, result, task_time

        # Test different levels of concurrency
        concurrency_levels = [1, 2, 4, 8]
        chunks_per_task = 200

        for concurrency in concurrency_levels:
            tasks = [
                concurrent_insert_task(i, chunks_per_task) for i in range(concurrency)
            ]

            overall_start = time.time()
            results = await asyncio.gather(*tasks)
            overall_time = time.time() - overall_start

            # Verify all tasks succeeded
            total_chunks = 0
            for _task_id, result, _task_time in results:
                assert result.success is True
                total_chunks += result.chunks_inserted

            overall_rate = total_chunks / overall_time

            print(f"Concurrency {concurrency}x results:")
            print(f"  Total time: {overall_time:.2f}s")
            print(f"  Total chunks: {total_chunks}")
            print(f"  Overall rate: {overall_rate:.1f} chunks/s")
            print(f"  Efficiency: {overall_rate / (chunks_per_task / 3.0) * 100:.1f}%")

    async def test_memory_efficiency_large_datasets(
        self, config: ChromaDBConfig
    ) -> None:
        """Test memory efficiency with large datasets."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        process = psutil.Process(os.getpid())

        # Test with progressively larger datasets
        dataset_sizes = [500, 1000, 2000, 5000]
        memory_measurements = []

        for size in dataset_sizes:
            # Measure initial memory
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            chunks = self.create_chunk_dataset(size, content_size=800)  # Larger chunks

            async with AsyncChromaDBClient(config) as client:
                await client.connect()

                collection_name = f"memory_test_{size}"
                collection = await client.get_or_create_collection(collection_name)

                start_time = time.time()
                result = await client.bulk_insert(collection, chunks)
                operation_time = time.time() - start_time

                # Measure peak memory after operation
                peak_memory = process.memory_info().rss / 1024 / 1024  # MB

                # Clean up
                await client.delete_collection(collection_name)

                # Measure memory after cleanup
                cleanup_memory = process.memory_info().rss / 1024 / 1024  # MB

                memory_growth = peak_memory - initial_memory
                memory_per_chunk = memory_growth / size if size > 0 else 0

                measurement = {
                    "size": size,
                    "initial_memory": initial_memory,
                    "peak_memory": peak_memory,
                    "cleanup_memory": cleanup_memory,
                    "memory_growth": memory_growth,
                    "memory_per_chunk": memory_per_chunk,
                    "operation_time": operation_time,
                    "success": result.success,
                }
                memory_measurements.append(measurement)

                print(f"Memory test for {size} chunks:")
                print(
                    f"  Memory growth: {memory_growth:.1f}MB "
                    f"({memory_per_chunk:.3f}MB per chunk)"
                )
                print(f"  Peak memory: {peak_memory:.1f}MB")
                print(f"  Time: {operation_time:.2f}s")

                # Verify memory efficiency requirements
                assert result.success is True
                assert memory_per_chunk < 0.1, (
                    f"Memory per chunk too high: {memory_per_chunk:.3f}MB > 0.1MB"
                )

        # Verify memory usage scales reasonably
        largest_test = memory_measurements[-1]
        assert largest_test["memory_growth"] < 500, (
            f"Total memory growth too high: {largest_test['memory_growth']:.1f}MB > "
            "500MB"
        )

    async def test_async_vs_sync_performance_benchmark(
        self, config: ChromaDBConfig
    ) -> None:
        """Comprehensive benchmark comparing async vs sync performance."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient
        from shard_markdown.chromadb.client import ChromaDBClient

        test_sizes = [100, 500, 1000]
        benchmark_results = []

        for size in test_sizes:
            chunks = self.create_chunk_dataset(size)

            # Async performance test
            async with AsyncChromaDBClient(config) as async_client:
                await async_client.connect()
                async_collection = await async_client.get_or_create_collection(
                    f"async_bench_{size}"
                )

                async_start = time.time()
                async_result = await async_client.bulk_insert(async_collection, chunks)
                async_time = time.time() - async_start

                await async_client.delete_collection(f"async_bench_{size}")

            # Sync performance test
            sync_client = ChromaDBClient(config)
            sync_client.connect()
            sync_collection = sync_client.get_or_create_collection(f"sync_bench_{size}")

            sync_start = time.time()
            sync_result = sync_client.bulk_insert(sync_collection, chunks)
            sync_time = time.time() - sync_start

            sync_client.delete_collection(f"sync_bench_{size}")

            # Calculate performance metrics
            performance_ratio = sync_time / async_time
            async_rate = size / async_time
            sync_rate = size / sync_time

            result = {
                "size": size,
                "async_time": async_time,
                "sync_time": sync_time,
                "performance_ratio": performance_ratio,
                "async_rate": async_rate,
                "sync_rate": sync_rate,
                "async_success": async_result.success,
                "sync_success": sync_result.success,
            }
            benchmark_results.append(result)

            print(f"Benchmark for {size} chunks:")
            print(f"  Async: {async_time:.2f}s ({async_rate:.1f} chunks/s)")
            print(f"  Sync:  {sync_time:.2f}s ({sync_rate:.1f} chunks/s)")
            print(f"  Speedup: {performance_ratio:.1f}x")

            # Verify both operations succeeded
            assert async_result.success is True
            assert sync_result.success is True

            # Verify performance improvement (should be at least 2x for larger datasets)
            if size >= 500:
                assert performance_ratio >= 2.0, (
                    f"Async performance not sufficient: {performance_ratio:.1f}x < "
                    f"2.0x for {size} chunks"
                )

        # Overall performance summary
        avg_speedup = sum(r["performance_ratio"] for r in benchmark_results) / len(
            benchmark_results
        )
        max_speedup = max(r["performance_ratio"] for r in benchmark_results)

        print("\nOverall Performance Summary:")
        print(f"  Average speedup: {avg_speedup:.1f}x")
        print(f"  Maximum speedup: {max_speedup:.1f}x")
        print(f"  Target achieved: {max_speedup >= 3.0}")

    async def test_throughput_under_sustained_load(
        self, config: ChromaDBConfig
    ) -> None:
        """Test throughput consistency under sustained load."""
        from shard_markdown.chromadb.async_client import AsyncChromaDBClient

        # Run sustained operations for performance validation
        operation_count = 10
        chunks_per_operation = 200
        throughput_measurements = []

        async with AsyncChromaDBClient(config) as client:
            await client.connect()

            for i in range(operation_count):
                chunks = self.create_chunk_dataset(chunks_per_operation)

                collection_name = f"sustained_test_{i}"
                collection = await client.get_or_create_collection(collection_name)

                start_time = time.time()
                result = await client.bulk_insert(collection, chunks)
                operation_time = time.time() - start_time

                throughput = chunks_per_operation / operation_time
                throughput_measurements.append(throughput)

                # Clean up immediately
                await client.delete_collection(collection_name)

                assert result.success is True

                print(f"Operation {i + 1}: {throughput:.1f} chunks/s")

        # Analyze throughput consistency
        avg_throughput = sum(throughput_measurements) / len(throughput_measurements)
        min_throughput = min(throughput_measurements)
        max_throughput = max(throughput_measurements)
        throughput_variance = max_throughput - min_throughput

        print("\nSustained Load Results:")
        print(f"  Average throughput: {avg_throughput:.1f} chunks/s")
        print(f"  Min throughput: {min_throughput:.1f} chunks/s")
        print(f"  Max throughput: {max_throughput:.1f} chunks/s")
        print(f"  Variance: {throughput_variance:.1f} chunks/s")

        # Verify consistent performance (variance should be reasonable)
        variance_ratio = throughput_variance / avg_throughput
        assert variance_ratio < 0.5, (
            f"Throughput too variable: {variance_ratio:.2f} > 0.5"
        )

        # Verify minimum acceptable throughput
        assert min_throughput > 50, (
            f"Minimum throughput too low: {min_throughput:.1f} < 50 chunks/s"
        )
