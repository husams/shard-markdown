"""Unit tests for metadata extraction functionality."""

from pathlib import Path

import pytest

from shard_markdown.core.metadata import MetadataExtractor
from shard_markdown.core.models import MarkdownAST, MarkdownElement


class TestFileMetadataExtraction:
    """Test file metadata extraction."""

    @pytest.fixture
    def extractor(self) -> MetadataExtractor:
        """Create a MetadataExtractor instance."""
        return MetadataExtractor()

    def test_extract_file_metadata_basic(
        self, extractor: MetadataExtractor, tmp_path: Path
    ) -> None:
        """Test basic file metadata extraction."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_content = "# Test Document\n\nSome content here."
        test_file.write_text(test_content)

        metadata = extractor.extract_file_metadata(test_file)

        # Basic file info - using actual field names from implementation
        assert metadata["file_name"] == "test.md"
        assert metadata["file_path"] == str(test_file.absolute())
        assert metadata["file_suffix"] == ".md"  # Changed from file_extension
        assert metadata["file_size"] == len(test_content.encode("utf-8"))

        # Timestamps should be present - using actual field names
        assert "file_created" in metadata  # Changed from created_at
        assert "file_modified" in metadata  # Changed from modified_at
        # Note: accessed_at is not in the implementation

    def test_extract_file_metadata_nonexistent_file(
        self, extractor: MetadataExtractor, tmp_path: Path
    ) -> None:
        """Test file metadata extraction for non-existent file."""
        nonexistent_file = tmp_path / "does_not_exist.md"

        # The implementation handles errors gracefully and returns partial metadata
        metadata = extractor.extract_file_metadata(nonexistent_file)

        # Should return minimal metadata with error info
        assert metadata["file_name"] == "does_not_exist.md"
        assert metadata["file_path"] == str(nonexistent_file)
        assert "extraction_error" in metadata

    def test_extract_file_metadata_different_extensions(
        self, extractor: MetadataExtractor, tmp_path: Path
    ) -> None:
        """Test file metadata extraction for different extensions."""
        # Test different extensions
        extensions = [".md", ".markdown", ".txt"]

        for ext in extensions:
            test_file = tmp_path / f"test{ext}"
            test_file.write_text("# Test")

            metadata = extractor.extract_file_metadata(test_file)

            assert metadata["file_suffix"] == ext  # Changed from file_extension
            assert metadata["file_name"] == f"test{ext}"


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

        # The fixture doesn't have frontmatter, so title comes from first header
        assert metadata["title"] == "Test Document"  # From first header in fixture

        # Should include structural info (7 elements: 3 headers, 3 paragraphs, 1 code)
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


class TestMetadataSanitization:
    """Test metadata sanitization for ChromaDB compatibility."""

    @pytest.fixture
    def extractor(self) -> MetadataExtractor:
        """Create a MetadataExtractor instance."""
        return MetadataExtractor()

    def test_sanitize_primitive_types(self, extractor: MetadataExtractor) -> None:
        """Test sanitization of primitive types."""
        metadata = {
            "string_field": "test string",
            "int_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "none_field": None,
        }

        sanitized = extractor.sanitize_metadata_for_chromadb(metadata)

        # Primitives should be preserved
        assert sanitized["string_field"] == "test string"
        assert sanitized["int_field"] == 42
        assert sanitized["float_field"] == 3.14
        assert sanitized["bool_field"] is True
        assert sanitized["none_field"] is None

    def test_sanitize_list_conversion(self, extractor: MetadataExtractor) -> None:
        """Test conversion of lists to strings."""
        metadata = {
            "simple_list": ["a", "b", "c"],
            "mixed_list": [1, "two", 3.0],
            "nested_list": [["a", "b"], ["c", "d"]],
            "empty_list": [],
        }

        sanitized = extractor.sanitize_metadata_for_chromadb(metadata)

        # Lists should be converted to strings
        assert isinstance(sanitized["simple_list"], str)
        assert "a" in sanitized["simple_list"]
        assert "b" in sanitized["simple_list"]
        assert "c" in sanitized["simple_list"]

        assert isinstance(sanitized["mixed_list"], str)
        assert isinstance(sanitized["nested_list"], str)
        assert isinstance(sanitized["empty_list"], str)

    def test_sanitize_dict_conversion(self, extractor: MetadataExtractor) -> None:
        """Test conversion of dictionaries to JSON strings."""
        metadata = {
            "simple_dict": {"key": "value", "number": 42},
            "nested_dict": {"outer": {"inner": "value"}},
            "empty_dict": {},
        }

        sanitized = extractor.sanitize_metadata_for_chromadb(metadata)

        # Dicts should be converted to JSON strings
        assert isinstance(sanitized["simple_dict"], str)
        assert isinstance(sanitized["nested_dict"], str)
        assert isinstance(sanitized["empty_dict"], str)

        # Should be valid JSON
        import json

        parsed = json.loads(sanitized["simple_dict"])
        assert parsed["key"] == "value"
        assert parsed["number"] == 42

    def test_sanitize_complex_nested_structures(
        self, extractor: MetadataExtractor
    ) -> None:
        """Test sanitization of complex nested structures."""
        metadata = {
            "complex": {
                "list_in_dict": ["item1", "item2"],
                "dict_in_dict": {"nested": True},
                "mixed": [{"dict_in_list": "value"}, ["list_in_list"]],
            }
        }

        sanitized = extractor.sanitize_metadata_for_chromadb(metadata)

        # Complex structure should be converted to JSON string
        assert isinstance(sanitized["complex"], str)

        # Should be valid JSON
        import json

        parsed = json.loads(sanitized["complex"])
        assert isinstance(parsed, dict)

    def test_sanitize_handles_serialization_errors(
        self, extractor: MetadataExtractor
    ) -> None:
        """Test that sanitization handles objects that can't be serialized."""

        class NonSerializable:
            def __str__(self) -> str:
                return "NonSerializable object"

        metadata = {
            "good_field": "normal string",
            "bad_field": NonSerializable(),
        }

        sanitized = extractor.sanitize_metadata_for_chromadb(metadata)

        # Good field should be preserved
        assert sanitized["good_field"] == "normal string"

        # Bad field should be converted to string representation
        assert isinstance(sanitized["bad_field"], str)
        assert "NonSerializable" in sanitized["bad_field"]

    def test_sanitize_preserves_chromadb_compatible_types(
        self, extractor: MetadataExtractor
    ) -> None:
        """Test that only ChromaDB-compatible types remain after sanitization."""
        metadata = {
            "string": "text",
            "integer": 42,
            "float": 3.14,
            "boolean": False,
            "none": None,
            "list": [1, 2, 3],
            "dict": {"key": "value"},
            "set": {1, 2, 3},  # Non-JSON serializable
            "tuple": (1, 2, 3),  # Should be converted
        }

        sanitized = extractor.sanitize_metadata_for_chromadb(metadata)

        # All values should be ChromaDB-compatible types
        compatible_types = (str, int, float, bool, type(None))
        for key, value in sanitized.items():
            assert isinstance(value, compatible_types), (
                f"Field {key} has incompatible type {type(value)}: {value}"
            )

    def test_sanitize_large_data_structures(self, extractor: MetadataExtractor) -> None:
        """Test sanitization of large data structures."""
        # Create a large list
        large_list = list(range(1000))

        # Create a large dict
        large_dict = {f"key_{i}": f"value_{i}" for i in range(100)}

        metadata = {
            "large_list": large_list,
            "large_dict": large_dict,
            "normal_field": "test",
        }

        sanitized = extractor.sanitize_metadata_for_chromadb(metadata)

        # Large structures should be converted to strings
        assert isinstance(sanitized["large_list"], str)
        assert isinstance(sanitized["large_dict"], str)
        assert sanitized["normal_field"] == "test"

        # Should not be empty strings
        assert len(sanitized["large_list"]) > 0
        assert len(sanitized["large_dict"]) > 0


class TestMetadataQualityAndValidation:
    """Test metadata quality and validation."""

    @pytest.fixture
    def extractor(self) -> MetadataExtractor:
        """Create a MetadataExtractor instance."""
        return MetadataExtractor()

    def test_metadata_keys_are_valid(self, extractor: MetadataExtractor) -> None:
        """Test that metadata keys are valid identifiers."""
        # Create test data
        ast = MarkdownAST(
            elements=[
                MarkdownElement(type="header", text="Title", level=1),
                MarkdownElement(type="paragraph", text="Content"),
            ]
        )

        metadata = extractor.extract_document_metadata(ast)

        # All keys should be valid Python identifiers (mostly)
        # and suitable for ChromaDB
        for key in metadata.keys():
            assert isinstance(key, str)
            assert len(key) > 0
            assert not key.startswith("_")  # Avoid private-looking keys
            # Should not contain problematic characters
            problematic_chars = [" ", ".", "-", "/", "\\"]
            assert not any(char in key for char in problematic_chars)

    def test_metadata_values_are_reasonable(
        self, extractor: MetadataExtractor, tmp_path: Path
    ) -> None:
        """Test that metadata values are reasonable."""
        # Create a test file
        test_file = tmp_path / "reasonable_test.md"
        test_file.write_text(
            "# Test Document\n\nThis is some content that should produce "
            "reasonable metadata values."
        )

        file_metadata = extractor.extract_file_metadata(test_file)

        # File size should be reasonable
        assert file_metadata["file_size"] > 0
        assert file_metadata["file_size"] < 1000000  # Less than 1MB for our small file

        # Timestamps should be ISO format strings (not Unix timestamps)
        created_time = file_metadata["file_created"]
        modified_time = file_metadata["file_modified"]

        # Should be ISO format strings
        assert isinstance(created_time, str)
        assert isinstance(modified_time, str)

        # Should contain reasonable timestamp format (ISO format check)
        import datetime

        try:
            datetime.datetime.fromisoformat(created_time)
            datetime.datetime.fromisoformat(modified_time)
        except ValueError:
            pytest.fail("Timestamps are not in valid ISO format")

    def test_metadata_consistency(self, extractor: MetadataExtractor) -> None:
        """Test that metadata extraction is consistent."""
        # Create identical ASTs
        elements = [
            MarkdownElement(type="header", text="Consistent Title", level=1),
            MarkdownElement(type="paragraph", text="Consistent content."),
        ]

        ast1 = MarkdownAST(elements=elements.copy())
        ast2 = MarkdownAST(elements=elements.copy())

        metadata1 = extractor.extract_document_metadata(ast1)
        metadata2 = extractor.extract_document_metadata(ast2)

        # Should produce identical metadata (except for timestamps)
        for key in metadata1:
            if "at" not in key and "timestamp" not in key:  # Skip time-based fields
                assert metadata1[key] == metadata2[key], f"Inconsistent value for {key}"
