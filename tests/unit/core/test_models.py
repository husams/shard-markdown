"""Unit tests for core data models."""

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from shard_markdown.core.models import (
    BatchResult,
    ChunkingConfig,
    DocumentChunk,
    InsertResult,
    MarkdownAST,
    MarkdownElement,
    ProcessingResult,
)


class TestMarkdownElement:
    """Test MarkdownElement model."""

    def test_basic_creation(self) -> None:
        """Test basic element creation."""
        element = MarkdownElement(type="header", text="Test Header", level=1)
        assert element.type == "header"
        assert element.text == "Test Header"
        assert element.level == 1
        assert element.language is None
        assert element.items is None
        assert element.metadata == {}

    def test_paragraph_element(self) -> None:
        """Test paragraph element creation."""
        element = MarkdownElement(type="paragraph", text="This is a paragraph.")
        assert element.type == "paragraph"
        assert element.text == "This is a paragraph."
        assert element.level is None

    def test_code_block_element(self) -> None:
        """Test code block element creation."""
        element = MarkdownElement(
            type="code_block", text="print('hello')", language="python"
        )
        assert element.type == "code_block"
        assert element.text == "print('hello')"
        assert element.language == "python"

    def test_list_element(self) -> None:
        """Test list element creation."""
        items = ["Item 1", "Item 2", "Item 3"]
        element = MarkdownElement(type="list", text="", items=items)
        assert element.type == "list"
        assert element.items == items

    def test_metadata_handling(self) -> None:
        """Test metadata handling."""
        metadata = {"source_line": 10, "indent_level": 2}
        element = MarkdownElement(type="paragraph", text="Test", metadata=metadata)
        assert element.metadata == metadata


class TestMarkdownAST:
    """Test MarkdownAST model."""

    def test_empty_ast(self) -> None:
        """Test empty AST creation."""
        ast = MarkdownAST(elements=[])
        assert ast.elements == []
        assert ast.frontmatter == {}
        assert ast.metadata == {}
        assert ast.headers == []
        assert ast.code_blocks == []

    def test_ast_with_elements(self) -> None:
        """Test AST with multiple elements."""
        elements = [
            MarkdownElement(type="header", text="Title", level=1),
            MarkdownElement(type="paragraph", text="Content"),
            MarkdownElement(type="code_block", text="code", language="python"),
        ]
        ast = MarkdownAST(elements=elements)
        assert len(ast.elements) == 3
        assert len(ast.headers) == 1
        assert len(ast.code_blocks) == 1

    def test_frontmatter_handling(self) -> None:
        """Test frontmatter handling."""
        frontmatter = {"title": "Test Document", "author": "Test Author"}
        ast = MarkdownAST(elements=[], frontmatter=frontmatter)
        assert ast.frontmatter == frontmatter

    def test_headers_property(self) -> None:
        """Test headers property filtering."""
        elements = [
            MarkdownElement(type="header", text="H1", level=1),
            MarkdownElement(type="paragraph", text="Para"),
            MarkdownElement(type="header", text="H2", level=2),
        ]
        ast = MarkdownAST(elements=elements)
        headers = ast.headers
        assert len(headers) == 2
        assert headers[0].text == "H1"
        assert headers[1].text == "H2"

    def test_code_blocks_property(self) -> None:
        """Test code_blocks property filtering."""
        elements = [
            MarkdownElement(type="paragraph", text="Para"),
            MarkdownElement(type="code_block", text="code1", language="python"),
            MarkdownElement(type="code_block", text="code2", language="javascript"),
        ]
        ast = MarkdownAST(elements=elements)
        code_blocks = ast.code_blocks
        assert len(code_blocks) == 2
        assert code_blocks[0].text == "code1"
        assert code_blocks[1].text == "code2"


class TestDocumentChunk:
    """Test DocumentChunk model."""

    def test_basic_creation(self) -> None:
        """Test basic chunk creation."""
        chunk = DocumentChunk(content="Test content", start_position=0, end_position=12)
        assert chunk.content == "Test content"
        assert chunk.start_position == 0
        assert chunk.end_position == 12
        assert chunk.size == 12
        assert chunk.id is None
        assert chunk.metadata == {}

    def test_chunk_with_id(self) -> None:
        """Test chunk with custom ID."""
        chunk = DocumentChunk(id="chunk-001", content="Test content")
        assert chunk.id == "chunk-001"

    def test_chunk_with_metadata(self) -> None:
        """Test chunk with initial metadata."""
        metadata = {"source_file": "test.md", "chapter": 1}
        chunk = DocumentChunk(content="Test content", metadata=metadata)
        assert chunk.metadata == metadata

    def test_add_metadata_method(self) -> None:
        """Test adding metadata to chunk."""
        chunk = DocumentChunk(content="Test content")
        chunk.add_metadata("key1", "value1")
        chunk.add_metadata("key2", 123)
        assert chunk.metadata == {"key1": "value1", "key2": 123}

    def test_size_property(self) -> None:
        """Test size property calculation."""
        short_chunk = DocumentChunk(content="Hi")
        long_chunk = DocumentChunk(content="This is a longer piece of content")
        assert short_chunk.size == 2
        assert long_chunk.size == 33


class TestProcessingResult:
    """Test ProcessingResult model."""

    def test_successful_result(self) -> None:
        """Test successful processing result."""
        result = ProcessingResult(
            file_path=Path("test.md"),
            success=True,
            chunks_created=5,
            processing_time=1.5,
        )
        assert result.file_path == Path("test.md")
        assert result.success is True
        assert result.chunks_created == 5
        assert result.processing_time == 1.5
        assert result.chunks_per_second == 5 / 1.5

    def test_failed_result(self) -> None:
        """Test failed processing result."""
        result = ProcessingResult(
            file_path=Path("failed.md"),
            success=False,
            error="File not found",
        )
        assert result.file_path == Path("failed.md")
        assert result.success is False
        assert result.error == "File not found"
        assert result.chunks_per_second == 0.0

    def test_chunks_per_second_zero_time(self) -> None:
        """Test chunks per second with zero processing time."""
        result = ProcessingResult(
            file_path=Path("test.md"),
            success=True,
            chunks_created=5,
            processing_time=0.0,
        )
        assert result.chunks_per_second == 0.0

    def test_timestamp_default(self) -> None:
        """Test timestamp default value."""
        result = ProcessingResult(file_path=Path("test.md"), success=True)
        assert isinstance(result.timestamp, datetime)


class TestBatchResult:
    """Test BatchResult model."""

    def test_batch_result_creation(self) -> None:
        """Test batch result creation."""
        results = [
            ProcessingResult(
                file_path=Path("file1.md"), success=True, chunks_created=3
            ),
            ProcessingResult(
                file_path=Path("file2.md"), success=True, chunks_created=2
            ),
            ProcessingResult(file_path=Path("file3.md"), success=False, error="Error"),
        ]

        batch = BatchResult(
            results=results,
            total_files=3,
            successful_files=2,
            failed_files=1,
            total_chunks=5,
            total_processing_time=3.0,
            collection_name="test_collection",
        )

        assert batch.total_files == 3
        assert batch.successful_files == 2
        assert batch.failed_files == 1
        assert batch.total_chunks == 5
        assert batch.collection_name == "test_collection"

    def test_success_rate_calculation(self) -> None:
        """Test success rate calculation."""
        batch = BatchResult(
            results=[],
            total_files=10,
            successful_files=8,
            failed_files=2,
            total_chunks=0,
            total_processing_time=0.0,
            collection_name="test",
        )
        assert batch.success_rate == 80.0

    def test_success_rate_zero_files(self) -> None:
        """Test success rate with zero files."""
        batch = BatchResult(
            results=[],
            total_files=0,
            successful_files=0,
            failed_files=0,
            total_chunks=0,
            total_processing_time=0.0,
            collection_name="test",
        )
        assert batch.success_rate == 0.0

    def test_average_chunks_per_file(self) -> None:
        """Test average chunks per file calculation."""
        batch = BatchResult(
            results=[],
            total_files=5,
            successful_files=4,
            failed_files=1,
            total_chunks=20,
            total_processing_time=0.0,
            collection_name="test",
        )
        assert batch.average_chunks_per_file == 5.0

    def test_processing_speed_calculation(self) -> None:
        """Test processing speed calculation."""
        batch = BatchResult(
            results=[],
            total_files=10,
            successful_files=10,
            failed_files=0,
            total_chunks=0,
            total_processing_time=5.0,
            collection_name="test",
        )
        assert batch.processing_speed == 2.0


class TestChunkingConfig:
    """Test ChunkingConfig model."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = ChunkingConfig()
        assert config.chunk_size == 1000
        assert config.overlap == 200
        assert config.method == "structure"
        assert config.respect_boundaries is True
        assert config.max_tokens is None
        assert config.include_frontmatter is False
        assert config.include_path_metadata is True

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = ChunkingConfig(
            chunk_size=2000,
            overlap=400,
            method="fixed",
            respect_boundaries=False,
            max_tokens=500,
            include_frontmatter=True,
            include_path_metadata=False,
        )
        assert config.chunk_size == 2000
        assert config.overlap == 400
        assert config.method == "fixed"
        assert config.respect_boundaries is False
        assert config.max_tokens == 500
        assert config.include_frontmatter is True
        assert config.include_path_metadata is False

    def test_chunk_size_validation(self) -> None:
        """Test chunk size validation."""
        # Valid sizes
        ChunkingConfig(chunk_size=100)
        ChunkingConfig(chunk_size=10000)

        # Invalid sizes
        with pytest.raises(ValidationError):
            ChunkingConfig(chunk_size=49)  # Below minimum

        with pytest.raises(ValidationError):
            ChunkingConfig(chunk_size=50001)  # Above maximum

    def test_overlap_validation(self) -> None:
        """Test overlap validation."""
        # Valid overlaps
        ChunkingConfig(overlap=0)
        ChunkingConfig(overlap=500)

        # Invalid overlaps
        with pytest.raises(ValidationError):
            ChunkingConfig(overlap=-1)  # Negative

        with pytest.raises(ValidationError):
            ChunkingConfig(overlap=5001)  # Above maximum

    def test_overlap_vs_chunk_size_validation(self) -> None:
        """Test overlap vs chunk size validation."""
        # Valid: overlap less than chunk size
        ChunkingConfig(chunk_size=1000, overlap=500)

        # Invalid: overlap >= chunk size
        with pytest.raises(ValidationError):
            ChunkingConfig(chunk_size=1000, overlap=1000)

        with pytest.raises(ValidationError):
            ChunkingConfig(chunk_size=1000, overlap=1200)

    def test_method_validation(self) -> None:
        """Test method validation."""
        # Valid methods
        ChunkingConfig(method="structure")
        ChunkingConfig(method="fixed")

        # Invalid method
        with pytest.raises(ValidationError):
            ChunkingConfig(method="invalid")

    def test_max_tokens_validation(self) -> None:
        """Test max tokens validation."""
        # Valid tokens
        ChunkingConfig(max_tokens=None)
        ChunkingConfig(max_tokens=100)
        ChunkingConfig(max_tokens=50000)

        # Invalid tokens
        with pytest.raises(ValidationError):
            ChunkingConfig(max_tokens=0)

        with pytest.raises(ValidationError):
            ChunkingConfig(max_tokens=100001)


class TestInsertResult:
    """Test InsertResult model."""

    def test_successful_insert(self) -> None:
        """Test successful insertion result."""
        result = InsertResult(
            success=True,
            chunks_inserted=10,
            processing_time=2.5,
            collection_name="test_collection",
        )
        assert result.success is True
        assert result.chunks_inserted == 10
        assert result.processing_time == 2.5
        assert result.collection_name == "test_collection"
        assert result.error is None
        assert result.insertion_rate == 4.0

    def test_failed_insert(self) -> None:
        """Test failed insertion result."""
        result = InsertResult(
            success=False,
            error="Database connection failed",
            collection_name="test_collection",
        )
        assert result.success is False
        assert result.error == "Database connection failed"
        assert result.chunks_inserted == 0
        assert result.insertion_rate == 0.0

    def test_insertion_rate_zero_time(self) -> None:
        """Test insertion rate with zero processing time."""
        result = InsertResult(
            success=True,
            chunks_inserted=5,
            processing_time=0.0,
            collection_name="test",
        )
        assert result.insertion_rate == 0.0


@pytest.fixture
def sample_chunks() -> list[DocumentChunk]:
    """Create sample chunks for testing."""
    return [
        DocumentChunk(
            id="chunk-1",
            content="First chunk content",
            start_position=0,
            end_position=19,
        ),
        DocumentChunk(
            id="chunk-2",
            content="Second chunk content",
            start_position=20,
            end_position=40,
        ),
    ]


class TestModelEdgeCases:
    """Test model validation and edge cases."""

    def test_markdown_element_required_fields(self) -> None:
        """Test that required fields are enforced."""
        # Should work with required fields
        element = MarkdownElement(type="paragraph", text="content")
        assert element.type == "paragraph"
        assert element.text == "content"

        # Missing required fields should raise ValidationError
        with pytest.raises(ValidationError):
            MarkdownElement(type="paragraph", text="")

        with pytest.raises(ValidationError):
            MarkdownElement(text="content", type="")

    def test_document_chunk_validation(self) -> None:
        """Test DocumentChunk validation."""
        # Content is required
        with pytest.raises(ValidationError):
            DocumentChunk(content="")

        # Valid chunk should work
        chunk = DocumentChunk(content="test")
        assert chunk.content == "test"

    def test_processing_result_validation(self) -> None:
        """Test ProcessingResult validation."""
        # Required fields
        with pytest.raises(ValidationError):
            ProcessingResult(success=True, file_path=Path())

        # Valid result
        result = ProcessingResult(file_path=Path("test.md"), success=True)
        assert result.file_path == Path("test.md")

    def test_model_serialization(self, sample_chunks: list[DocumentChunk]) -> None:
        """Test model serialization to dict."""
        chunk = sample_chunks[0]
        chunk_dict = chunk.model_dump()

        assert isinstance(chunk_dict, dict)
        assert chunk_dict["content"] == "First chunk content"
        assert chunk_dict["id"] == "chunk-1"

    def test_model_json_serialization(self, sample_chunks: list[DocumentChunk]) -> None:
        """Test model JSON serialization."""
        chunk = sample_chunks[0]
        json_str = chunk.model_dump_json()

        assert isinstance(json_str, str)
        assert "First chunk content" in json_str
        assert "chunk-1" in json_str
