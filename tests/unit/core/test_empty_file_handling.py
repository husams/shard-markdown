"""Tests for empty file and whitespace-only file handling."""

from pathlib import Path

import pytest

from shard_markdown.config.settings import ProcessingConfig
from shard_markdown.core.models import ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor
from shard_markdown.core.validation import ContentValidator, ValidationConfig


class TestEmptyFileHandling:
    """Test suite for empty file handling."""

    @pytest.fixture
    def chunking_config(self) -> ChunkingConfig:
        """Create basic chunking configuration."""
        return ChunkingConfig(
            chunk_size=500,
            overlap=50,
            method="structure",
            respect_boundaries=True,
        )

    @pytest.fixture
    def validator(self) -> ContentValidator:
        """Create content validator for testing."""
        return ContentValidator(ValidationConfig())

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create processor for testing."""
        return DocumentProcessor(chunking_config)

    @pytest.fixture
    def strict_processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create strict processor for testing."""
        config = ProcessingConfig(strict_validation=True)
        return DocumentProcessor(chunking_config, config)

    def test_empty_content_validation_fails(self, validator: ContentValidator) -> None:
        """Test that empty content fails validation."""
        result = validator.validate_content("", Path("test.md"))

        assert result.is_valid is False
        assert result.error is not None and "empty" in result.error.lower()
        assert (
            result.error is not None
            and "no processable content" in result.error.lower()
        )

    def test_whitespace_only_content_validation_fails(
        self, validator: ContentValidator
    ) -> None:
        """Test that whitespace-only content fails validation."""
        whitespace_cases = [
            "   ",  # spaces only
            "\t\t\t",  # tabs only
            "\n\n\n",  # newlines only
            "   \n\n\t\t\n   \n",  # mixed whitespace
            "\r\n\r\n\r\n",  # windows line endings
        ]

        for whitespace_content in whitespace_cases:
            result = validator.validate_content(whitespace_content, Path("test.md"))

            assert result.is_valid is False, (
                f"Should fail for: {repr(whitespace_content)}"
            )
            assert result.error is not None and "empty" in result.error.lower()
            assert (
                result.error is not None
                and "no processable content" in result.error.lower()
            )

    def test_completely_empty_file_processing_fails(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that completely empty files fail processing."""
        empty_file = temp_dir / "empty.md"
        empty_file.write_text("", encoding="utf-8")

        result = processor.process_document(empty_file)

        assert result.success is False
        assert result.chunks_created == 0
        assert result.error is not None and "empty" in result.error.lower()
        assert (
            result.error is not None
            and "no processable content" in result.error.lower()
        )

    def test_whitespace_only_file_processing_fails(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that whitespace-only files fail processing."""
        whitespace_cases = [
            ("spaces_only", "    " * 100),
            ("tabs_only", "\t" * 50),
            ("newlines_only", "\n" * 20),
            ("mixed_whitespace", "   \n\n\t\t\n   \n\t  \n\n\t"),
            ("carriage_returns", "\r\n\r\n\r\n\r\n"),
            ("unicode_whitespace", "\u00a0\u2000\u2001\u2002\u2003"),
        ]

        for case_name, content in whitespace_cases:
            whitespace_file = temp_dir / f"whitespace_{case_name}.md"
            whitespace_file.write_text(content, encoding="utf-8")

            result = processor.process_document(whitespace_file)

            assert result.success is False, f"Should fail for {case_name}"
            assert result.chunks_created == 0
            assert result.error is not None and "empty" in result.error.lower()

    def test_empty_file_strict_mode_fails(
        self, strict_processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that empty files fail in strict mode."""
        empty_file = temp_dir / "empty_strict.md"
        empty_file.write_text("", encoding="utf-8")

        result = strict_processor.process_document(empty_file)

        assert result.success is False
        assert result.chunks_created == 0
        assert result.error is not None and "empty" in result.error.lower()

    def test_empty_file_graceful_mode_fails(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that empty files fail even in graceful mode."""
        empty_file = temp_dir / "empty_graceful.md"
        empty_file.write_text("", encoding="utf-8")

        result = processor.process_document(empty_file)

        # Empty files should fail consistently in both modes
        assert result.success is False
        assert result.chunks_created == 0
        assert result.error is not None and "empty" in result.error.lower()

    def test_zero_byte_file_processing_fails(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that zero-byte files fail processing."""
        zero_byte_file = temp_dir / "zero_bytes.md"
        zero_byte_file.touch()  # Creates empty file

        assert zero_byte_file.stat().st_size == 0

        result = processor.process_document(zero_byte_file)

        assert result.success is False
        assert result.chunks_created == 0
        assert result.error is not None and "empty" in result.error.lower()

    def test_file_with_only_bom_fails(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that files with only BOM character fail processing."""
        bom_file = temp_dir / "bom_only.md"
        # Write only UTF-8 BOM
        bom_file.write_bytes(b"\xef\xbb\xbf")

        result = processor.process_document(bom_file)

        assert result.success is False
        assert result.chunks_created == 0
        # After decoding BOM, content should be empty
        assert result.error is not None and "empty" in result.error.lower()

    def test_file_with_bom_and_whitespace_fails(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that files with BOM and only whitespace fail processing."""
        bom_whitespace_file = temp_dir / "bom_whitespace.md"
        # Write UTF-8 BOM followed by whitespace
        bom_whitespace_file.write_bytes(b"\xef\xbb\xbf   \n\n\t\t\n   ")

        result = processor.process_document(bom_whitespace_file)

        assert result.success is False
        assert result.chunks_created == 0
        assert result.error is not None and "empty" in result.error.lower()

    def test_minimal_valid_content_succeeds(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that minimal but valid content succeeds."""
        minimal_cases = [
            ("single_header", "# Title"),
            ("header_with_text", "# Title\n\nText."),
            ("simple_paragraph", "This is text."),
            ("single_list_item", "- Item"),
            ("single_quote", "> Quote"),
            ("code_block", "```\ncode\n```"),
        ]

        for case_name, content in minimal_cases:
            minimal_file = temp_dir / f"minimal_{case_name}.md"
            minimal_file.write_text(content, encoding="utf-8")

            result = processor.process_document(minimal_file)

            assert result.success is True, f"Should succeed for {case_name}: {content}"
            assert result.chunks_created > 0
            assert result.error is None

    def test_content_with_leading_whitespace_succeeds(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that content with leading whitespace but valid text succeeds."""
        content_with_leading_whitespace = """


    # Title with Leading Whitespace

    This document has some leading whitespace but contains valid content.
    """

        whitespace_file = temp_dir / "leading_whitespace.md"
        whitespace_file.write_text(content_with_leading_whitespace, encoding="utf-8")

        result = processor.process_document(whitespace_file)

        assert result.success is True
        assert result.chunks_created > 0
        assert result.error is None

    def test_content_with_trailing_whitespace_succeeds(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that content with trailing whitespace but valid text succeeds."""
        content_with_trailing_whitespace = """# Title with Trailing Whitespace

This document has valid content but trailing whitespace.



   """

        whitespace_file = temp_dir / "trailing_whitespace.md"
        whitespace_file.write_text(content_with_trailing_whitespace, encoding="utf-8")

        result = processor.process_document(whitespace_file)

        assert result.success is True
        assert result.chunks_created > 0
        assert result.error is None

    def test_disabled_validation_allows_empty(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test that disabled validation allows empty content through."""
        # Create processor with validation disabled
        config = ProcessingConfig()
        config.validation.enable_content_validation = False

        processor = DocumentProcessor(chunking_config, config)

        empty_file = temp_dir / "empty_no_validation.md"
        empty_file.write_text("", encoding="utf-8")

        result = processor.process_document(empty_file)

        # Should still fail because empty content is handled at processor level
        assert result.success is False
        assert result.chunks_created == 0
        assert result.error is not None and "empty" in result.error.lower()

    def test_empty_content_error_consistency(self, validator: ContentValidator) -> None:
        """Test that empty content error messages are consistent."""
        empty_cases = [
            "",
            "   ",
            "\n\n\n",
            "\t\t\t",
            "   \n\n\t\t\n   ",
        ]

        expected_error = "File is empty or contains no processable content"

        for empty_content in empty_cases:
            result = validator.validate_content(empty_content, Path("test.md"))

            assert result.is_valid is False
            assert result.error == expected_error
