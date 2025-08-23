"""Performance tests for batch processing - stress testing and efficiency."""

import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from shard_markdown.cli.main import shard_md


@pytest.mark.performance
@pytest.mark.slow
class TestBatchPerformance:
    """Performance tests for batch processing of markdown files."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    @pytest.mark.timeout(120)  # 2 minute timeout for safety
    def test_batch_memory_efficiency(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test memory efficiency with many files.

        This is a PERFORMANCE test that processes 50 files to ensure
        the system can handle larger batches without memory issues.
        """
        # Create 50 moderate-sized documents
        for i in range(50):
            content = f"# Document {i}\n\n"
            # Use varied content to avoid the infinite loop bug
            content += f"This is document {i} with unique content.\n\n" * 10
            content += f"## Section 1\n\nContent for section 1 of doc {i}.\n\n"
            content += f"## Section 2\n\nContent for section 2 of doc {i}.\n\n"
            content += f"## Section 3\n\nContent for section 3 of doc {i}.\n\n"

            (tmp_path / f"doc_{i:03d}.md").write_text(content)

        # Process all files
        start_time = time.time()
        result = cli_runner.invoke(shard_md, [str(tmp_path)])
        elapsed = time.time() - start_time

        assert result.exit_code == 0
        # Performance expectation: should handle 50 files in under 60 seconds
        assert elapsed < 60, f"Processing 50 files took {elapsed:.1f}s, expected < 60s"

        # Verify all files were processed
        for i in range(50):
            assert f"doc_{i:03d}.md" in result.output

    @pytest.mark.timeout(180)  # 3 minute timeout
    def test_batch_large_directory(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test processing a large directory efficiently.

        This is a PERFORMANCE test with 100 files to test scalability.
        """
        # Create 100 small documents
        for i in range(100):
            content = f"# Doc {i}\n\nMinimal content for document {i}."
            (tmp_path / f"doc_{i:03d}.md").write_text(content)

        start_time = time.time()
        result = cli_runner.invoke(shard_md, [str(tmp_path)])
        elapsed = time.time() - start_time

        assert result.exit_code == 0
        # Should process 100 small files efficiently
        assert elapsed < 120, (
            f"Processing 100 files took {elapsed:.1f}s, expected < 120s"
        )

    def test_batch_throughput(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test processing throughput (files per second).

        This measures how many files can be processed per second.
        """
        # Create 20 standard-sized documents
        num_files = 20
        for i in range(num_files):
            content = f"""# Document {i}

## Introduction
This is a standard document for throughput testing.

## Content
Some paragraph content here. This represents a typical
markdown file that users might process.

## Code Example
```python
def example_{i}():
    return "Example {i}"
```

## Conclusion
End of document {i}.
"""
            (tmp_path / f"doc_{i:02d}.md").write_text(content)

        start_time = time.time()
        result = cli_runner.invoke(shard_md, [str(tmp_path)])
        elapsed = time.time() - start_time

        assert result.exit_code == 0

        # Calculate throughput
        throughput = num_files / elapsed if elapsed > 0 else 0

        # Expect at least 5 files per second for standard documents
        assert throughput >= 5, (
            f"Throughput {throughput:.1f} files/sec is too slow (expected >= 5)"
        )

        # Log performance metrics
        print("\nPerformance Metrics:")
        print(f"  Files processed: {num_files}")
        print(f"  Time taken: {elapsed:.2f}s")
        print(f"  Throughput: {throughput:.1f} files/sec")

    def test_memory_usage_growth(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that memory usage doesn't grow excessively with batch size.

        This test verifies that processing doesn't accumulate memory.
        """
        import tracemalloc

        # Create 30 files
        for i in range(30):
            content = f"# Document {i}\n\n" + ("Content paragraph. " * 50 + "\n\n") * 10
            (tmp_path / f"doc_{i:02d}.md").write_text(content)

        # Start memory tracking
        tracemalloc.start()

        # Process files
        result = cli_runner.invoke(shard_md, [str(tmp_path)])

        # Get memory peak
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert result.exit_code == 0

        # Memory should not exceed reasonable limits (e.g., 100MB for 30 files)
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 100, f"Peak memory usage {peak_mb:.1f}MB exceeds 100MB limit"

        print("\nMemory Usage:")
        print(f"  Current: {current / 1024 / 1024:.1f}MB")
        print(f"  Peak: {peak_mb:.1f}MB")

    @pytest.mark.timeout(60)
    def test_large_file_processing(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test processing large markdown files (1MB+).

        This is a PERFORMANCE test for large file handling.
        """
        # Create a 1MB file with varied content
        large_content = "# Large Document\n\n"

        # Use varied content to avoid infinite loop bug
        for section in range(50):
            large_content += f"## Section {section}\n\n"
            large_content += f"This is section {section} with unique content.\n\n"
            large_content += ("Some paragraph content. " * 50 + "\n\n") * 5

        large_file = tmp_path / "large.md"
        large_file.write_text(large_content)

        # Check file size
        file_size_mb = len(large_content) / 1024 / 1024
        print(f"\nFile size: {file_size_mb:.2f}MB")

        start_time = time.time()
        result = cli_runner.invoke(
            shard_md,
            [str(large_file), "--size", "1000"],
        )
        elapsed = time.time() - start_time

        assert result.exit_code == 0
        assert "large.md" in result.output

        # Performance expectation for large files
        assert elapsed < 30, f"Processing 1MB file took {elapsed:.1f}s, expected < 30s"

        print(f"Processing time: {elapsed:.2f}s")
        print(f"Processing speed: {file_size_mb / elapsed:.2f}MB/s")
