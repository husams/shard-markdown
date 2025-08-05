"""Performance benchmarks for document processing."""

import statistics
import time
from typing import Any

import psutil
import pytest

from shard_markdown.core.models import ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor


@pytest.mark.performance
class TestProcessingBenchmarks:
    """Performance benchmarks for document processing."""

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create processor for benchmarking."""
        return DocumentProcessor(chunking_config)

    @pytest.fixture
    def benchmark_config(self) -> ChunkingConfig:
        """Provide standard configuration for benchmarking."""
        return ChunkingConfig(chunk_size=1000, overlap=200, method="structure")

    def test_single_document_processing_benchmark(
        self, temp_dir: Any, benchmark_config: ChunkingConfig
    ) -> None:
        """Benchmark processing of a single document."""
        processor = DocumentProcessor(benchmark_config)

        # Create test document
        doc_content = self._generate_document_content(
            sections=20, paragraphs_per_section=5
        )
        doc_path = temp_dir / "benchmark_doc.md"
        doc_path.write_text(doc_content)

        # Warmup run
        processor.process_document(doc_path, "warmup-collection")

        # Benchmark runs
        times = []
        chunks_created = []

        for run in range(5):
            start_time = time.perf_counter()
            result = processor.process_document(doc_path, f"benchmark-{run}")
            end_time = time.perf_counter()

            assert result.success, f"Processing failed on run {run}: {result.error}"

            times.append(end_time - start_time)
            chunks_created.append(result.chunks_created)

        # Calculate statistics
        avg_time = statistics.mean(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0
        avg_chunks = statistics.mean(chunks_created)

        print("\nSingle Document Benchmark Results:")
        print(f"Average processing time: {avg_time:.3f}s ± {std_dev:.3f}s")
        print(f"Average chunks created: {avg_chunks:.1f}")
        print(f"Processing rate: {avg_chunks / avg_time:.1f} chunks/second")
        print(f"Document size: {len(doc_content)} characters")

        # Performance assertions
        assert avg_time < 5.0, f"Processing too slow: {avg_time:.3f}s"
        assert avg_chunks > 0, "No chunks created"
        assert std_dev < avg_time * 0.5, (
            f"High variance in processing time: {std_dev:.3f}s"
        )

    def test_batch_processing_benchmark(
        self, temp_dir: Any, benchmark_config: ChunkingConfig
    ) -> None:
        """Benchmark batch processing performance."""
        processor = DocumentProcessor(benchmark_config)

        # Create multiple test documents
        documents = []
        for i in range(10):
            doc_content = self._generate_document_content(
                sections=10, paragraphs_per_section=3
            )
            doc_path = temp_dir / f"batch_doc_{i:02d}.md"
            doc_path.write_text(doc_content)
            documents.append(doc_path)

        # Test different worker counts
        worker_counts = [1, 2, 4]
        results: dict[int, dict[str, Any]] = {}

        for workers in worker_counts:
            start_time = time.perf_counter()
            batch_result = processor.process_batch(
                documents, f"batch-{workers}", max_workers=workers
            )
            end_time = time.perf_counter()

            processing_time = end_time - start_time
            results[workers] = {
                "time": processing_time,
                "successful_files": batch_result.successful_files,
                "total_chunks": batch_result.total_chunks,
                "throughput": len(documents) / processing_time,
            }

        print("\nBatch Processing Benchmark Results:")
        for workers, result in results.items():
            print(f"Workers: {workers}")
            print(f"  Processing time: {result['time']:.3f}s")
            print(f"  Successful files: {result['successful_files']}/{len(documents)}")
            print(f"  Total chunks: {result['total_chunks']}")
            print(f"  Throughput: {result['throughput']:.1f} files/second")

        # Performance assertions
        assert all(r["successful_files"] == len(documents) for r in results.values())
        assert results[4]["time"] <= results[1]["time"], (
            "Concurrency should improve performance"
        )

    @pytest.mark.parametrize(
        "chunk_size,overlap",
        [
            (500, 100),
            (1000, 200),
            (1500, 300),
            (2000, 400),
        ],
    )
    def test_chunking_performance_by_size(
        self, temp_dir: Any, chunk_size: int, overlap: int
    ) -> dict[str, Any]:
        """Benchmark performance with different chunk sizes."""
        config = ChunkingConfig(
            chunk_size=chunk_size, overlap=overlap, method="structure"
        )
        processor = DocumentProcessor(config)

        # Create consistent test document
        doc_content = self._generate_document_content(
            sections=50, paragraphs_per_section=4
        )
        doc_path = temp_dir / f"chunk_size_test_{chunk_size}.md"
        doc_path.write_text(doc_content)

        # Benchmark
        start_time = time.perf_counter()
        result = processor.process_document(doc_path, f"chunk-size-{chunk_size}")
        end_time = time.perf_counter()

        processing_time = end_time - start_time

        print(f"\nChunk Size {chunk_size} (overlap {overlap}) Results:")
        print(f"  Processing time: {processing_time:.3f}s")
        print(f"  Chunks created: {result.chunks_created}")
        chunk_process_time = processing_time / result.chunks_created * 1000
        print(f"  Avg chunk processing time: {chunk_process_time:.1f}ms")
        chars_per_chunk = len(doc_content) / result.chunks_created
        print(f"  Characters per chunk: {chars_per_chunk:.0f}")

        assert result.success, f"Processing failed: {result.error}"
        assert processing_time < 10.0, f"Processing too slow: {processing_time:.3f}s"

        return {
            "chunk_size": chunk_size,
            "overlap": overlap,
            "processing_time": processing_time,
            "chunks_created": result.chunks_created,
            "chunks_per_second": result.chunks_created / processing_time,
        }

    def test_memory_usage_benchmark(
        self, temp_dir: Any, benchmark_config: ChunkingConfig
    ) -> None:
        """Monitor memory usage during processing."""
        import os

        process = psutil.Process(os.getpid())

        processor = DocumentProcessor(benchmark_config)

        # Create large document
        large_content = self._generate_document_content(
            sections=200, paragraphs_per_section=10
        )
        large_file = temp_dir / "memory_test.md"
        large_file.write_text(large_content)

        # Get baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Monitor memory during processing
        memory_samples = []
        start_time = time.perf_counter()

        def memory_monitor() -> None:
            while True:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory - baseline_memory)
                time.sleep(0.05)  # Sample every 50ms

        import threading

        monitor_thread = threading.Thread(target=memory_monitor, daemon=True)
        monitor_thread.start()

        # Process document
        result = processor.process_document(large_file, "memory-test")

        processing_time = time.perf_counter() - start_time

        # Let memory stabilize
        time.sleep(1)

        if memory_samples:
            max_memory_increase = max(memory_samples)
            avg_memory_increase = statistics.mean(memory_samples)

            print("\nMemory Usage Benchmark Results:")
            print(f"  Baseline memory: {baseline_memory:.1f} MB")
            print(f"  Max memory increase: {max_memory_increase:.1f} MB")
            print(f"  Average memory increase: {avg_memory_increase:.1f} MB")
            memory_per_chunk = max_memory_increase / result.chunks_created
            print(f"  Memory per chunk: {memory_per_chunk:.2f} MB")
            print(f"  Document size: {len(large_content) / 1024:.1f} KB")
            print(f"  Processing time: {processing_time:.3f}s")

            # Memory usage assertions
            assert max_memory_increase < 500, (
                f"Memory usage too high: {max_memory_increase:.1f}MB"
            )
            assert result.success, f"Processing failed: {result.error}"

    def test_large_document_scalability(
        self, temp_dir: Any, benchmark_config: ChunkingConfig
    ) -> None:
        """Test scalability with increasingly large documents."""
        processor = DocumentProcessor(benchmark_config)

        document_sizes = [10, 50, 100, 200]  # Number of sections
        results: list[dict[str, int | float]] = []

        for size in document_sizes:
            doc_content = self._generate_document_content(
                sections=size, paragraphs_per_section=5
            )
            doc_path = temp_dir / f"scalability_test_{size}.md"
            doc_path.write_text(doc_content)

            start_time = time.perf_counter()
            result = processor.process_document(doc_path, f"scalability-{size}")
            end_time = time.perf_counter()

            processing_time = end_time - start_time

            results.append(
                {
                    "sections": size,
                    "document_size": len(doc_content),
                    "processing_time": processing_time,
                    "chunks_created": result.chunks_created,
                    "throughput": len(doc_content) / processing_time,
                }
            )

            assert result.success, f"Processing failed for size {size}: {result.error}"

        print("\nScalability Benchmark Results:")
        for benchmark_result in results:
            print(f"  Sections: {benchmark_result['sections']}")
            print(f"    Document size: {benchmark_result['document_size']} chars")
            print(f"    Processing time: {benchmark_result['processing_time']:.3f}s")
            print(f"    Chunks created: {benchmark_result['chunks_created']}")
            print(f"    Throughput: {benchmark_result['throughput']:.0f} chars/second")

        # Check that processing time scales reasonably
        times = [r["processing_time"] for r in results]
        sizes = [r["document_size"] for r in results]

        # Processing time should scale sublinearly with document size
        time_ratio = times[-1] / times[0]
        size_ratio = sizes[-1] / sizes[0]

        scaling_msg = (
            "Processing time scaling poorly: "
            f"{time_ratio:.2f}x time for {size_ratio:.2f}x size"
        )
        assert time_ratio < size_ratio * 1.5, scaling_msg

    def test_concurrent_processing_scalability(
        self, temp_dir: Any, benchmark_config: ChunkingConfig
    ) -> None:
        """Test scalability of concurrent processing."""
        processor = DocumentProcessor(benchmark_config)

        # Create multiple documents
        documents = []
        for i in range(20):
            doc_content = self._generate_document_content(
                sections=15, paragraphs_per_section=4
            )
            doc_path = temp_dir / f"concurrent_test_{i:02d}.md"
            doc_path.write_text(doc_content)
            documents.append(doc_path)

        # Test with different worker counts
        worker_counts = [1, 2, 4, 8]
        scalability_results: list[dict[str, int | float]] = []

        for workers in worker_counts:
            start_time = time.perf_counter()
            result = processor.process_batch(
                documents, f"concurrent-{workers}", max_workers=workers
            )
            end_time = time.perf_counter()

            processing_time = end_time - start_time

            scalability_results.append(
                {
                    "workers": workers,
                    "processing_time": processing_time,
                    "successful_files": result.successful_files,
                    "efficiency": result.successful_files / processing_time / workers,
                }
            )

            assert result.successful_files == len(documents), (
                f"Not all files processed with {workers} workers"
            )

        print("\nConcurrent Processing Scalability Results:")
        for scalability_result in scalability_results:
            print(f"  Workers: {scalability_result['workers']}")
            print(f"    Processing time: {scalability_result['processing_time']:.3f}s")
            print(
                f"    Efficiency: {scalability_result['efficiency']:.3f} "
                f"files/second/worker"
            )

        # Check efficiency doesn't degrade too much with more workers
        single_worker_efficiency = scalability_results[0]["efficiency"]
        max_worker_efficiency = scalability_results[-1]["efficiency"]

        efficiency_ratio = max_worker_efficiency / single_worker_efficiency
        assert efficiency_ratio > 0.5, (
            f"Efficiency degraded too much: {efficiency_ratio:.2f}"
        )

    def test_chunking_method_performance_comparison(self, temp_dir: Any) -> None:
        """Compare performance of different chunking methods."""
        methods = ["structure", "fixed"]
        results: dict[str, dict[str, float]] = {}

        # Create test document
        doc_content = self._generate_document_content(
            sections=30, paragraphs_per_section=6
        )
        doc_path = temp_dir / "method_comparison.md"
        doc_path.write_text(doc_content)

        for method in methods:
            config = ChunkingConfig(chunk_size=1000, overlap=200, method=method)
            processor = DocumentProcessor(config)

            # Run multiple times for statistical accuracy
            times = []
            chunks_list = []

            for run in range(3):
                start_time = time.perf_counter()
                result = processor.process_document(doc_path, f"method-{method}-{run}")
                end_time = time.perf_counter()

                assert result.success, (
                    f"Processing failed for method {method}: {result.error}"
                )

                times.append(end_time - start_time)
                chunks_list.append(result.chunks_created)

            results[method] = {
                "avg_time": statistics.mean(times),
                "std_time": statistics.stdev(times) if len(times) > 1 else 0,
                "avg_chunks": statistics.mean(chunks_list),
                "throughput": statistics.mean(
                    [c / t for c, t in zip(chunks_list, times, strict=False)]
                ),
            }

        print("\nChunking Method Performance Comparison:")
        for method, method_result in results.items():
            print(f"  {method.title()} Method:")
            avg_time = method_result["avg_time"]
            std_time = method_result["std_time"]
            print(f"    Average time: {avg_time:.3f}s ± {std_time:.3f}s")
            print(f"    Average chunks: {method_result['avg_chunks']:.1f}")
            print(f"    Throughput: {method_result['throughput']:.1f} chunks/second")

        # Both methods should complete in reasonable time
        for method, method_result in results.items():
            assert method_result["avg_time"] < 10.0, (
                f"{method} method too slow: {method_result['avg_time']:.3f}s"
            )

    def _generate_document_content(
        self, sections: int, paragraphs_per_section: int
    ) -> str:
        """Generate test document content of specified size."""
        content = ["# Performance Test Document\n\n"]
        content.append(
            "This document is generated for performance testing purposes.\n\n"
        )

        for section in range(sections):
            content.append(f"## Section {section + 1}\n\n")

            for paragraph in range(paragraphs_per_section):
                content.append(
                    f"This is paragraph {paragraph + 1} of section {section + 1}. "
                )
                content.append(
                    "It contains substantial content to test processing performance "
                )
                content.append(
                    "and chunking behavior. The content is designed to be realistic "
                )
                content.append("and representative of actual documentation.\n\n")

            # Add code blocks occasionally
            if section % 5 == 0:
                content.append("```python\n")
                content.append(f"def section_{section}_function():\n")
                content.append(f'    """Function for section {section}."""\n')
                content.append(f"    result = process_section_{section}()\n")
                content.append("    return result\n")
                content.append("```\n\n")

        return "".join(content)


@pytest.mark.performance
class TestMemoryEfficiency:
    """Test memory efficiency and resource usage."""

    def test_memory_leak_detection(
        self, temp_dir: Any, benchmark_config: ChunkingConfig
    ) -> None:
        """Test for memory leaks during repeated processing."""
        import gc
        import os

        process = psutil.Process(os.getpid())
        processor = DocumentProcessor(benchmark_config)

        # Create test document
        doc_content = "# Test Doc\n\n" + ("Test paragraph. " * 100 + "\n\n") * 50
        doc_path = temp_dir / "memory_leak_test.md"
        doc_path.write_text(doc_content)

        # Get baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024

        memory_readings = []

        # Process the same document many times
        for i in range(20):
            result = processor.process_document(doc_path, f"leak-test-{i}")
            assert result.success, f"Processing failed on iteration {i}"

            # Force garbage collection and measure memory
            gc.collect()
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = current_memory - baseline_memory
            memory_readings.append(memory_increase)

        print("\nMemory Leak Detection Results:")
        print(f"  Baseline memory: {baseline_memory:.1f} MB")
        print(f"  Memory after 20 iterations: {memory_readings[-1]:.1f} MB increase")
        print(f"  Average memory increase: {statistics.mean(memory_readings):.1f} MB")
        print(f"  Max memory increase: {max(memory_readings):.1f} MB")

        # Check for memory leaks
        # Memory should not continuously increase
        first_half_avg = statistics.mean(memory_readings[:10])
        second_half_avg = statistics.mean(memory_readings[10:])

        memory_growth = second_half_avg - first_half_avg
        assert memory_growth < 10, (
            f"Potential memory leak detected: {memory_growth:.1f} MB growth"
        )

    def test_large_file_memory_efficiency(
        self, temp_dir: Any, benchmark_config: ChunkingConfig
    ) -> None:
        """Test memory efficiency with large files."""
        import os

        process = psutil.Process(os.getpid())
        processor = DocumentProcessor(benchmark_config)

        # Create very large document (several MB)
        large_content = []
        for i in range(1000):  # 1000 sections
            large_content.append(f"## Section {i}\n")
            large_content.append(("Large content paragraph. " * 50 + "\n") * 10)

        large_doc = "# Very Large Document\n\n" + "".join(large_content)
        large_file = temp_dir / "very_large_test.md"
        large_file.write_text(large_doc)

        file_size = len(large_doc) / (1024 * 1024)  # MB

        # Monitor memory during processing
        baseline_memory = process.memory_info().rss / 1024 / 1024

        result = processor.process_document(large_file, "large-file-memory-test")

        peak_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = peak_memory - baseline_memory

        print("\nLarge File Memory Efficiency Results:")
        print(f"  File size: {file_size:.1f} MB")
        print(f"  Memory increase: {memory_increase:.1f} MB")
        print(f"  Memory ratio: {memory_increase / file_size:.2f}x file size")
        print(f"  Chunks created: {result.chunks_created}")

        assert result.success, f"Large file processing failed: {result.error}"

        # Memory usage should be reasonable relative to file size
        memory_msg = (
            "Memory usage too high: "
            f"{memory_increase:.1f} MB for {file_size:.1f} MB file"
        )
        assert memory_increase < file_size * 3, memory_msg
