"""Tests for DocumentProcessor handling of various text encodings."""

import tempfile
from pathlib import Path

import pytest

from shard_markdown.core.models import ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor


class TestEncodingEdgeCases:
    """Test DocumentProcessor with various text encodings."""

    @pytest.fixture
    def processor(self) -> DocumentProcessor:
        """Create a DocumentProcessor for testing."""
        config = ChunkingConfig(method="structure", chunk_size=1000, overlap=50)
        return DocumentProcessor(chunking_config=config)

    def test_utf8_encoding(self, processor: DocumentProcessor) -> None:
        """Test processing of UTF-8 encoded files."""
        content = """# UTF-8 Test

This is a test with UTF-8 characters: áëíóú, 中文, 🚀

## Section

More content here.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", encoding="utf-8", delete=False
        ) as f:
            f.write(content)
            f.flush()

            result = processor.process_file(Path(f.name))
            assert result.success
            assert result.chunks_created > 0

    def test_latin1_encoding(self, processor: DocumentProcessor) -> None:
        """Test processing of Latin-1 encoded files."""
        content = """# Latin-1 Test

This file contains Latin-1 characters: café, naïve, résumé

## Section

More content here.
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", encoding="latin-1", delete=False
        ) as f:
            f.write(content)
            f.flush()

            # This should still work due to encoding detection
            result = processor.process_file(Path(f.name))
            assert result.success or "encoding" in (result.error or "").lower()

    def test_mixed_encoding_fallback(self, processor: DocumentProcessor) -> None:
        """Test encoding fallback behavior."""
        # Create a file with bytes that might cause encoding issues
        content_bytes = b"# Test\n\nSome content with \x80\x81 invalid UTF-8 bytes\n"

        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(content_bytes)
            f.flush()

            # Should handle encoding issues gracefully
            result = processor.process_file(Path(f.name))
            # May succeed with fallback encoding or fail gracefully
            if not result.success:
                error_lower = (result.error or "").lower()
                assert "encoding" in error_lower or "decode" in error_lower
