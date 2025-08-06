"""Example test file demonstrating the use of test utilities.

This file shows how to use the test utilities and helper functions
to write cleaner, more maintainable tests.
"""

from pathlib import Path

from tests.utils.helpers import (
    AssertionHelper,
    DataGenerator,
    FileHelper,
    MockHelper,
    TimingHelper,
)


class TestUtilitiesExample:
    """Example tests demonstrating utility usage."""

    def test_file_helper_usage(self, temp_dir: Path) -> None:
        """Test using FileHelper to create test files."""
        # Create a simple markdown file
        simple_file = FileHelper.create_markdown_file(
            temp_dir, "test.md", "# Test\n\nContent here."
        )

        assert simple_file.exists()
        assert simple_file.read_text().startswith("# Test")

        # Create a file with Unicode content
        unicode_file = FileHelper.create_unicode_markdown_file(temp_dir, "unicode.md")
        assert unicode_file.exists()
        content = unicode_file.read_text(encoding="utf-8")
        assert "文档标题" in content

        # Create an empty file
        empty_file = FileHelper.create_empty_file(temp_dir, "empty.md")
        assert empty_file.exists()
        assert empty_file.stat().st_size == 0

    def test_mock_helper_usage(self) -> None:
        """Test using MockHelper to create mock objects."""
        # Create mock configurations
        chromadb_config = MockHelper.create_mock_chromadb_config(
            host="test-host", port=9000
        )
        assert chromadb_config.host == "test-host"
        assert chromadb_config.port == 9000

        chunking_config = MockHelper.create_mock_chunking_config(
            chunk_size=500, overlap=100
        )
        assert chunking_config.chunk_size == 500
        assert chunking_config.overlap == 100

        # Create mock processing result
        result = MockHelper.create_mock_processing_result(
            success=True, chunks_created=5
        )
        assert result.success is True
        assert result.chunks_created == 5

    def test_assertion_helper_usage(self) -> None:
        """Test using AssertionHelper for common assertions."""
        # Create a successful processing result
        success_result = MockHelper.create_mock_processing_result(
            success=True, chunks_created=3, processing_time=1.5
        )

        # Test successful assertion
        AssertionHelper.assert_processing_result_success(
            success_result, expected_chunks=3, min_processing_time=1.0
        )

        # Create a failed processing result
        failure_result = MockHelper.create_mock_processing_result(
            success=False, chunks_created=0, error="Test error"
        )

        # Test failure assertion
        AssertionHelper.assert_processing_result_failure(
            failure_result, expected_error_keywords=["test", "error"]
        )

    def test_data_generator_usage(self) -> None:
        """Test using DataGenerator for test data."""
        # Generate markdown templates
        templates = DataGenerator.generate_markdown_content_templates()
        assert "simple" in templates
        assert "complex" in templates
        assert "technical" in templates
        assert "blog" in templates

        # Check template content
        assert templates["simple"].startswith("# Simple Document")
        assert "```python" in templates["technical"]

        # Generate test chunks
        chunks = DataGenerator.generate_test_chunks(count=5)
        assert len(chunks) == 5

        # Validate chunks using assertion helper
        AssertionHelper.assert_chunks_valid(chunks)

    def test_timing_helper_usage(self) -> None:
        """Test using TimingHelper for performance testing."""

        def slow_function(delay: float = 0.1) -> str:
            """A function that takes some time to execute."""
            import time

            time.sleep(delay)
            return "completed"

        # Time a function execution
        result, execution_time = TimingHelper.time_function(slow_function, 0.05)
        assert result == "completed"
        assert execution_time >= 0.05

        # Assert execution time is within bounds
        fast_result = TimingHelper.assert_execution_time(
            slow_function, max_time=0.2, delay=0.05
        )
        assert fast_result == "completed"

    def test_file_size_assertion(self, temp_dir: Path) -> None:
        """Test file size assertion helper."""
        # Create a file with specific size
        test_file = FileHelper.create_file_at_size(temp_dir, "sized.md", 500)

        # Assert file size is within expected range
        AssertionHelper.assert_file_size_within_range(test_file, 450, 550)

        # This should pass since file is created at exactly 500 bytes
        actual_size = test_file.stat().st_size
        assert actual_size == 500

    def test_performance_file_generation(self, temp_dir: Path) -> None:
        """Test generating multiple files for performance testing."""
        files = DataGenerator.generate_performance_test_files(
            temp_dir, count=3, size_per_file=1000
        )

        assert len(files) == 3
        for file_path in files:
            assert file_path.exists()
            # Files should be reasonably sized for testing
            file_size = file_path.stat().st_size
            assert file_size > 500  # Should have substantial content

    def test_combined_utilities_example(self, temp_dir: Path) -> None:
        """Test combining multiple utilities for a complete test scenario."""
        # 1. Generate test data
        templates = DataGenerator.generate_markdown_content_templates()

        # 2. Create test files using templates
        test_files = []
        for name, content in templates.items():
            file_path = FileHelper.create_markdown_file(temp_dir, f"{name}.md", content)
            test_files.append(file_path)

        # 3. Verify files were created
        assert len(test_files) == len(templates)
        for file_path in test_files:
            assert file_path.exists()

        # 4. Create mock processing results
        results = []
        for i, file_path in enumerate(test_files):
            result = MockHelper.create_mock_processing_result(
                file_path=file_path,
                success=True,
                chunks_created=i + 2,
                processing_time=0.5 + i * 0.1,
            )
            results.append(result)

        # 5. Validate all results using assertion helpers
        for result in results:
            AssertionHelper.assert_processing_result_success(result)

        # 6. Create and validate test chunks
        chunks = DataGenerator.generate_test_chunks(count=10)
        AssertionHelper.assert_chunks_valid(chunks)

        # All utilities working together successfully!
        assert len(results) == len(test_files)
        assert all(r.success for r in results)


class TestUtilitiesIntegration:
    """Integration tests for utilities with existing fixtures."""

    def test_utilities_with_existing_fixtures(
        self, temp_dir: Path, chunking_config, sample_chunks
    ) -> None:
        """Test that utilities work well with existing fixtures."""
        # Use existing fixtures alongside new utilities
        assert chunking_config.chunk_size == 300

        # Create additional test data using utilities
        large_file = FileHelper.create_large_markdown_file(
            temp_dir, "large_test.md", num_sections=10
        )

        # Validate existing fixture data using assertion helpers
        AssertionHelper.assert_chunks_valid(sample_chunks)

        # Mix utilities with existing patterns
        assert large_file.exists()
        assert len(sample_chunks) >= 1

    def test_backward_compatibility(
        self, sample_markdown_file: Path, mock_processing_result
    ) -> None:
        """Test that new utilities don't break existing test patterns."""
        # Existing fixture usage still works
        assert sample_markdown_file.exists()
        assert mock_processing_result.success is True

        # Can enhance with new assertion helpers
        AssertionHelper.assert_processing_result_success(mock_processing_result)

        # Utilities complement existing fixtures
        templates = DataGenerator.generate_markdown_content_templates()
        assert len(templates) > 0
