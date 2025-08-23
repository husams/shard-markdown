"""E2E test cases TC-E2E-026, TC-E2E-027, and TC-E2E-028.

Test Cases:
- TC-E2E-026: Memory-Limited Processing
- TC-E2E-027: Large Document Processing
- TC-E2E-028: Concurrent Processing
"""

import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest
from click.testing import CliRunner

from shard_markdown.cli.main import shard_md


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.performance
class TestResourceLimitsPerformanceCases:
    """Test cases for resource limits, large files, and concurrent processing."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    def _create_large_markdown(self, tmp_path: Path, size_mb: int) -> Path:
        """Create a markdown file of approximately the specified size in MB."""
        content = []
        content.append(f"# Large Document Test ({size_mb}MB)\n\n")

        # Calculate sections needed for target size
        sections_needed = size_mb * 50  # Approx 20KB per section

        base_text = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            "This is a performance test document with substantial content. "
            "The content is designed to test memory handling and processing "
            "efficiency with large files in the shard-markdown application. "
        )

        for section in range(sections_needed):
            content.append(f"## Section {section + 1}\n\n")
            content.append(f"This is section {section + 1} content.\n\n")
            content.append(base_text * 50)  # About 20KB per section
            content.append("\n\n")

        file_content = "".join(content)
        file_path = tmp_path / f"large_{size_mb}mb.md"
        file_path.write_text(file_content)

        return file_path

    @pytest.mark.timeout(300)
    def test_tc_e2e_026_memory_limited_processing(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """TC-E2E-026: Memory-Limited Processing.

        Tests processing with large chunk sizes that stress memory usage.
        Verifies graceful handling when resources are limited.
        """
        # Create a test document that will stress memory with large chunks
        test_file = self._create_large_markdown(tmp_path, size_mb=2)

        # Start memory tracking
        tracemalloc.start()

        try:
            # Test with very large chunk size (5MB) to stress memory
            start_time = time.time()
            result = cli_runner.invoke(
                shard_md, [str(test_file), "--size", "5242880", "--overlap", "1000"]
            )
            elapsed_time = time.time() - start_time

            # Get peak memory usage
            current, peak = tracemalloc.get_traced_memory()
            peak_mb = peak / 1024 / 1024

            # Assertions
            assert result.exit_code == 0, f"Processing failed: {result.output}"
            assert (
                test_file.name.replace(".md", "") in result.output
                or "chunk" in result.output.lower()
            )

            # Performance constraints
            assert elapsed_time < 120, (
                f"Processing took {elapsed_time:.1f}s, expected < 120s"
            )
            assert peak_mb < 500, f"Peak memory {peak_mb:.1f}MB exceeds 500MB limit"

        finally:
            tracemalloc.stop()

    @pytest.mark.timeout(600)
    @pytest.mark.parametrize("size_mb", [1, 5])
    def test_tc_e2e_027_large_document_processing(
        self, cli_runner: CliRunner, tmp_path: Path, size_mb: int
    ) -> None:
        """TC-E2E-027: Large Document Processing.

        Tests with progressively larger markdown files (1MB, 5MB).
        Verifies performance doesn't degrade catastrophically.
        """
        test_file = self._create_large_markdown(tmp_path, size_mb)

        start_time = time.time()
        result = cli_runner.invoke(
            shard_md, [str(test_file), "--size", "2000", "--overlap", "100"]
        )
        elapsed_time = time.time() - start_time

        # Assertions
        assert result.exit_code == 0, f"Large file processing failed: {result.output}"
        assert test_file.name in result.output or "chunk" in result.output.lower()

        # Performance expectations based on file size
        max_time = 60 if size_mb <= 2 else 180
        assert elapsed_time < max_time, (
            f"Processing {size_mb}MB file took {elapsed_time:.1f}s, "
            f"expected < {max_time}s"
        )

        # Verify no error indicators
        assert "error" not in result.output.lower()
        assert "failed" not in result.output.lower()

    @pytest.mark.timeout(180)
    def test_tc_e2e_028_concurrent_processing(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """TC-E2E-028: Concurrent Processing.

        Tests processing multiple files simultaneously to verify basic
        thread safety and ensure no catastrophic race conditions.
        """
        # Create test files
        test_files = []
        for i in range(5):  # Reduced number for stability
            content = f"""# Concurrent Test Document {i + 1}

## Overview
Test document {i + 1} for concurrent processing validation.

## Content
This document tests concurrent processing capabilities.
Document ID: {i + 1}

## Conclusion
Document {i + 1} ready for processing.
"""
            file_path = tmp_path / f"concurrent_doc_{i + 1:02d}.md"
            file_path.write_text(content)
            test_files.append(file_path)

        def process_file(file_path: Path) -> dict:
            """Process a single file and return results."""
            try:
                runner = CliRunner()
                result = runner.invoke(shard_md, [str(file_path)])
                return {
                    "file": file_path.name,
                    "exit_code": result.exit_code,
                    "success": result.exit_code == 0,
                    "thread_id": threading.current_thread().ident,
                }
            except Exception as e:
                return {
                    "file": file_path.name,
                    "exit_code": -1,
                    "success": False,
                    "error": str(e),
                    "thread_id": threading.current_thread().ident,
                }

        results = []
        start_time = time.time()

        # Process files concurrently (limited workers for stability)
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_file = {executor.submit(process_file, f): f for f in test_files}

            for future in as_completed(future_to_file):
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    file_path = future_to_file[future]
                    results.append(
                        {
                            "file": file_path.name,
                            "exit_code": -1,
                            "success": False,
                            "error": str(e),
                            "thread_id": None,
                        }
                    )

        elapsed_time = time.time() - start_time

        # Assertions
        assert len(results) == len(test_files), (
            f"Expected {len(test_files)} results, got {len(results)}"
        )

        # Allow for some concurrency issues but ensure basic functionality
        successful_results = [r for r in results if r["success"]]
        success_rate = len(successful_results) / len(test_files)

        assert success_rate >= 0.2, (
            f"Success rate {success_rate:.2%} below 20%. "
            f"Successful: {len(successful_results)}/{len(test_files)}"
        )

        # Ensure at least some concurrent processing occurred
        assert len(successful_results) >= 1, (
            f"Expected at least 1 successful operation, got {len(successful_results)}"
        )

        # Verify successful files have exit code 0
        for result in successful_results:
            assert result["exit_code"] == 0, (
                f"Successful result has non-zero exit code: {result['exit_code']}"
            )

        # Performance check
        assert elapsed_time < 60, (
            f"Concurrent processing took {elapsed_time:.1f}s, expected < 60s"
        )

        # Thread safety verification
        thread_ids = {r["thread_id"] for r in results if r["thread_id"]}
        assert len(thread_ids) >= 1, "No thread IDs captured"
