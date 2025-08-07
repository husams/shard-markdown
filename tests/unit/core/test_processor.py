"""Test module for DocumentProcessor core functionality.

This module contains comprehensive tests for the DocumentProcessor class,
covering various scenarios including successful processing, error handling,
edge cases, and integration with ChromaDB.
"""

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from shard_markdown.core.models import ChunkingConfig, ProcessingResult
from shard_markdown.core.processor import DocumentProcessor
from shard_markdown.utils.errors import ProcessingError


class TestDocumentProcessorCore:
    """Test core DocumentProcessor functionality."""

    @pytest.fixture
    def basic_config(self) -> ChunkingConfig:
        """Create basic chunking configuration."""
        return ChunkingConfig(
            chunk_size=500,
            overlap=50,
            method="structure",
            respect_boundaries=True,
        )

    @pytest.fixture
    def processor(self, basic_config: ChunkingConfig) -> DocumentProcessor:
        """Create DocumentProcessor instance for testing."""
        return DocumentProcessor(chunking_config=basic_config)

    def test_processor_initialization(self, basic_config: ChunkingConfig) -> None:
        """Test DocumentProcessor initialization."""
        processor = DocumentProcessor(chunking_config=basic_config)
        assert processor is not None
        assert processor.chunking_config == basic_config

    def test_process_simple_file(self, processor: DocumentProcessor) -> None:
        """Test processing a simple markdown file."""
        content = """# Test Document

This is a simple test document.

## Section 1

Some content here.

## Section 2

More content here.
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            result = processor.process_document(Path(f.name))

            assert isinstance(result, ProcessingResult)
            assert result.success
            assert result.chunks_created > 0
            assert result.processing_time >= 0

    def test_process_empty_file(self, processor: DocumentProcessor) -> None:
        """Test processing an empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("")
            f.flush()

            result = processor.process_document(Path(f.name))

            # Empty files should always fail for consistent behavior
            assert not result.success
            assert result.chunks_created == 0
            assert "empty" in (result.error or "").lower()

    def test_process_nonexistent_file(self, processor: DocumentProcessor) -> None:
        """Test processing a file that doesn't exist."""
        nonexistent_path = Path("/path/that/does/not/exist.md")

        result = processor.process_document(nonexistent_path)

        assert not result.success
        assert result.error is not None
        assert "not found" in result.error.lower() or "exist" in result.error.lower()

    def test_process_large_document(self, processor: DocumentProcessor) -> None:
        """Test processing a large document."""
        # Create a large document
        sections = []
        for i in range(20):
            sections.append(f"# Section {i + 1}")
            sections.append(f"This is content for section {i + 1}." * 10)

        content = "\n\n".join(sections)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            result = processor.process_document(Path(f.name))

            assert result.success
            assert result.chunks_created > 1  # Should create multiple chunks

    @patch("shard_markdown.core.processor.DocumentProcessor._chunk_document")
    def test_chunking_error_handling(
        self, mock_chunk: Any, processor: DocumentProcessor
    ) -> None:
        """Test error handling when chunking fails."""
        mock_chunk.side_effect = ProcessingError("Chunking failed", error_code=1300)

        content = "# Test\n\nSome content."
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            result = processor.process_document(Path(f.name))

            assert not result.success
            assert "Chunking failed" in (result.error or "")

    def test_processor_with_different_configs(self) -> None:
        """Test processor behavior with different configurations."""
        # Small chunks
        small_config = ChunkingConfig(chunk_size=100, overlap=20, method="fixed")
        small_processor = DocumentProcessor(chunking_config=small_config)

        # Large chunks
        large_config = ChunkingConfig(chunk_size=2000, overlap=100, method="structure")
        large_processor = DocumentProcessor(chunking_config=large_config)

        content = """# Long Document

""" + ("This is a long paragraph with lots of content. " * 50)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            small_result = small_processor.process_document(Path(f.name))
            large_result = large_processor.process_document(Path(f.name))

            # Small chunks should create more chunks
            if small_result.success and large_result.success:
                assert small_result.chunks_created >= large_result.chunks_created
