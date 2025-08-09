"""Unit tests for metadata extraction and sanitization."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from shard_markdown.core.metadata import MetadataExtractor
from shard_markdown.core.models import MarkdownAST, MarkdownElement


class TestMetadataExtractor:
    """Test MetadataExtractor functionality."""

    @pytest.fixture
    def extractor(self) -> MetadataExtractor:
        """Create a MetadataExtractor instance."""
        return MetadataExtractor()

    @pytest.fixture
    def sample_ast(self) -> MarkdownAST:
        """Create a sample MarkdownAST for testing."""
        elements = [
            MarkdownElement(
                type="header",
                text="Main Title",
                level=1,
            ),
            MarkdownElement(
                type="paragraph",
                text="This is a paragraph.",
            ),
            MarkdownElement(
                type="header",
                text="Section A",
                level=2,
            ),
            MarkdownElement(
                type="code_block",
                text="print('hello')",
                language="python",
            ),
            MarkdownElement(
                type="header",
                text="Section B",
                level=3,
            ),
            MarkdownElement(
                type="list",
                text="- Item 1\n- Item 2",
            ),
        ]

        frontmatter = {
            "title": "Document Title",
            "author": "Test Author",
            "tags": ["test", "markdown", "example"],
            "meta": {"category": "testing", "priority": 1},
        }

        return MarkdownAST(elements=elements, frontmatter=frontmatter)


class TestMetadataSanitization:
    """Test metadata sanitization for ChromaDB compatibility."""

    @pytest.fixture
    def extractor(self) -> MetadataExtractor:
        """Create a MetadataExtractor instance."""
        return MetadataExtractor()

    def test_sanitize_primitive_types(self, extractor: MetadataExtractor) -> None:
        """Test that primitive types are left unchanged."""
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

    def test_sanitize_simple_list(self, extractor: MetadataExtractor) -> None:
        """Test that simple lists are converted to comma-separated strings."""
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

    def test_sanitize_simple_dict(self, extractor: MetadataExtractor) -> None:
        """Test that dictionaries are converted to JSON strings."""
        metadata = {
            "config": {"host": "localhost", "port": 8000},
            "nested": {"a": 1, "b": {"c": 2}},
            "empty_dict": {},
        }

        result = extractor.sanitize_metadata_for_chromadb(metadata)

        # Check that dicts are converted to JSON
        assert result["config"] == '{"host":"localhost","port":8000}'
        assert result["nested"] == '{"a":1,"b":{"c":2}}'
        assert result["empty_dict"] == "{}"

        # Verify JSON is valid
        assert json.loads(result["config"]) == {"host": "localhost", "port": 8000}
        assert json.loads(result["nested"]) == {"a": 1, "b": {"c": 2}}

    def test_sanitize_list_of_dicts(self, extractor: MetadataExtractor) -> None:
        """Test that lists containing dictionaries are properly handled."""
        metadata = {
            "table_of_contents": [
                {"level": 1, "text": "Chapter 1"},
                {"level": 2, "text": "Section 1.1"},
                {"level": 2, "text": "Section 1.2"},
            ]
        }

        result = extractor.sanitize_metadata_for_chromadb(metadata)

        # Should be a comma-separated list of JSON strings
        expected = (
            '{"level":1,"text":"Chapter 1"},'
            '{"level":2,"text":"Section 1.1"},'
            '{"level":2,"text":"Section 1.2"}'
        )
        assert result["table_of_contents"] == expected

    def test_sanitize_nested_lists(self, extractor: MetadataExtractor) -> None:
        """Test that nested lists are properly handled."""
        metadata = {
            "matrix": [[1, 2], [3, 4]],
            "mixed_nested": ["string", [1, 2, 3], {"key": "value"}],
        }

        result = extractor.sanitize_metadata_for_chromadb(metadata)

        # Nested structures should be JSON-encoded
        assert result["matrix"] == "[1,2],[3,4]"
        assert result["mixed_nested"] == 'string,[1,2,3],{"key":"value"}'

    def test_sanitize_real_document_metadata(
        self, extractor: MetadataExtractor
    ) -> None:
        """Test sanitization with realistic document metadata."""
        metadata = {
            # Primitive types (should remain unchanged)
            "file_name": "example.md",
            "file_size": 1024,
            "word_count": 150,
            "is_first_chunk": True,
            "processed_at": None,
            # Lists (should be comma-separated)
            "header_levels": [1, 2, 3],
            "code_languages": ["python", "javascript"],
            # Dictionaries (should be JSON)
            "file_stats": {"lines": 50, "chars": 1024},
            # Complex nested structures
            "table_of_contents": [
                {"level": 1, "text": "Introduction"},
                {"level": 2, "text": "Getting Started"},
            ],
        }

        result = extractor.sanitize_metadata_for_chromadb(metadata)

        # Primitives unchanged
        assert result["file_name"] == "example.md"
        assert result["file_size"] == 1024
        assert result["word_count"] == 150
        assert result["is_first_chunk"] is True
        assert result["processed_at"] is None

        # Lists converted
        assert result["header_levels"] == "1,2,3"
        assert result["code_languages"] == "python,javascript"

        # Dict converted to JSON
        assert result["file_stats"] == '{"lines":50,"chars":1024}'

        # Complex structure converted
        expected_toc = (
            '{"level":1,"text":"Introduction"},{"level":2,"text":"Getting Started"}'
        )
        assert result["table_of_contents"] == expected_toc

    def test_sanitize_edge_cases(self, extractor: MetadataExtractor) -> None:
        """Test edge cases in sanitization."""
        metadata = {
            "single_item_list": ["only_one"],
            "list_with_none": [1, None, 3],
            "dict_with_none": {"key": None, "other": "value"},
            "empty_string": "",
            "zero": 0,
            "false_bool": False,
        }

        result = extractor.sanitize_metadata_for_chromadb(metadata)

        assert result["single_item_list"] == "only_one"
        assert result["list_with_none"] == "1,None,3"
        assert result["dict_with_none"] == '{"key":null,"other":"value"}'
        assert result["empty_string"] == ""
        assert result["zero"] == 0
        assert result["false_bool"] is False

    def test_sanitize_invalid_json_fallback(self, extractor: MetadataExtractor) -> None:
        """Test fallback to string conversion for invalid JSON."""

        # Create a mock object that can't be JSON-serialized
        class UnserializableObject:
            def __str__(self) -> str:
                return "unserializable_object"

        metadata = {
            "invalid_dict": {"circular": UnserializableObject()},
            "invalid_list": [UnserializableObject()],
        }

        result = extractor.sanitize_metadata_for_chromadb(metadata)

        # Should fall back to string conversion
        assert isinstance(result["invalid_dict"], str)
        assert isinstance(result["invalid_list"], str)

    def test_sanitize_non_dict_input(self, extractor: MetadataExtractor) -> None:
        """Test sanitization with non-dictionary input."""
        # Should return input unchanged if not a dict
        assert extractor.sanitize_metadata_for_chromadb("not a dict") == "not a dict"
        assert extractor.sanitize_metadata_for_chromadb([1, 2, 3]) == [1, 2, 3]
        assert extractor.sanitize_metadata_for_chromadb(None) is None

    def test_sanitize_metadata_value_individual(
        self, extractor: MetadataExtractor
    ) -> None:
        """Test the _sanitize_metadata_value method directly."""
        # Primitives
        assert extractor._sanitize_metadata_value("string") == "string"
        assert extractor._sanitize_metadata_value(42) == 42
        assert extractor._sanitize_metadata_value(3.14) == 3.14
        assert extractor._sanitize_metadata_value(True) is True
        assert extractor._sanitize_metadata_value(None) is None

        # Lists
        assert extractor._sanitize_metadata_value([1, 2, 3]) == "1,2,3"
        assert extractor._sanitize_metadata_value([]) == ""

        # Dicts
        assert extractor._sanitize_metadata_value({"a": 1}) == '{"a":1}'
        assert extractor._sanitize_metadata_value({}) == "{}"

        # Other types (converted to string) - use a specific object type for testing
        test_obj = datetime.now()
        assert extractor._sanitize_metadata_value(test_obj) == str(test_obj)


class TestFileMetadataExtraction:
    """Test file metadata extraction."""

    @pytest.fixture
    def extractor(self) -> MetadataExtractor:
        """Create a MetadataExtractor instance."""
        return MetadataExtractor()

    def test_extract_file_metadata(
        self, extractor: MetadataExtractor, tmp_path: Path
    ) -> None:
        """Test basic file metadata extraction."""
        test_file = tmp_path / "test.md"
        test_content = "# Test Document\n\nContent here."
        test_file.write_text(test_content)

        metadata = extractor.extract_file_metadata(test_file)

        # Check essential fields
        assert metadata["file_name"] == "test.md"
        assert metadata["file_stem"] == "test"
        assert metadata["file_suffix"] == ".md"
        assert metadata["file_size"] == len(test_content.encode())
        assert "file_hash" in metadata
        assert metadata["file_hash_algorithm"] == "sha256"
        assert "file_modified" in metadata
        assert "file_created" in metadata

        # Check paths
        assert str(test_file.absolute()) in metadata["file_path"]
        assert metadata["parent_directory"] == str(test_file.parent)

    def test_extract_file_metadata_error_handling(
        self, extractor: MetadataExtractor
    ) -> None:
        """Test error handling in file metadata extraction."""
        nonexistent_file = Path("/nonexistent/file.md")

        metadata = extractor.extract_file_metadata(nonexistent_file)

        # Should still return basic info with error
        assert metadata["file_name"] == "file.md"
        assert "extraction_error" in metadata


class TestDocumentMetadataExtraction:
    """Test document metadata extraction from AST."""

    @pytest.fixture
    def extractor(self) -> MetadataExtractor:
        """Create a MetadataExtractor instance."""
        return MetadataExtractor()

    def test_extract_document_metadata_with_frontmatter(
        self, extractor: MetadataExtractor, sample_ast: MarkdownAST
    ) -> None:
        """Test document metadata extraction with frontmatter."""
        metadata = extractor.extract_document_metadata(sample_ast)

        # Should include frontmatter (using the actual fixture data)
        assert metadata["title"] == "Sample Document"  # From actual fixture
        assert metadata["author"] == "Test Author"

        # Should include structural info
        assert metadata["total_elements"] == 7  # From actual fixture
        assert metadata["header_count"] == 3  # From actual fixture
        assert metadata["paragraph_count"] == 3  # From actual fixture

        # Should include word count and reading time
        assert metadata["word_count"] > 0
        assert metadata["estimated_reading_time_minutes"] >= 1

    def test_extract_document_metadata_without_frontmatter(
        self, extractor: MetadataExtractor
    ) -> None:
        """Test document metadata extraction without frontmatter."""
        elements = [
            MarkdownElement(
                type="header",
                text="Auto Title",
                level=1,
            ),
            MarkdownElement(
                type="paragraph",
                text="Content paragraph.",
            ),
        ]

        # Use empty dict instead of None for frontmatter
        ast = MarkdownAST(elements=elements, frontmatter={})
        metadata = extractor.extract_document_metadata(ast)

        # Should extract title from first header
        assert metadata["title"] == "Auto Title"
        assert metadata["total_elements"] == 2
        assert metadata["header_count"] == 1
        assert metadata["paragraph_count"] == 1

    def test_extract_document_metadata_empty_ast(
        self, extractor: MetadataExtractor
    ) -> None:
        """Test document metadata extraction with empty AST."""
        # Use empty dict instead of None for frontmatter
        ast = MarkdownAST(elements=[], frontmatter={})
        metadata = extractor.extract_document_metadata(ast)

        assert metadata["total_elements"] == 0
        assert metadata["header_count"] == 0
        assert metadata["paragraph_count"] == 0
        assert metadata["word_count"] == 0
        assert metadata["estimated_reading_time_minutes"] == 1  # Minimum

    def test_extract_document_metadata_with_complex_structures(
        self, extractor: MetadataExtractor, sample_ast: MarkdownAST
    ) -> None:
        """Test that complex structures are extracted properly before sanitization."""
        # Add some complex frontmatter to the AST
        ast_with_complex = MarkdownAST(
            elements=[
                MarkdownElement(type="header", text="Title", level=1),
                MarkdownElement(type="header", text="Section", level=2),
                MarkdownElement(type="code_block", text="code", language="python"),
            ],
            frontmatter={
                "tags": ["test", "metadata"],  # List
                "config": {"enabled": True, "count": 5},  # Dict
                "simple": "string",
            },
        )

        metadata = extractor.extract_document_metadata(ast_with_complex)

        # Complex structures should be preserved in raw extraction
        assert isinstance(metadata["tags"], list)
        assert metadata["tags"] == ["test", "metadata"]
        assert isinstance(metadata["config"], dict)
        assert metadata["config"]["enabled"] is True

        # Lists created by the extractor
        assert isinstance(metadata["header_levels"], list)
        assert isinstance(metadata["code_languages"], list)


class TestChunkMetadataEnhancement:
    """Test chunk metadata enhancement."""

    @pytest.fixture
    def extractor(self) -> MetadataExtractor:
        """Create a MetadataExtractor instance."""
        return MetadataExtractor()

    def test_enhance_chunk_metadata(self, extractor: MetadataExtractor) -> None:
        """Test chunk metadata enhancement."""
        base_metadata = {
            "file_name": "test.md",
            "original_field": "value",
        }

        enhanced = extractor.enhance_chunk_metadata(
            chunk_metadata=base_metadata,
            chunk_index=1,
            total_chunks=5,
            structural_context="Document > Chapter 1 > Section A",
        )

        # Should preserve original metadata
        assert enhanced["file_name"] == "test.md"
        assert enhanced["original_field"] == "value"

        # Should add positioning info
        assert enhanced["chunk_index"] == 1
        assert enhanced["total_chunks"] == 5
        assert enhanced["is_first_chunk"] is False
        assert enhanced["is_last_chunk"] is False
        assert enhanced["chunk_position_percent"] == 25.0

        # Should add structural context
        assert enhanced["structural_context"] == "Document > Chapter 1 > Section A"
        assert enhanced["context_depth"] == 3

        # Should add processing info
        assert "processed_at" in enhanced
        assert enhanced["processor_version"] == "0.1.0"

    def test_enhance_chunk_metadata_edge_cases(
        self, extractor: MetadataExtractor
    ) -> None:
        """Test chunk metadata enhancement edge cases."""
        # First chunk
        enhanced = extractor.enhance_chunk_metadata({}, 0, 3)
        assert enhanced["is_first_chunk"] is True
        assert enhanced["is_last_chunk"] is False
        assert enhanced["chunk_position_percent"] == 0.0

        # Last chunk
        enhanced = extractor.enhance_chunk_metadata({}, 2, 3)
        assert enhanced["is_first_chunk"] is False
        assert enhanced["is_last_chunk"] is True
        assert enhanced["chunk_position_percent"] == 100.0

        # Single chunk
        enhanced = extractor.enhance_chunk_metadata({}, 0, 1)
        assert enhanced["is_first_chunk"] is True
        assert enhanced["is_last_chunk"] is True
        assert enhanced["chunk_position_percent"] == 0.0


class TestIntegrationWithSanitization:
    """Test integration between metadata extraction and sanitization."""

    @pytest.fixture
    def extractor(self) -> MetadataExtractor:
        """Create a MetadataExtractor instance."""
        return MetadataExtractor()

    def test_full_pipeline_sanitization(
        self, extractor: MetadataExtractor, tmp_path: Path
    ) -> None:
        """Test full pipeline from extraction to sanitization."""
        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n\nContent")

        # Create AST with complex metadata
        ast = MarkdownAST(
            elements=[
                MarkdownElement(type="header", text="Title", level=1),
                MarkdownElement(type="header", text="Section", level=2),
                MarkdownElement(type="code_block", text="code", language="python"),
            ],
            frontmatter={
                "tags": ["test", "metadata"],  # List that needs sanitization
                "config": {"enabled": True, "count": 5},  # Dict that needs sanitization
            },
        )

        # Extract file metadata
        file_metadata = extractor.extract_file_metadata(test_file)

        # Extract document metadata
        doc_metadata = extractor.extract_document_metadata(ast)

        # Combine metadata (simulating chunk creation)
        combined_metadata = {**file_metadata, **doc_metadata}

        # Enhance chunk metadata
        enhanced_metadata = extractor.enhance_chunk_metadata(
            chunk_metadata=combined_metadata,
            chunk_index=0,
            total_chunks=1,
        )

        # Sanitize for ChromaDB
        sanitized_metadata = extractor.sanitize_metadata_for_chromadb(enhanced_metadata)

        # Verify all values are ChromaDB-compatible using union syntax
        for key, value in sanitized_metadata.items():
            assert isinstance(value, str | int | float | bool | type(None)), (
                f"Key {key} has incompatible type {type(value)}"
            )

        # Verify specific conversions exist
        assert "tags" in sanitized_metadata
        assert isinstance(sanitized_metadata["tags"], str)  # List converted to string
        assert "config" in sanitized_metadata
        assert isinstance(sanitized_metadata["config"], str)  # Dict converted to JSON

        # Verify header_levels if they exist
        if "header_levels" in sanitized_metadata:
            assert isinstance(
                sanitized_metadata["header_levels"], str
            )  # List converted to string

        # Verify table_of_contents if it exists
        if "table_of_contents" in sanitized_metadata:
            assert isinstance(
                sanitized_metadata["table_of_contents"], str
            )  # List of dicts converted

        # Verify primitives are preserved
        assert isinstance(sanitized_metadata["file_size"], int)
        assert isinstance(sanitized_metadata["word_count"], int)
        assert isinstance(sanitized_metadata["is_first_chunk"], bool)
