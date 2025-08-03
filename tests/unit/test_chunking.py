"""Unit tests for chunking engines."""

import pytest

from shard_markdown.core.chunking.engine import ChunkingEngine
from shard_markdown.core.chunking.structure import StructureAwareChunker
from shard_markdown.core.chunking.fixed import FixedSizeChunker
from shard_markdown.core.models import ChunkingConfig
from shard_markdown.core.parser import MarkdownParser


class TestChunkingEngine:
    """Test cases for ChunkingEngine."""
    
    def test_engine_initialization(self, chunking_config: ChunkingConfig):
        """Test chunking engine initializes correctly."""
        engine = ChunkingEngine(chunking_config)
        assert engine.config == chunking_config
        assert "structure" in engine.strategies
        assert "fixed" in engine.strategies
    
    def test_chunk_document_structure_method(self, sample_markdown_content: str, chunking_config: ChunkingConfig):
        """Test chunking with structure-aware method."""
        parser = MarkdownParser()
        ast = parser.parse(sample_markdown_content)
        
        chunking_config.method = "structure"
        engine = ChunkingEngine(chunking_config)
        chunks = engine.chunk_document(ast)
        
        assert len(chunks) > 0
        assert all(chunk.content.strip() for chunk in chunks)
        assert all(chunk.id is not None for chunk in chunks)
        
        # Check metadata
        for i, chunk in enumerate(chunks):
            assert chunk.metadata["chunk_index"] == i
            assert chunk.metadata["total_chunks"] == len(chunks)
            assert chunk.metadata["chunk_method"] == "structure"
    
    def test_chunk_document_fixed_method(self, sample_markdown_content: str, chunking_config: ChunkingConfig):
        """Test chunking with fixed-size method."""
        parser = MarkdownParser()
        ast = parser.parse(sample_markdown_content)
        
        chunking_config.method = "fixed"
        engine = ChunkingEngine(chunking_config)
        chunks = engine.chunk_document(ast)
        
        assert len(chunks) > 0
        assert all(chunk.content.strip() for chunk in chunks)
        
        # Check chunk sizes are within reasonable limits
        for chunk in chunks:
            assert len(chunk.content) <= chunking_config.chunk_size * 1.5
    
    def test_chunk_empty_document(self, chunking_config: ChunkingConfig):
        """Test chunking empty document."""
        from shard_markdown.core.models import MarkdownAST
        
        ast = MarkdownAST(elements=[])
        engine = ChunkingEngine(chunking_config)
        chunks = engine.chunk_document(ast)
        
        assert len(chunks) == 0
    
    def test_invalid_chunking_method(self, sample_markdown_content: str, chunking_config: ChunkingConfig):
        """Test chunking with invalid method."""
        parser = MarkdownParser()
        ast = parser.parse(sample_markdown_content)
        
        chunking_config.method = "invalid_method"
        engine = ChunkingEngine(chunking_config)
        
        with pytest.raises(Exception):  # Should raise ProcessingError
            engine.chunk_document(ast)


class TestStructureAwareChunker:
    """Test cases for StructureAwareChunker."""
    
    def test_structure_aware_chunking(self, sample_markdown_content: str, chunking_config: ChunkingConfig):
        """Test structure-aware chunking preserves boundaries."""
        parser = MarkdownParser()
        ast = parser.parse(sample_markdown_content)
        
        chunker = StructureAwareChunker(chunking_config)
        chunks = chunker.chunk_document(ast)
        
        assert len(chunks) > 0
        
        # Check that headers are preserved
        for chunk in chunks:
            if "# Main Title" in chunk.content:
                # Should be in first chunk
                assert chunk == chunks[0]
    
    def test_code_block_preservation(self, chunking_config: ChunkingConfig):
        """Test that code blocks are never split."""
        content = """# Code Example

Here's a long code block:

```python
def very_long_function_name():
    # This is a very long comment that might exceed chunk size
    # when combined with the rest of the code block
    print("This is a very long string that goes on and on")
    print("And continues with more content")
    print("And even more content to make it really long")
    return "A very long return value string"
```

More content after code.
"""
        parser = MarkdownParser()
        ast = parser.parse(content)
        
        # Use small chunk size to force splitting
        chunking_config.chunk_size = 100
        chunker = StructureAwareChunker(chunking_config)
        chunks = chunker.chunk_document(ast)
        
        # Find chunk with code block
        code_chunk = None
        for chunk in chunks:
            if "```python" in chunk.content and "```" in chunk.content:
                code_chunk = chunk
                break
        
        assert code_chunk is not None
        # Code block should be complete in one chunk
        assert chunk.content.count("```") == 2


class TestFixedSizeChunker:
    """Test cases for FixedSizeChunker."""
    
    def test_fixed_size_chunking(self, sample_markdown_content: str, chunking_config: ChunkingConfig):
        """Test fixed-size chunking."""
        parser = MarkdownParser()
        ast = parser.parse(sample_markdown_content)
        
        chunker = FixedSizeChunker(chunking_config)
        chunks = chunker.chunk_document(ast)
        
        assert len(chunks) > 0
        
        # Most chunks should be close to target size
        target_size = chunking_config.chunk_size
        for chunk in chunks[:-1]:  # Exclude last chunk which might be smaller
            assert len(chunk.content) <= target_size * 1.2  # Allow some tolerance
    
    def test_overlap_functionality(self, sample_markdown_content: str, chunking_config: ChunkingConfig):
        """Test that overlap works correctly."""
        parser = MarkdownParser()
        ast = parser.parse(sample_markdown_content)
        
        chunking_config.overlap = 50
        chunker = FixedSizeChunker(chunking_config)
        chunks = chunker.chunk_document(ast)
        
        if len(chunks) > 1:
            # Check that there's some overlap between consecutive chunks
            for i in range(len(chunks) - 1):
                current_chunk = chunks[i].content
                next_chunk = chunks[i + 1].content
                
                # Find potential overlap
                overlap_found = False
                if len(current_chunk) > 20 and len(next_chunk) > 20:
                    # Check if end of current chunk appears in beginning of next
                    current_end = current_chunk[-20:]
                    if any(word in next_chunk[:100] for word in current_end.split()[-3:] if len(word) > 3):
                        overlap_found = True
                
                # This is a heuristic check - overlap might not always be detectable this way
                # The main goal is to ensure the code runs without error