"""Unit tests for core data models."""

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from shard_markdown.config.settings import ChunkingParams
from shard_markdown.core.models import (
    BatchResult,
    DocumentChunk,
    InsertResult,
    MarkdownAST,
    MarkdownElement,
    ProcessingResult,
)


class TestMarkdownElement:
    """Test MarkdownElement model."""

    @pytest.mark.unit
    def test_create_basic_element(self) -> None:
        """Test creating basic markdown element."""
        element = MarkdownElement(type="paragraph", text="Test content")

        assert element.type == "paragraph"
        assert element.text == "Test content"
        assert element.level is None
        assert element.language is None
        assert element.items is None
        assert element.metadata == {}

    @pytest.mark.unit
    def test_create_header_element(self) -> None:
        """Test creating header element."""
        element = MarkdownElement(type="header", text="Test Header", level=2)

        assert element.type == "header"
        assert element.text == "Test Header"
        assert element.level == 2

    @pytest.mark.unit
    def test_create_code_block_element(self) -> None:
        """Test creating code block element."""
        element = MarkdownElement(
            type="code_block", text="print('hello')", language="python"
        )

        assert element.type == "code_block"
        assert element.text == "print('hello')"
        assert element.language == "python"

    @pytest.mark.unit
    def test_create_list_element(self) -> None:
        """Test creating list element."""
        items = ["Item 1", "Item 2", "Item 3"]
        element = MarkdownElement(type="list", text="List content", items=items)

        assert element.type == "list"
        assert element.items == items

    @pytest.mark.unit
    def test_element_with_metadata(self) -> None:
        """Test element with custom metadata."""
        metadata = {"custom_field": "value", "another": 123}
        element = MarkdownElement(type="paragraph", text="Test", metadata=metadata)

        assert element.metadata == metadata


class TestMarkdownAST:
    """Test MarkdownAST model."""

    @pytest.mark.unit
    def test_create_empty_ast(self) -> None:
        """Test creating empty AST."""
        ast = MarkdownAST(elements=[])

        assert ast.elements == []
        assert ast.frontmatter == {}
        assert ast.metadata == {}

    @pytest.mark.unit
    def test_create_ast_with_elements(self, sample_ast: MarkdownAST) -> None:
        """Test creating AST with elements."""
        assert len(sample_ast.elements) == 7
        assert any(elem.type == "header" for elem in sample_ast.elements)
        assert any(elem.type == "paragraph" for elem in sample_ast.elements)
        assert any(elem.type == "code_block" for elem in sample_ast.elements)

    @pytest.mark.unit
    def test_headers_property(self, sample_ast: MarkdownAST) -> None:
        """Test headers property."""
        headers = sample_ast.headers

        assert len(headers) == 3  # Main Title, Section 1, Section 2
        assert all(elem.type == "header" for elem in headers)
        assert headers[0].level == 1
        assert headers[1].level == 2
        assert headers[2].level == 2

    @pytest.mark.unit
    def test_code_blocks_property(self, sample_ast: MarkdownAST) -> None:
        """Test code_blocks property."""
        code_blocks = sample_ast.code_blocks

        assert len(code_blocks) == 1
        assert code_blocks[0].type == "code_block"
        assert code_blocks[0].language == "python"

    @pytest.mark.unit
    def test_ast_with_frontmatter(self) -> None:
        """Test AST with frontmatter."""
        frontmatter = {"title": "Test", "author": "Test Author"}
        ast = MarkdownAST(elements=[], frontmatter=frontmatter)

        assert ast.frontmatter == frontmatter

    @pytest.mark.unit
    def test_ast_with_metadata(self) -> None:
        """Test AST with document metadata."""
        metadata = {"word_count": 150, "reading_time": 1}
        ast = MarkdownAST(elements=[], metadata=metadata)

        assert ast.metadata == metadata


class TestDocumentChunk:
    """Test DocumentChunk model."""

    @pytest.mark.unit
    def test_create_basic_chunk(self) -> None:
        """Test creating basic chunk."""
        chunk = DocumentChunk(content="Test chunk content")

        assert chunk.content == "Test chunk content"
        assert chunk.id is None
        assert chunk.metadata == {}
        assert chunk.start_position == 0
        assert chunk.end_position == 0

    @pytest.mark.unit
    def test_create_chunk_with_id(self) -> None:
        """Test creating chunk with ID."""
        chunk = DocumentChunk(id="chunk_001", content="Test content")

        assert chunk.id == "chunk_001"
        assert chunk.content == "Test content"

    @pytest.mark.unit
    def test_chunk_size_property(self) -> None:
        """Test chunk size property."""
        content = "This is test content"
        chunk = DocumentChunk(content=content)

        assert chunk.size == len(content)

    @pytest.mark.unit
    def test_add_metadata(self) -> None:
        """Test adding metadata to chunk."""
        chunk = DocumentChunk(content="Test")

        chunk.add_metadata("source", "test.md")
        chunk.add_metadata("index", 0)

        assert chunk.metadata["source"] == "test.md"
        assert chunk.metadata["index"] == 0

    @pytest.mark.unit
    def test_chunk_with_positions(self) -> None:
        """Test chunk with start/end positions."""
        chunk = DocumentChunk(
            content="Test content", start_position=100, end_position=200
        )

        assert chunk.start_position == 100
        assert chunk.end_position == 200

    @pytest.mark.unit
    def test_chunk_with_complex_metadata(self) -> None:
        """Test chunk with complex metadata."""
        metadata = {
            "source_file": "test.md",
            "chunk_index": 5,
            "total_chunks": 10,
            "structural_context": ["header", "section"],
            "code_languages": ["python", "javascript"],
        }

        chunk = DocumentChunk(content="Test content", metadata=metadata)

        assert chunk.metadata == metadata


class TestProcessingResult:
    """Test ProcessingResult model."""

    @pytest.mark.unit
    def test_create_successful_result(self) -> None:
        """Test creating successful processing result."""
        file_path = Path("test.md")
        result = ProcessingResult(
            file_path=file_path,
            success=True,
            chunks_created=5,
            processing_time=1.5,
            collection_name="test-collection",
        )

        assert result.file_path == file_path
        assert result.success is True
        assert result.chunks_created == 5
        assert result.processing_time == 1.5
        assert result.collection_name == "test-collection"
        assert result.error is None
        assert isinstance(result.timestamp, datetime)

    @pytest.mark.unit
    def test_create_failed_result(self) -> None:
        """Test creating failed processing result."""
        file_path = Path("test.md")
        result = ProcessingResult(
            file_path=file_path, success=False, error="File not found"
        )

        assert result.file_path == file_path
        assert result.success is False
        assert result.chunks_created == 0
        assert result.processing_time == 0.0
        assert result.error == "File not found"

    @pytest.mark.unit
    def test_chunks_per_second_property(self) -> None:
        """Test chunks per second calculation."""
        result = ProcessingResult(
            file_path=Path("test.md"),
            success=True,
            chunks_created=10,
            processing_time=2.0,
        )

        assert result.chunks_per_second == 5.0

    @pytest.mark.unit
    def test_chunks_per_second_zero_time(self) -> None:
        """Test chunks per second with zero processing time."""
        result = ProcessingResult(
            file_path=Path("test.md"),
            success=True,
            chunks_created=10,
            processing_time=0.0,
        )

        assert result.chunks_per_second == 0.0


class TestBatchResult:
    """Test BatchResult model."""

    @pytest.mark.unit
    def test_create_batch_result(self, sample_chunks: list[DocumentChunk]) -> None:
        """Test creating batch result."""
        # Create mock processing results
        results = [
            ProcessingResult(
                file_path=Path(f"test_{i}.md"),
                success=True,
                chunks_created=len(sample_chunks),
                processing_time=1.0,
            )
            for i in range(3)
        ]

        batch_result = BatchResult(
            results=results,
            total_files=3,
            successful_files=3,
            failed_files=0,
            total_chunks=9,
            total_processing_time=3.0,
            collection_name="test-collection",
        )

        assert len(batch_result.results) == 3
        assert batch_result.total_files == 3
        assert batch_result.successful_files == 3
        assert batch_result.failed_files == 0
        assert batch_result.total_chunks == 9
        assert batch_result.collection_name == "test-collection"

    @pytest.mark.unit
    def test_success_rate_property(self) -> None:
        """Test success rate calculation."""
        batch_result = BatchResult(
            results=[],
            total_files=10,
            successful_files=8,
            failed_files=2,
            total_chunks=24,
            total_processing_time=5.0,
            collection_name="test",
        )

        assert batch_result.success_rate == 80.0

    @pytest.mark.unit
    def test_success_rate_zero_files(self) -> None:
        """Test success rate with zero files."""
        batch_result = BatchResult(
            results=[],
            total_files=0,
            successful_files=0,
            failed_files=0,
            total_chunks=0,
            total_processing_time=0.0,
            collection_name="test",
        )

        assert batch_result.success_rate == 0.0

    @pytest.mark.unit
    def test_average_chunks_per_file(self) -> None:
        """Test average chunks per file calculation."""
        batch_result = BatchResult(
            results=[],
            total_files=5,
            successful_files=4,
            failed_files=1,
            total_chunks=12,
            total_processing_time=4.0,
            collection_name="test",
        )

        assert batch_result.average_chunks_per_file == 3.0

    @pytest.mark.unit
    def test_processing_speed_property(self) -> None:
        """Test processing speed calculation."""
        batch_result = BatchResult(
            results=[],
            total_files=10,
            successful_files=8,
            failed_files=2,
            total_chunks=24,
            total_processing_time=2.0,
            collection_name="test",
        )

        assert batch_result.processing_speed == 5.0


class TestChunkingParams:
    """Test ChunkingParams dataclass."""

    @pytest.mark.unit
    def test_create_default_config(self) -> None:
        """Test creating config with defaults."""
        config = ChunkingParams(chunk_size=1000, overlap=200)

        assert config.chunk_size == 1000
        assert config.overlap == 200
        assert config.method == "structure"
        assert config.respect_boundaries is True
        assert config.max_tokens is None

    @pytest.mark.unit
    def test_create_custom_config(self) -> None:
        """Test creating custom config."""
        config = ChunkingParams(
            chunk_size=1500,
            overlap=300,
            method="fixed",
            respect_boundaries=False,
            max_tokens=500,
        )

        assert config.chunk_size == 1500
        assert config.overlap == 300
        assert config.method == "fixed"
        assert config.respect_boundaries is False
        assert config.max_tokens == 500

    @pytest.mark.unit
    def test_config_validation(self) -> None:
        """Test config validation."""
        # Valid config should work
        config = ChunkingParams(chunk_size=1000, overlap=200)
        assert config.chunk_size == 1000

        # Test that basic dataclass creation works
        # (ChunkingParams is now a dataclass, not a Pydantic model)


class TestInsertResult:
    """Test InsertResult model."""

    @pytest.mark.unit
    def test_create_successful_insert_result(self) -> None:
        """Test creating successful insert result."""
        result = InsertResult(
            success=True,
            chunks_inserted=15,
            processing_time=2.5,
            collection_name="test-collection",
        )

        assert result.success is True
        assert result.chunks_inserted == 15
        assert result.processing_time == 2.5
        assert result.collection_name == "test-collection"
        assert result.error is None

    @pytest.mark.unit
    def test_create_failed_insert_result(self) -> None:
        """Test creating failed insert result."""
        result = InsertResult(
            success=False, error="Connection failed", collection_name="test-collection"
        )

        assert result.success is False
        assert result.chunks_inserted == 0
        assert result.processing_time == 0.0
        assert result.error == "Connection failed"

    @pytest.mark.unit
    def test_insertion_rate_property(self) -> None:
        """Test insertion rate calculation."""
        result = InsertResult(
            success=True,
            chunks_inserted=20,
            processing_time=4.0,
            collection_name="test",
        )

        assert result.insertion_rate == 5.0

    @pytest.mark.unit
    def test_insertion_rate_zero_time(self) -> None:
        """Test insertion rate with zero time."""
        result = InsertResult(
            success=True,
            chunks_inserted=10,
            processing_time=0.0,
            collection_name="test",
        )

        assert result.insertion_rate == 0.0


class TestModelValidation:
    """Test model validation and edge cases."""

    @pytest.mark.unit
    def test_markdown_element_required_fields(self) -> None:
        """Test that required fields are enforced."""
        # Should work with required fields
        element = MarkdownElement(type="paragraph", text="content")
        assert element.type == "paragraph"
        assert element.text == "content"

        # Missing required fields should raise ValidationError
        with pytest.raises(ValidationError):
            MarkdownElement(type="paragraph")  # Missing text

        with pytest.raises(ValidationError):
            MarkdownElement(text="content")  # Missing type

    @pytest.mark.unit
    def test_document_chunk_validation(self) -> None:
        """Test DocumentChunk validation."""
        # Content is required
        with pytest.raises(ValidationError):
            DocumentChunk()  # Missing content

        # Valid chunk should work
        chunk = DocumentChunk(content="test")
        assert chunk.content == "test"

    @pytest.mark.unit
    def test_processing_result_validation(self) -> None:
        """Test ProcessingResult validation."""
        # Required fields
        with pytest.raises(ValidationError):
            ProcessingResult(success=True)  # Missing file_path

        # Valid result
        result = ProcessingResult(file_path=Path("test.md"), success=True)
        assert result.file_path == Path("test.md")

    @pytest.mark.unit
    def test_model_serialization(self, sample_chunks: list[DocumentChunk]) -> None:
        """Test model serialization to dict."""
        chunk = sample_chunks[0]
        chunk_dict = chunk.model_dump()

        assert isinstance(chunk_dict, dict)
        assert chunk_dict["content"] == chunk.content
        assert chunk_dict["id"] == chunk.id
        assert chunk_dict["metadata"] == chunk.metadata

    @pytest.mark.unit
    def test_model_json_serialization(self, sample_chunks: list[DocumentChunk]) -> None:
        """Test model JSON serialization."""
        chunk = sample_chunks[0]
        chunk_json = chunk.model_dump_json()

        assert isinstance(chunk_json, str)

        # Should be able to parse back
        import json

        parsed = json.loads(chunk_json)
        assert parsed["content"] == chunk.content
