"""Performance benchmarks for document processing."""

import statistics
import time
from typing import Any

import psutil
import pytest

from shard_markdown.config.settings import ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor


@pytest.mark.performance
class TestProcessingBenchmarks:
    """Performance benchmarks for document processing."""

    @pytest.fixture
    def small_config(self) -> ChunkingConfig:
        """Create small chunk configuration."""
        return ChunkingConfig(default_size=500, default_overlap=100)

    @pytest.fixture
    def medium_config(self) -> ChunkingConfig:
        """Create medium chunk configuration."""
        return ChunkingConfig(default_size=1000, default_overlap=200)

    @pytest.fixture
    def large_config(self) -> ChunkingConfig:
        """Create large chunk configuration."""
        return ChunkingConfig(default_size=2000, default_overlap=400)

    @pytest.fixture
    def benchmark_processor(self, medium_config: ChunkingConfig) -> DocumentProcessor:
        """Create processor for benchmarking."""
        return DocumentProcessor(chunking_config=medium_config)

    @pytest.mark.benchmark
    @pytest.mark.performance
    def test_small_document_processing_speed(
        self,
        benchmark_processor: DocumentProcessor,
        small_markdown_file: Any,
        benchmark: Any,
    ) -> None:
        """Benchmark processing speed for small documents."""

        def process_small_doc() -> Any:
            return benchmark_processor.process_file(
                file_path=small_markdown_file, collection_name="benchmark-small"
            )

        result = benchmark(process_small_doc)

        # Assert result is successful
        assert result.success is True
        assert result.chunks_created > 0

    @pytest.mark.benchmark
    @pytest.mark.performance
    def test_medium_document_processing_speed(
        self,
        benchmark_processor: DocumentProcessor,
        medium_markdown_file: Any,
        benchmark: Any,
    ) -> None:
        """Benchmark processing speed for medium documents."""

        def process_medium_doc() -> Any:
            return benchmark_processor.process_file(
                file_path=medium_markdown_file, collection_name="benchmark-medium"
            )

        result = benchmark(process_medium_doc)

        assert result.success is True
        assert result.chunks_created > 0

    @pytest.mark.benchmark
    @pytest.mark.performance
    def test_large_document_processing_speed(
        self,
        benchmark_processor: DocumentProcessor,
        large_markdown_file: Any,
        benchmark: Any,
    ) -> None:
        """Benchmark processing speed for large documents."""

        def process_large_doc() -> Any:
            return benchmark_processor.process_file(
                file_path=large_markdown_file, collection_name="benchmark-large"
            )

        result = benchmark(process_large_doc)

        assert result.success is True
        assert result.chunks_created > 0

    @pytest.mark.benchmark
    @pytest.mark.performance
    def test_batch_processing_speed(
        self,
        benchmark_processor: DocumentProcessor,
        sample_markdown_files: Any,
        benchmark: Any,
    ) -> None:
        """Benchmark batch processing speed."""

        def process_batch() -> Any:
            return benchmark_processor.process_batch(
                file_paths=sample_markdown_files, collection_name="benchmark-batch"
            )

        result = benchmark(process_batch)

        assert result.total_files == len(sample_markdown_files)
        assert result.successful_files > 0

    @pytest.mark.performance
    def test_memory_usage_single_file(
        self,
        benchmark_processor: DocumentProcessor,
        large_markdown_file: Any,
    ) -> None:
        """Test memory usage for single file processing."""
        process = psutil.Process()

        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process file
        result = benchmark_processor.process_file(
            file_path=large_markdown_file, collection_name="memory-test"
        )

        # Peak memory
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - baseline_memory

        # Assert reasonable memory usage (less than 100MB increase for most files)
        assert memory_increase < 100  # MB
        assert result.success is True

    @pytest.mark.performance
    def test_memory_usage_batch_processing(
        self,
        benchmark_processor: DocumentProcessor,
        sample_markdown_files: Any,
    ) -> None:
        """Test memory usage for batch processing."""
        process = psutil.Process()

        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process batch
        result = benchmark_processor.process_batch(
            file_paths=sample_markdown_files, collection_name="memory-batch-test"
        )

        # Peak memory
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - baseline_memory

        # Assert reasonable memory scaling
        expected_max_memory = len(sample_markdown_files) * 20  # 20MB per file max
        assert memory_increase < expected_max_memory
        assert result.total_files == len(sample_markdown_files)

    @pytest.mark.performance
    def test_processing_consistency(
        self,
        benchmark_processor: DocumentProcessor,
        medium_markdown_file: Any,
    ) -> None:
        """Test processing time consistency."""
        processing_times = []

        # Run multiple processing iterations
        for _ in range(10):
            start_time = time.time()
            result = benchmark_processor.process_file(
                file_path=medium_markdown_file, collection_name="consistency-test"
            )
            end_time = time.time()

            assert result.success is True
            processing_times.append(end_time - start_time)

        # Calculate statistics
        mean_time = statistics.mean(processing_times)
        std_dev = statistics.stdev(processing_times)
        coefficient_of_variation = std_dev / mean_time

        # Assert reasonable consistency (CV < 0.3 means fairly consistent)
        assert coefficient_of_variation < 0.3

    @pytest.mark.performance
    def test_chunk_size_scaling(
        self,
        small_config: ChunkingConfig,
        medium_config: ChunkingConfig,
        large_config: ChunkingConfig,
        medium_markdown_file: Any,
    ) -> None:
        """Test how processing time scales with chunk size."""
        configs = [
            ("small", small_config),
            ("medium", medium_config),
            ("large", large_config),
        ]

        results = {}

        for config_name, config in configs:
            processor = DocumentProcessor(chunking_config=config)

            start_time = time.time()
            result = processor.process_file(
                file_path=medium_markdown_file, collection_name=f"scaling-{config_name}"
            )
            end_time = time.time()

            assert result.success is True

            results[config_name] = {
                "processing_time": end_time - start_time,
                "chunks_created": result.chunks_created,
                "chunk_size": config.default_size,
            }

        # Smaller chunks should create more chunks
        assert results["small"]["chunks_created"] > results["medium"]["chunks_created"]
        assert results["medium"]["chunks_created"] > results["large"]["chunks_created"]

    @pytest.mark.performance
    def test_concurrent_processing_safety(
        self,
        benchmark_processor: DocumentProcessor,
        sample_markdown_files: Any,
    ) -> None:
        """Test that processing is thread-safe (basic check)."""
        import threading
        from queue import Queue

        results_queue: Queue[Any] = Queue()

        def process_file(file_path: Any) -> None:
            result = benchmark_processor.process_file(
                file_path=file_path, collection_name="concurrent-test"
            )
            results_queue.put(result)

        # Create threads for processing different files
        threads = []
        files_to_process = sample_markdown_files[:3]  # Limit to 3 for test speed

        for file_path in files_to_process:
            thread = threading.Thread(target=process_file, args=(file_path,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())

        # Assert all processing succeeded
        assert len(results) == len(files_to_process)
        for result in results:
            assert result.success is True

    @pytest.mark.performance
    def test_large_file_handling(
        self,
        benchmark_processor: DocumentProcessor,
        very_large_markdown_file: Any,
    ) -> None:
        """Test processing of very large files."""
        start_time = time.time()

        result = benchmark_processor.process_file(
            file_path=very_large_markdown_file, collection_name="large-file-test"
        )

        end_time = time.time()
        processing_time = end_time - start_time

        # Assert processing completed successfully
        assert result.success is True
        assert result.chunks_created > 0

        # Assert reasonable processing time (should complete within reasonable time)
        # This is a rough check - adjust based on actual requirements
        assert processing_time < 60  # seconds

    @pytest.mark.performance
    def test_processing_rate_calculation(
        self,
        benchmark_processor: DocumentProcessor,
        sample_markdown_files: Any,
    ) -> None:
        """Test processing rate calculations."""
        batch_result = benchmark_processor.process_batch(
            file_paths=sample_markdown_files, collection_name="rate-test"
        )

        # Verify rate calculations are reasonable
        assert batch_result.processing_speed > 0  # files per second

        if batch_result.successful_files > 0:
            assert batch_result.average_chunks_per_file > 0

        # Success rate should be a percentage
        assert 0 <= batch_result.success_rate <= 100
