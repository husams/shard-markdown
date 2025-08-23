"""Unit tests for core data models and metadata - pure validation, no mocks."""

import json
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from shard_markdown.core.metadata import MetadataExtractor
from shard_markdown.core.models import (
    BatchResult,
    DocumentChunk,
    InsertResult,
    MarkdownAST,
    MarkdownElement,
    ProcessingResult,
)


class TestMarkdownElement:
    """Test MarkdownElement model - pure data validation."""

    def test_create_basic_element(self) -> None:
        """Test creating basic markdown element."""
        element = MarkdownElement(type="paragraph", text="Test content")

        assert element.type == "paragraph"
        assert element.text == "Test content"
        assert element.level is None
        assert element.language is None
        assert element.items is None
        assert element.metadata == {}

    def test_create_header_element(self) -> None:
        """Test creating header element with level."""
        element = MarkdownElement(type="header", text="Test Header", level=2)

        assert element.type == "header"
        assert element.text == "Test Header"
        assert element.level == 2

    def test_create_code_block_element(self) -> None:
        """Test creating code block element with language."""
        element = MarkdownElement(
            type="code_block", text="print('hello')", language="python"
        )

        assert element.type == "code_block"
        assert element.text == "print('hello')"
        assert element.language == "python"

    def test_create_list_element(self) -> None:
        """Test creating list element with items."""
        items = ["Item 1", "Item 2", "Item 3"]
        element = MarkdownElement(type="list", text="List content", items=items)

        assert element.type == "list"
        assert element.items == items

    def test_element_with_metadata(self) -> None:
        """Test element with custom metadata."""
        metadata = {"custom_field": "value", "another": 123}
        element = MarkdownElement(type="paragraph", text="Test", metadata=metadata)

        assert element.metadata == metadata

    def test_element_required_fields(self) -> None:
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


class TestMarkdownAST:
    """Test MarkdownAST model - pure data structures."""

    def test_create_empty_ast(self) -> None:
        """Test creating empty AST."""
        ast = MarkdownAST(elements=[])

        assert ast.elements == []
        assert ast.frontmatter == {}
        assert ast.metadata == {}

    def test_create_ast_with_elements(self) -> None:
        """Test creating AST with various elements."""
        elements = [
            MarkdownElement(type="header", text="Title", level=1),
            MarkdownElement(type="paragraph", text="Content"),
            MarkdownElement(type="code_block", text="code", language="python"),
        ]
        ast = MarkdownAST(elements=elements)

        assert len(ast.elements) == 3
        assert ast.elements[0].type == "header"
        assert ast.elements[1].type == "paragraph"
        assert ast.elements[2].type == "code_block"

    def test_headers_property(self) -> None:
        """Test headers property filtering."""
        elements = [
            MarkdownElement(type="header", text="Main Title", level=1),
            MarkdownElement(type="paragraph", text="Some text"),
            MarkdownElement(type="header", text="Section 1", level=2),
            MarkdownElement(type="header", text="Section 2", level=2),
        ]
        ast = MarkdownAST(elements=elements)
        headers = ast.headers

        assert len(headers) == 3
        assert all(elem.type == "header" for elem in headers)
        assert headers[0].level == 1
        assert headers[1].level == 2
        assert headers[2].level == 2

    def test_code_blocks_property(self) -> None:
        """Test code_blocks property filtering."""
        elements = [
            MarkdownElement(type="paragraph", text="Text"),
            MarkdownElement(type="code_block", text="print()", language="python"),
            MarkdownElement(type="code_block", text="console.log()", language="js"),
        ]
        ast = MarkdownAST(elements=elements)
        code_blocks = ast.code_blocks

        assert len(code_blocks) == 2
        assert all(elem.type == "code_block" for elem in code_blocks)
        assert code_blocks[0].language == "python"
        assert code_blocks[1].language == "js"

    def test_ast_with_frontmatter(self) -> None:
        """Test AST with frontmatter metadata."""
        frontmatter = {"title": "Test", "author": "Test Author", "tags": ["test"]}
        ast = MarkdownAST(elements=[], frontmatter=frontmatter)

        assert ast.frontmatter == frontmatter
        assert ast.frontmatter["title"] == "Test"
        assert ast.frontmatter["tags"] == ["test"]

    def test_ast_with_metadata(self) -> None:
        """Test AST with document metadata."""
        metadata = {"word_count": 150, "reading_time": 1, "complexity": "medium"}
        ast = MarkdownAST(elements=[], metadata=metadata)

        assert ast.metadata == metadata
        assert ast.metadata["word_count"] == 150


class TestDocumentChunk:
    """Test DocumentChunk model - pure data validation."""

    def test_create_basic_chunk(self) -> None:
        """Test creating basic chunk with defaults."""
        chunk = DocumentChunk(content="Test chunk content")

        assert chunk.content == "Test chunk content"
        assert chunk.id is None
        assert chunk.metadata == {}
        assert chunk.start_position == 0
        assert chunk.end_position == 0

    def test_create_chunk_with_id(self) -> None:
        """Test creating chunk with explicit ID."""
        chunk = DocumentChunk(id="chunk_001", content="Test content")

        assert chunk.id == "chunk_001"
        assert chunk.content == "Test content"

    def test_chunk_size_property(self) -> None:
        """Test chunk size calculation."""
        content = "This is test content that is exactly 35 long"  # 45 chars
        chunk = DocumentChunk(content=content)

        assert chunk.size == len(content)
        assert chunk.size == 44

    def test_add_metadata(self) -> None:
        """Test adding metadata to chunk."""
        chunk = DocumentChunk(content="Test")

        chunk.add_metadata("source", "test.md")
        chunk.add_metadata("index", 0)
        chunk.add_metadata("section", "introduction")

        assert chunk.metadata["source"] == "test.md"
        assert chunk.metadata["index"] == 0
        assert chunk.metadata["section"] == "introduction"

    def test_chunk_with_positions(self) -> None:
        """Test chunk with start/end positions."""
        chunk = DocumentChunk(
            content="Test content", start_position=100, end_position=200
        )

        assert chunk.start_position == 100
        assert chunk.end_position == 200

    def test_chunk_with_complex_metadata(self) -> None:
        """Test chunk with nested metadata structures."""
        metadata = {
            "source_file": "test.md",
            "chunk_index": 5,
            "total_chunks": 10,
            "structural_context": ["header", "section", "subsection"],
            "code_languages": ["python", "javascript"],
            "properties": {"has_code": True, "has_links": False},
        }

        chunk = DocumentChunk(content="Test content", metadata=metadata)

        assert chunk.metadata == metadata
        assert chunk.metadata["structural_context"][0] == "header"
        assert chunk.metadata["properties"]["has_code"] is True

    def test_chunk_validation(self) -> None:
        """Test DocumentChunk field validation."""
        # Content is required
        with pytest.raises(ValidationError):
            DocumentChunk()  # Missing content

        # Valid chunk should work
        chunk = DocumentChunk(content="test")
        assert chunk.content == "test"

        # Empty content should be allowed
        chunk = DocumentChunk(content="")
        assert chunk.content == ""

    def test_chunk_serialization(self) -> None:
        """Test chunk serialization to dict."""
        chunk = DocumentChunk(
            id="test_id",
            content="Test content",
            metadata={"key": "value"},
            start_position=10,
            end_position=20,
        )
        chunk_dict = chunk.model_dump()

        assert isinstance(chunk_dict, dict)
        assert chunk_dict["content"] == "Test content"
        assert chunk_dict["id"] == "test_id"
        assert chunk_dict["metadata"] == {"key": "value"}
        assert chunk_dict["start_position"] == 10
        assert chunk_dict["end_position"] == 20

    def test_chunk_json_serialization(self) -> None:
        """Test chunk JSON serialization."""
        chunk = DocumentChunk(content="Test", metadata={"index": 1})
        chunk_json = chunk.model_dump_json()

        assert isinstance(chunk_json, str)

        # Should be able to parse back
        parsed = json.loads(chunk_json)
        assert parsed["content"] == "Test"
        assert parsed["metadata"]["index"] == 1


class TestProcessingResult:
    """Test ProcessingResult model - pure data validation."""

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

    def test_chunks_per_second_property(self) -> None:
        """Test chunks per second calculation."""
        result = ProcessingResult(
            file_path=Path("test.md"),
            success=True,
            chunks_created=10,
            processing_time=2.0,
        )

        assert result.chunks_per_second == 5.0

    def test_chunks_per_second_zero_time(self) -> None:
        """Test chunks per second with zero processing time."""
        result = ProcessingResult(
            file_path=Path("test.md"),
            success=True,
            chunks_created=10,
            processing_time=0.0,
        )

        assert result.chunks_per_second == 0.0

    def test_processing_result_validation(self) -> None:
        """Test ProcessingResult field validation."""
        # Required fields
        with pytest.raises(ValidationError):
            ProcessingResult(success=True)  # Missing file_path

        # Valid result
        result = ProcessingResult(file_path=Path("test.md"), success=True)
        assert result.file_path == Path("test.md")


class TestBatchResult:
    """Test BatchResult model - pure data validation."""

    def test_create_batch_result(self) -> None:
        """Test creating batch result with multiple files."""
        results = [
            ProcessingResult(
                file_path=Path(f"test_{i}.md"),
                success=True,
                chunks_created=3,
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


class TestInsertResult:
    """Test InsertResult model - pure data validation."""

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

    def test_create_failed_insert_result(self) -> None:
        """Test creating failed insert result."""
        result = InsertResult(
            success=False, error="Connection failed", collection_name="test-collection"
        )

        assert result.success is False
        assert result.chunks_inserted == 0
        assert result.processing_time == 0.0
        assert result.error == "Connection failed"

    def test_insertion_rate_property(self) -> None:
        """Test insertion rate calculation."""
        result = InsertResult(
            success=True,
            chunks_inserted=20,
            processing_time=4.0,
            collection_name="test",
        )

        assert result.insertion_rate == 5.0

    def test_insertion_rate_zero_time(self) -> None:
        """Test insertion rate with zero time."""
        result = InsertResult(
            success=True,
            chunks_inserted=10,
            processing_time=0.0,
            collection_name="test",
        )

        assert result.insertion_rate == 0.0


class TestMetadataExtractor:
    """Test MetadataExtractor functionality - real extraction logic."""

    def test_sanitize_primitive_types(self) -> None:
        """Test that primitive types are preserved during sanitization."""
        extractor = MetadataExtractor()
        metadata = {
            "string_field": "test",
            "int_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "none_field": None,
        }

        result = extractor.sanitize_metadata_for_chromadb(metadata)

        assert result == metadata
        assert isinstance(result["string_field"], str)
        assert isinstance(result["int_field"], int)
        assert isinstance(result["float_field"], float)
        assert isinstance(result["bool_field"], bool)
        assert result["none_field"] is None

    def test_sanitize_simple_list(self) -> None:
        """Test that simple lists are converted to comma-separated strings."""
        extractor = MetadataExtractor()
        metadata = {
            "tags": ["python", "testing", "metadata"],
            "numbers": [1, 2, 3],
            "mixed": ["string", 42, True],
            "empty_list": [],
        }

        result = extractor.sanitize_metadata_for_chromadb(metadata)

        assert result["tags"] == "python,testing,metadata"
        assert result["numbers"] == "1,2,3"
        assert result["mixed"] == "string,42,True"
        assert result["empty_list"] == ""

    def test_sanitize_nested_dict(self) -> None:
        """Test that nested dicts are flattened or serialized."""
        extractor = MetadataExtractor()
        metadata = {
            "simple": "value",
            "nested": {"key1": "value1", "key2": 42, "deep": {"inner": "value"}},
        }

        result = extractor.sanitize_metadata_for_chromadb(metadata)

        assert result["simple"] == "value"
        # Nested dict should be JSON serialized
        assert isinstance(result["nested"], str)
        parsed = json.loads(result["nested"])
        assert parsed["key1"] == "value1"
        assert parsed["deep"]["inner"] == "value"

    def test_extract_chunk_metadata(self) -> None:
        """Test enhancing chunk metadata."""
        extractor = MetadataExtractor()
        chunk = DocumentChunk(
            content="# Header\nThis is content",
            metadata={"source": "test.md", "index": 0},
        )

        # Create base metadata from chunk
        base_metadata = chunk.metadata.copy()
        base_metadata["source_file"] = "test.md"
        base_metadata["chunk_size"] = len(chunk.content)
        base_metadata["title"] = "Test Document"
        base_metadata["tags"] = ["test"]

        # Use enhance_chunk_metadata instead of extract_chunk_metadata
        metadata = extractor.enhance_chunk_metadata(
            chunk_metadata=base_metadata,
            chunk_index=0,
            total_chunks=5,
            structural_context="Document > Header",
        )

        # Check enhanced metadata
        assert metadata["chunk_index"] == 0
        assert metadata["total_chunks"] == 5
        assert metadata["source_file"] == "test.md"
        assert metadata["chunk_size"] == len(chunk.content)
        assert metadata["is_first_chunk"] is True
        assert metadata["is_last_chunk"] is False
        # Check frontmatter was preserved
        assert "title" in metadata
        assert metadata["title"] == "Test Document"

    def test_extract_structural_context(self) -> None:
        """Test enhancing chunk metadata with structural context."""
        extractor = MetadataExtractor()

        # Create base metadata
        base_metadata = {
            "source_file": "doc.md",
            "content_preview": "Content under section",
        }

        # Use enhance_chunk_metadata with structural context
        metadata = extractor.enhance_chunk_metadata(
            chunk_metadata=base_metadata,
            chunk_index=1,
            total_chunks=3,
            structural_context="Main > Section",
        )

        # Should have structural information
        assert "chunk_index" in metadata
        assert metadata["chunk_index"] == 1
        assert metadata["source_file"] == "doc.md"
        assert metadata["structural_context"] == "Main > Section"
        assert metadata["context_depth"] == 2
        assert metadata["is_first_chunk"] is False
        assert metadata["is_last_chunk"] is False
