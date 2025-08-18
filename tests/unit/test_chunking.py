"""Unit tests for chunking engines."""

from pathlib import Path

import pytest

from shard_markdown.config import ChunkingConfig
from shard_markdown.core.chunking.engine import ChunkingEngine
from shard_markdown.core.chunking.fixed import FixedSizeChunker
from shard_markdown.core.chunking.structure import StructureAwareChunker
from shard_markdown.core.parser import MarkdownParser


class TestChunkingEngine:
    """Test cases for ChunkingEngine."""

    @pytest.mark.unit
    def test_chunk_engine_initialization(self, chunking_config: ChunkingConfig) -> None:
        """Test ChunkingEngine initializes correctly."""
        engine = ChunkingEngine(chunking_config)

        assert engine.config == chunking_config
        assert "structure" in engine.strategies
        assert "fixed" in engine.strategies
        assert isinstance(engine.strategies["structure"], StructureAwareChunker)
        assert isinstance(engine.strategies["fixed"], FixedSizeChunker)

    @pytest.mark.unit
    def test_chunk_simple_document(
        self, chunking_config: ChunkingConfig, sample_md_file: Path
    ) -> None:
        """Test chunking a simple document."""
        parser = MarkdownParser()
        engine = ChunkingEngine(chunking_config)

        # Read and parse the file
        content = sample_md_file.read_text()
        ast = parser.parse(content)

        # Chunk the document
        chunks = engine.chunk_document(ast)

        assert len(chunks) > 0
        assert all(chunk.content.strip() for chunk in chunks)
        assert all(chunk.id is not None for chunk in chunks)

        # Check metadata
        for i, chunk in enumerate(chunks):
            assert chunk.metadata["chunk_index"] == i
            assert chunk.metadata["total_chunks"] == len(chunks)

    @pytest.mark.unit
    def test_empty_document(self, chunking_config: ChunkingConfig) -> None:
        """Test chunking empty document."""
        engine = ChunkingEngine(chunking_config)

        # Empty AST
        from shard_markdown.core.models import MarkdownAST

        empty_ast = MarkdownAST(elements=[])

        chunks = engine.chunk_document(empty_ast)
        assert chunks == []
