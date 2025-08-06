"""Example showing how to refactor existing tests using the new utilities.

This file demonstrates how existing test code can be simplified and made
more maintainable using the test utilities.
"""

from pathlib import Path

from shard_markdown.config.settings import ProcessingConfig
from shard_markdown.core.models import ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor
from tests.utils.helpers import AssertionHelper, FileHelper, MockHelper


class TestRefactoredFileSizeEdgeCases:
    """Refactored version of file size edge case tests using utilities."""

    def test_file_at_exact_size_limit_refactored(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test file exactly at the configured size limit (refactored version)."""
        limit = 500  # 500 bytes

        # Use MockHelper for configuration creation
        config = MockHelper.create_mock_processing_config(max_file_size=limit)
        processor = DocumentProcessor(chunking_config, config)

        # Use FileHelper to create file at exact size
        exact_file = FileHelper.create_file_at_size(temp_dir, "exact_limit.md", limit)

        # Use AssertionHelper to verify file size
        AssertionHelper.assert_file_size_within_range(exact_file, limit, limit)

        result = processor.process_document(exact_file, "exact-limit-test")

        # Use AssertionHelper for result validation
        AssertionHelper.assert_processing_result_success(result)

    def test_file_just_under_limit_refactored(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test file 1 byte under the size limit (refactored version)."""
        limit = 500
        target_size = limit - 1

        # Use utilities for cleaner setup
        config = MockHelper.create_mock_processing_config(max_file_size=limit)
        processor = DocumentProcessor(chunking_config, config)

        # Create file at specific size using utility
        under_file = FileHelper.create_file_at_size(
            temp_dir, "under_limit.md", target_size
        )

        # Verify size with assertion helper
        AssertionHelper.assert_file_size_within_range(
            under_file, target_size, target_size
        )

        result = processor.process_document(under_file, "under-limit-test")

        # Clean assertion using helper
        AssertionHelper.assert_processing_result_success(result)

    def test_file_just_over_limit_refactored(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test file 1 byte over the size limit (refactored version)."""
        limit = 500
        over_size = limit + 1

        config = MockHelper.create_mock_processing_config(max_file_size=limit)
        processor = DocumentProcessor(chunking_config, config)

        # Create oversized file using utility
        over_file = FileHelper.create_file_at_size(temp_dir, "over_limit.md", over_size)

        # Verify file is actually over limit
        file_size = over_file.stat().st_size
        assert file_size > limit

        result = processor.process_document(over_file, "over-limit-test")

        # Use assertion helper for failure validation
        AssertionHelper.assert_processing_result_failure(
            result, expected_error_keywords=["too large"]
        )

    def test_empty_files_refactored(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test handling of empty files (refactored version)."""
        processor = DocumentProcessor(chunking_config)

        # Use utility to create empty file
        empty_file = FileHelper.create_empty_file(temp_dir, "empty.md")

        # Verify file is empty
        assert empty_file.stat().st_size == 0

        result = processor.process_document(empty_file, "empty-test")

        # Use assertion helper for expected failure
        AssertionHelper.assert_processing_result_failure(
            result, expected_error_keywords=["empty"]
        )


class TestRefactoredComplexScenarios:
    """More complex refactoring examples."""

    def test_unicode_processing_refactored(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test Unicode content processing (refactored version)."""
        processor = DocumentProcessor(chunking_config)

        # Use utility to create Unicode file
        unicode_file = FileHelper.create_unicode_markdown_file(temp_dir, "unicode.md")

        result = processor.process_document(unicode_file, "unicode-test")

        # Clean success assertion
        AssertionHelper.assert_processing_result_success(result)

    def test_large_document_processing_refactored(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test processing of large documents (refactored version)."""
        processor = DocumentProcessor(chunking_config)

        # Use utility to create large file
        large_file = FileHelper.create_large_markdown_file(
            temp_dir, "large.md", num_sections=20, content_multiplier=5
        )

        result = processor.process_document(large_file, "large-test")

        # Verify success and substantial chunk creation
        AssertionHelper.assert_processing_result_success(result)
        assert result.chunks_created >= 5  # Should create multiple chunks

    def test_mixed_file_types_refactored(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test processing multiple file types (refactored version)."""
        processor = DocumentProcessor(chunking_config)

        # Create different types of test files using utilities
        files_and_expectations = [
            (
                FileHelper.create_markdown_file(
                    temp_dir, "simple.md", "# Simple\n\nBasic content."
                ),
                True,  # Should succeed
                ["simple"],
            ),
            (
                FileHelper.create_empty_file(temp_dir, "empty.md"),
                False,  # Should fail
                ["empty"],
            ),
            (
                FileHelper.create_unicode_markdown_file(temp_dir, "unicode.md"),
                True,  # Should succeed
                [],
            ),
            (
                FileHelper.create_whitespace_file(temp_dir, "whitespace.md"),
                False,  # Should fail (effectively empty)
                ["empty", "no content"],
            ),
        ]

        results = []
        for file_path, should_succeed, error_keywords in files_and_expectations:
            result = processor.process_document(file_path, f"test-{file_path.stem}")
            results.append((result, should_succeed, error_keywords))

        # Validate results using assertion helpers
        for result, should_succeed, error_keywords in results:
            if should_succeed:
                AssertionHelper.assert_processing_result_success(result)
            else:
                AssertionHelper.assert_processing_result_failure(
                    result, expected_error_keywords=error_keywords
                )


class TestComparisonOldVsNew:
    """Direct comparison showing before/after refactoring."""

    def test_old_style_manual_setup(self, temp_dir: Path) -> None:
        """Example of old-style test with manual setup (before refactoring)."""
        # Manual configuration creation
        config = ProcessingConfig(
            batch_size=1,
            max_workers=1,
            max_file_size=1_000_000,
            recursive=False,
            pattern="*.md",
            include_frontmatter=True,
            include_path_metadata=True,
            skip_empty_files=True,
            strict_validation=False,
            encoding="utf-8",
            encoding_fallback="latin-1",
            enable_encoding_detection=True,
        )

        # Manual file creation
        content = """# Test Document

This is a test document with some content.

## Section 1

Here's some content in the first section.

## Section 2

More content in the second section.
"""
        test_file = temp_dir / "manual_test.md"
        test_file.write_text(content)

        # Manual processor setup
        chunking_config = ChunkingConfig(
            chunk_size=300,
            overlap=50,
            method="structure",
            respect_boundaries=True,
        )
        processor = DocumentProcessor(chunking_config, config)

        result = processor.process_document(test_file, "manual-test")

        # Manual assertions
        assert result.success is True
        assert result.error is None
        assert result.chunks_created > 0
        assert result.processing_time >= 0

    def test_new_style_with_utilities(self, temp_dir: Path, chunking_config) -> None:
        """Example of new-style test using utilities (after refactoring)."""
        # Clean configuration creation using utility
        config = MockHelper.create_mock_processing_config()

        # Clean file creation using utility
        test_file = FileHelper.create_markdown_file(
            temp_dir,
            "utility_test.md",
            """# Test Document

This is a test document with some content.

## Section 1

Here's some content in the first section.

## Section 2

More content in the second section.
""",
        )

        # Use existing fixture for chunking config
        processor = DocumentProcessor(chunking_config, config)

        result = processor.process_document(test_file, "utility-test")

        # Clean assertion using helper
        AssertionHelper.assert_processing_result_success(result)


# Benefits of the refactoring:
# 1. Less code duplication
# 2. More readable and maintainable tests
# 3. Consistent patterns across test files
# 4. Easier to modify test setup and assertions
# 5. Better error messages from assertion helpers
# 6. Reusable components for similar test scenarios
