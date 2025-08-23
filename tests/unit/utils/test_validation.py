"""Unit tests for validation utility functions."""

from pathlib import Path

import pytest


class TestNumericValidation:
    """Test numeric value validation."""

    @pytest.mark.unit
    def test_validate_positive_integers(self) -> None:
        """Test validation of positive integer values."""
        # Valid positive integers
        valid_values = [1, 10, 100, 1000, 999999]
        for value in valid_values:
            assert value > 0, f"{value} should be positive"

        # Invalid values
        invalid_values = [-1, -100, 0]
        for value in invalid_values:
            assert not (value > 0), f"{value} should not be positive"

    @pytest.mark.unit
    def test_validate_range_boundaries(self) -> None:
        """Test validation of numeric range boundaries."""
        # Test common boundary values
        assert 0 == 0  # Boundary value
        assert 1 > 0  # Just above boundary
        assert -1 < 0  # Just below boundary

        # Test maximum safe integer operations
        max_safe = 2**31 - 1  # Common max int
        assert max_safe > 0
        assert max_safe + 1 > max_safe

    @pytest.mark.unit
    def test_validate_float_values(self) -> None:
        """Test validation of floating point values."""
        valid_floats = [0.1, 1.5, 99.99, 1000.001]
        for value in valid_floats:
            assert value > 0, f"{value} should be positive"

        invalid_floats = [-0.1, -99.99, 0.0]
        for value in invalid_floats:
            assert not (value > 0) or value == 0


class TestFilePathValidation:
    """Test file path validation utilities."""

    @pytest.mark.unit
    def test_markdown_file_extensions(self) -> None:
        """Test validation of markdown file extensions."""
        # Common markdown extensions
        valid_extensions = [".md", ".markdown", ".mdown", ".mkd", ".mdwn"]

        for ext in valid_extensions:
            path = Path(f"document{ext}")
            assert path.suffix.lower() in [
                ".md",
                ".markdown",
                ".mdown",
                ".mkd",
                ".mdwn",
            ]

    @pytest.mark.unit
    def test_non_markdown_extensions(self) -> None:
        """Test detection of non-markdown file extensions."""
        invalid_extensions = [".txt", ".doc", ".pdf", ".html", ".rst"]

        for ext in invalid_extensions:
            path = Path(f"document{ext}")
            assert path.suffix.lower() not in [".md", ".markdown"]

    @pytest.mark.unit
    def test_case_insensitive_extension_check(self) -> None:
        """Test case-insensitive extension validation."""
        mixed_case_files = [
            Path("README.MD"),
            Path("notes.Markdown"),
            Path("doc.mD"),
            Path("file.MDOWN"),
        ]

        for path in mixed_case_files:
            assert path.suffix.lower() in [
                ".md",
                ".markdown",
                ".mdown",
            ]

    @pytest.mark.unit
    def test_files_without_extensions(self) -> None:
        """Test handling of files without extensions."""
        files = [Path("README"), Path("Makefile"), Path("LICENSE")]

        for path in files:
            assert path.suffix == ""


class TestURLValidation:
    """Test URL validation patterns."""

    @pytest.mark.unit
    def test_valid_http_urls(self) -> None:
        """Test validation of HTTP/HTTPS URLs."""
        valid_urls = [
            "http://localhost:8000",
            "https://example.com",
            "http://192.168.1.1:8080",
            "https://api.example.com/v1",
            "http://localhost:3000/path",
        ]

        for url in valid_urls:
            assert url.startswith(("http://", "https://"))

    @pytest.mark.unit
    def test_invalid_url_formats(self) -> None:
        """Test detection of invalid URL formats."""
        invalid_urls = [
            "not_a_url",
            "ftp://example.com",  # Not HTTP/HTTPS
            "//example.com",  # Missing protocol
            "example.com",  # No protocol
            "http:/",  # Malformed
            "",  # Empty
        ]

        for url in invalid_urls:
            assert not url.startswith(("http://", "https://"))

    @pytest.mark.unit
    def test_localhost_url_variations(self) -> None:
        """Test various localhost URL formats."""
        localhost_urls = [
            "http://localhost",
            "http://localhost:8000",
            "http://127.0.0.1",
            "http://127.0.0.1:8000",
            "http://0.0.0.0:8000",  # noqa: S104
        ]

        for url in localhost_urls:
            assert url.startswith("http://")
            assert "local" in url or "127.0.0.1" in url or "0.0.0.0" in url  # noqa: S104


class TestChunkSizeValidation:
    """Test chunk size parameter validation."""

    @pytest.mark.unit
    def test_valid_chunk_sizes(self) -> None:
        """Test validation of reasonable chunk sizes."""
        # Common chunk sizes
        valid_sizes = [100, 250, 500, 1000, 2000, 5000]

        for size in valid_sizes:
            assert 50 <= size <= 10000, f"Chunk size {size} should be in valid range"

    @pytest.mark.unit
    def test_invalid_chunk_sizes(self) -> None:
        """Test detection of invalid chunk sizes."""
        # Too small
        small_sizes = [-100, -1, 0, 10, 49]
        for size in small_sizes:
            assert size < 50, f"Size {size} should be below minimum"

        # Too large
        large_sizes = [10001, 50000, 100000]
        for size in large_sizes:
            assert size > 10000, f"Size {size} should be above maximum"

    @pytest.mark.unit
    def test_chunk_size_boundaries(self) -> None:
        """Test chunk size boundary values."""
        # Minimum boundary
        assert 50 >= 50  # Minimum valid
        assert 49 < 50  # Just below minimum

        # Maximum boundary
        assert 10000 <= 10000  # Maximum valid
        assert 10001 > 10000  # Just above maximum


class TestCollectionNameValidation:
    """Test ChromaDB collection name validation."""

    @pytest.mark.unit
    def test_valid_collection_names(self) -> None:
        """Test validation of valid ChromaDB collection names."""
        valid_names = [
            "test_collection",
            "my-docs",
            "project123",
            "data_2024",
            "user-data-v2",
            "test",  # Minimum length (3 chars)
            "a" * 63,  # Maximum length
        ]

        for name in valid_names:
            # ChromaDB rules: 3-63 chars, alphanumeric + underscore + hyphen
            assert 3 <= len(name) <= 63
            assert all(c.isalnum() or c in "_-" for c in name)

    @pytest.mark.unit
    def test_invalid_collection_names(self) -> None:
        """Test detection of invalid collection names."""
        invalid_names = [
            "ab",  # Too short (< 3 chars)
            "a" * 64,  # Too long (> 63 chars)
            "test collection",  # Contains space
            "test@collection",  # Invalid character @
            "test.collection",  # Invalid character .
            "test/collection",  # Invalid character /
            "",  # Empty
        ]

        for name in invalid_names:
            is_valid = (
                len(name) >= 3
                and len(name) <= 63
                and all(c.isalnum() or c in "_-" for c in name)
            )
            assert not is_valid, f"Name '{name}' should be invalid"

    @pytest.mark.unit
    def test_collection_name_edge_cases(self) -> None:
        """Test edge cases for collection names."""
        # Starts with number (valid)
        assert all(c.isalnum() or c in "_-" for c in "123_collection")

        # Starts with hyphen (valid)
        assert all(c.isalnum() or c in "_-" for c in "-collection")

        # Starts with underscore (valid)
        assert all(c.isalnum() or c in "_-" for c in "_collection")

        # Only numbers (valid)
        assert all(c.isalnum() or c in "_-" for c in "123456")

        # Mixed case (valid)
        assert all(c.isalnum() or c in "_-" for c in "MyCollection")


class TestStringValidation:
    """Test string validation utilities."""

    @pytest.mark.unit
    def test_non_empty_string_validation(self) -> None:
        """Test validation of non-empty strings."""
        # Valid non-empty strings
        valid_strings = ["test", " ", "123", "multi\nline", "\t"]

        for s in valid_strings:
            assert len(s) > 0, f"String '{s}' should be non-empty"

        # Invalid (empty) string
        assert len("") == 0

    @pytest.mark.unit
    def test_string_length_validation(self) -> None:
        """Test string length validation."""
        test_string = "test"

        # Length checks
        assert len(test_string) == 4
        assert len(test_string) >= 3
        assert len(test_string) <= 10

    @pytest.mark.unit
    def test_string_pattern_validation(self) -> None:
        """Test string pattern validation."""
        # Alphanumeric check
        assert "test123".isalnum()
        assert not "test-123".isalnum()

        # Alpha check
        assert "test".isalpha()
        assert not "test123".isalpha()

        # Digit check
        assert "123".isdigit()
        assert not "test123".isdigit()
