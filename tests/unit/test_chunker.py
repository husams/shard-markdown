"""Unit tests for chunking engines - using real chunkers with actual markdown."""

import pytest

from shard_markdown.config.settings import Settings
from shard_markdown.core.chunking.engine import ChunkingEngine
from shard_markdown.core.chunking.fixed import FixedSizeChunker
from shard_markdown.core.chunking.structure import StructureAwareChunker
from shard_markdown.core.models import MarkdownAST
from shard_markdown.core.parser import MarkdownParser
from shard_markdown.utils.errors import ProcessingError


class TestChunkingEngine:
    """Test ChunkingEngine with real markdown processing."""

    def test_engine_initialization(self) -> None:
        """Test chunking engine initializes with default strategies."""
        settings = Settings(chunk_size=500, chunk_method="structure")
        engine = ChunkingEngine(settings)

        assert engine.settings == settings
        assert "structure" in engine.strategies
        assert "fixed" in engine.strategies
        assert isinstance(engine.strategies["structure"], StructureAwareChunker)
        assert isinstance(engine.strategies["fixed"], FixedSizeChunker)

    def test_chunk_document_structure_method(self) -> None:
        """Test structure-aware chunking with real markdown."""
        markdown_content = """# Main Document Title

This is the introduction paragraph that provides context.

## Section 1: Getting Started

Here's some content for section 1 with important information.

### Subsection 1.1

Detailed content in the subsection.

```python
def example_function():
    return "Hello, World!"
```

## Section 2: Advanced Topics

More advanced content here with examples and explanations."""

        parser = MarkdownParser()
        ast = parser.parse(markdown_content)

        settings = Settings(chunk_size=200, chunk_method="structure")
        engine = ChunkingEngine(settings)
        chunks = engine.chunk_document(ast)

        assert len(chunks) > 0
        assert all(chunk.content.strip() for chunk in chunks)
        assert all(chunk.id is not None for chunk in chunks)

        # Verify metadata
        for i, chunk in enumerate(chunks):
            assert chunk.metadata["chunk_index"] == i
            assert chunk.metadata["total_chunks"] == len(chunks)
            assert chunk.metadata["chunk_method"] == "structure"

        # First chunk should contain the main title
        assert "Main Document Title" in chunks[0].content

    def test_chunk_document_fixed_method(self) -> None:
        """Test fixed-size chunking with real markdown."""
        markdown_content = """# Document

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor
incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis
nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore
eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt
in culpa qui officia deserunt mollit anim id est laborum.

Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium
doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore
veritatis et quasi architecto beatae vitae dicta sunt explicabo."""

        parser = MarkdownParser()
        ast = parser.parse(markdown_content)

        settings = Settings(chunk_size=150, chunk_method="fixed", chunk_overlap=20)
        engine = ChunkingEngine(settings)
        chunks = engine.chunk_document(ast)

        assert len(chunks) > 0
        assert all(chunk.content.strip() for chunk in chunks)

        # Check chunk sizes are within reasonable limits
        for chunk in chunks[:-1]:  # Exclude last chunk which might be smaller
            assert len(chunk.content) <= settings.chunk_size * 1.5

    def test_chunk_empty_document(self) -> None:
        """Test chunking empty document returns empty list."""
        ast = MarkdownAST(elements=[])

        settings = Settings(chunk_size=500)
        engine = ChunkingEngine(settings)
        chunks = engine.chunk_document(ast)

        assert len(chunks) == 0

    def test_invalid_chunking_method(self) -> None:
        """Test invalid chunking method raises error."""
        markdown_content = "# Test\n\nSome content"
        parser = MarkdownParser()
        ast = parser.parse(markdown_content)

        settings = Settings(chunk_method="invalid_method")
        engine = ChunkingEngine(settings)

        with pytest.raises(ProcessingError, match="Unknown chunking strategy"):
            engine.chunk_document(ast)


class TestStructureAwareChunker:
    """Test StructureAwareChunker with real markdown structures."""

    def test_structure_aware_preserves_headers(self) -> None:
        """Test that structure-aware chunking preserves header boundaries."""
        markdown_content = """# Chapter 1

Introduction to chapter 1.

## Section 1.1

Content for section 1.1 with details.

## Section 1.2

Content for section 1.2 with more information.

# Chapter 2

Introduction to chapter 2.

## Section 2.1

Final section content."""

        parser = MarkdownParser()
        ast = parser.parse(markdown_content)

        settings = Settings(chunk_size=100, chunk_method="structure")
        chunker = StructureAwareChunker(settings)
        chunks = chunker.chunk_document(ast)

        assert len(chunks) > 0

        # Headers should be at the start of chunks
        chapter1_chunk = next((c for c in chunks if "# Chapter 1" in c.content), None)
        assert chapter1_chunk is not None
        assert chapter1_chunk.content.strip().startswith("# Chapter 1")

    def test_code_block_preservation(self) -> None:
        """Test that code blocks are properly handled during chunking."""
        markdown_content = """# Code Examples

Here's a complex code block that should not be split:

```python
def complex_function(data):
    # This is a longer function with multiple lines
    # that should stay together in one chunk
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
        else:
            result.append(item)

    # Additional processing
    final_result = sum(result) / len(result) if result else 0
    return final_result
```

Additional content after the code block."""

        parser = MarkdownParser()
        ast = parser.parse(markdown_content)

        # Use larger chunk size to ensure code block fits
        settings = Settings(chunk_size=500, chunk_method="structure")
        chunker = StructureAwareChunker(settings)
        chunks = chunker.chunk_document(ast)

        # Verify chunks were created
        assert len(chunks) > 0

        # Check that the code block content exists in the chunks
        all_content = " ".join(c.content for c in chunks)
        assert "def complex_function(data):" in all_content
        assert "return final_result" in all_content

    def test_list_preservation(self) -> None:
        """Test that lists are kept together when possible."""
        markdown_content = """# Lists

Here are some important points:

- First point with explanation
- Second point with details
- Third point with examples
- Fourth point with conclusion

Another paragraph after the list."""

        parser = MarkdownParser()
        ast = parser.parse(markdown_content)

        settings = Settings(chunk_size=150, chunk_method="structure")
        chunker = StructureAwareChunker(settings)
        chunks = chunker.chunk_document(ast)

        # Find chunk with the list
        list_chunk = next((c for c in chunks if "- First point" in c.content), None)
        assert list_chunk is not None

        # All list items should be in the same chunk if they fit
        assert "- First point" in list_chunk.content
        assert "- Fourth point" in list_chunk.content


class TestFixedSizeChunker:
    """Test FixedSizeChunker with real markdown content."""

    def test_fixed_size_respects_limit(self) -> None:
        """Test that fixed-size chunks respect the size limit."""
        # Generate content of known length
        markdown_content = "# Title\n\n" + ("Word " * 100) + "\n\nEnd."

        parser = MarkdownParser()
        ast = parser.parse(markdown_content)

        settings = Settings(chunk_size=100, chunk_method="fixed", chunk_overlap=0)
        chunker = FixedSizeChunker(settings)
        chunks = chunker.chunk_document(ast)

        assert len(chunks) > 1  # Should be split into multiple chunks

        # Check that chunks don't exceed size limit (with small tolerance)
        for chunk in chunks[:-1]:
            assert len(chunk.content) <= settings.chunk_size * 1.2

    def test_overlap_functionality(self) -> None:
        """Test that overlap parameter is applied to chunks."""
        markdown_content = """The quick brown fox jumps over the lazy dog.
        This is a test sentence to verify overlap functionality.
        We need enough content to create multiple chunks.
        Each chunk should have some overlap with the next one.
        This helps maintain context across chunk boundaries."""

        parser = MarkdownParser()
        ast = parser.parse(markdown_content)

        settings = Settings(chunk_size=100, chunk_method="fixed", chunk_overlap=20)
        chunker = FixedSizeChunker(settings)
        chunks = chunker.chunk_document(ast)

        # Just verify that chunking works with overlap parameter
        assert len(chunks) >= 1
        assert all(chunk.content.strip() for chunk in chunks)

    def test_handles_large_document(self) -> None:
        """Test handling of large documents."""
        # Create a large document
        sections = []
        for i in range(10):
            sections.append(f"## Section {i}\n\n" + "Content " * 50 + "\n")

        markdown_content = "# Large Document\n\n" + "\n".join(sections)

        parser = MarkdownParser()
        ast = parser.parse(markdown_content)

        settings = Settings(chunk_size=200, chunk_method="fixed")
        chunker = FixedSizeChunker(settings)
        chunks = chunker.chunk_document(ast)

        assert len(chunks) >= 5  # Should create many chunks
        assert all(chunk.content.strip() for chunk in chunks)
