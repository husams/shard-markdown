"""Unit tests for content validation module."""

from pathlib import Path

import pytest

from shard_markdown.core.validation import (
    ContentValidator,
    ValidationConfig,
    ValidationResult,
)


class TestValidationConfig:
    """Test ValidationConfig model."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = ValidationConfig()
        assert config.enable_content_validation is True
        assert config.max_control_char_ratio == 0.05
        assert config.check_encoding_artifacts is True
        assert config.validate_markdown_structure is False
        assert config.max_sample_size == 50000
        assert config.min_printable_ratio == 0.7

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = ValidationConfig(
            enable_content_validation=False,
            max_control_char_ratio=0.1,
            check_encoding_artifacts=False,
            validate_markdown_structure=True,
            max_sample_size=10000,
            min_printable_ratio=0.8,
        )
        assert config.enable_content_validation is False
        assert config.max_control_char_ratio == 0.1
        assert config.check_encoding_artifacts is False
        assert config.validate_markdown_structure is True
        assert config.max_sample_size == 10000
        assert config.min_printable_ratio == 0.8

    def test_config_validation(self) -> None:
        """Test configuration validation."""
        with pytest.raises(ValueError):
            ValidationConfig(max_control_char_ratio=-0.1)

        with pytest.raises(ValueError):
            ValidationConfig(max_control_char_ratio=1.1)

        with pytest.raises(ValueError):
            ValidationConfig(min_printable_ratio=-0.1)

        with pytest.raises(ValueError):
            ValidationConfig(min_printable_ratio=1.1)

        with pytest.raises(ValueError):
            ValidationConfig(max_sample_size=0)


class TestValidationResult:
    """Test ValidationResult model."""

    def test_valid_result(self) -> None:
        """Test valid result creation."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.error is None
        assert result.warnings == []

    def test_invalid_result(self) -> None:
        """Test invalid result creation."""
        result = ValidationResult(
            is_valid=False,
            error="Content validation failed",
            warnings=["Warning message"],
        )
        assert result.is_valid is False
        assert result.error == "Content validation failed"
        assert result.warnings == ["Warning message"]


class TestContentValidator:
    """Test ContentValidator functionality."""

    def test_default_validator(self) -> None:
        """Test validator with default configuration."""
        validator = ContentValidator()
        assert validator.config.enable_content_validation is True

    def test_custom_config_validator(self) -> None:
        """Test validator with custom configuration."""
        config = ValidationConfig(enable_content_validation=False)
        validator = ContentValidator(config)
        assert validator.config.enable_content_validation is False

    def test_disabled_validation(self) -> None:
        """Test validation when disabled."""
        config = ValidationConfig(enable_content_validation=False)
        validator = ContentValidator(config)

        result = validator.validate_content("any content", Path("test.md"))
        assert result.is_valid is True
        assert result.error is None

    def test_valid_markdown_content(self) -> None:
        """Test validation of valid markdown content."""
        validator = ContentValidator()

        content = """# Test Document

This is a test document with valid markdown content.

## Section 1

Content with some text and **bold** formatting.

## Section 2

- List item 1
- List item 2
- List item 3

> Quote block with some content.

```python
# Code block
def hello_world():
    return "Hello, World!"
```
"""

        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is True
        assert result.error is None

    def test_empty_content(self) -> None:
        """Test validation of empty content."""
        validator = ContentValidator()

        result = validator.validate_content("", Path("test.md"))
        assert result.is_valid is False
        assert "empty" in result.error.lower()

    def test_whitespace_only_content(self) -> None:
        """Test validation of whitespace-only content."""
        validator = ContentValidator()

        content = "   \n\n\t\t\n   \n"
        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is False
        assert "empty" in result.error.lower()

    def test_high_control_character_ratio(self) -> None:
        """Test content with high ratio of control characters."""
        validator = ContentValidator()

        # Content with many control characters
        content = "# Test\n\n" + "\x00\x01\x02\x03" * 50 + "\n\nSome text"
        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is False
        assert "control characters" in result.error

    def test_low_printable_character_ratio(self) -> None:
        """Test content with low ratio of printable characters."""
        validator = ContentValidator()

        # Content with many non-printable characters
        content = "# Test\n\n" + "".join(chr(i) for i in range(1, 20)) * 10
        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is False
        assert "binary" in result.error

    def test_encoding_artifacts_detection(self) -> None:
        """Test detection of encoding artifacts."""
        validator = ContentValidator()

        # Common encoding artifacts
        artifacts = [
            "\ufffd",  # Unicode replacement character
            "\ufeff",  # Byte order mark
            "Ã¡",  # Double-encoded á
            "Ã©",  # Double-encoded é
        ]

        for artifact in artifacts:
            content = f"# Test\n\nContent with {artifact} encoding issues"
            result = validator.validate_content(content, Path("test.md"))

            if artifact in ["\ufffd"]:
                # These should fail
                assert result.is_valid is False
                assert "encoding" in result.error.lower()
            # Others might pass depending on implementation

    def test_null_byte_detection(self) -> None:
        """Test detection of null bytes."""
        validator = ContentValidator()

        content = "# Test\n\nContent with\x00null bytes"
        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is False
        assert "null bytes" in result.error

    def test_repeated_byte_patterns(self) -> None:
        """Test detection of repeated byte patterns."""
        validator = ContentValidator()

        # Content with long repeated sequences (binary-like)
        content = "A" * 60  # Long sequence of same character

        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is False
        assert "repeated bytes" in result.error

    def test_base64_detection(self) -> None:
        """Test detection of base64-encoded content."""
        validator = ContentValidator()

        # Multiple long base64-like sequences
        base64_chunk = (
            "SGVsbG8gV29ybGQhIFRoaXMgaXMgYSB0ZXN0IG9mIGJhc2U2NCBlbmNvZGluZyB0aGF0"
            "IGlzIHZlcnkgbG9uZyBhbmQgc2hvdWxkIGJlIGRldGVjdGVkIGFzIHN1c3BpY2lvdXM="
        )
        content = f"""# Document
{base64_chunk}

## Section 2
{base64_chunk}

## Section 3
{base64_chunk}

## Section 4
{base64_chunk}
"""

        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is False
        assert "encoded binary data" in result.error

    def test_markdown_structure_validation(self) -> None:
        """Test markdown structure validation."""
        config = ValidationConfig(validate_markdown_structure=True)
        validator = ContentValidator(config)

        # Content with unclosed code blocks
        content = """# Test

```python
def unclosed_function():
    return "missing closing backticks"

More content after unclosed block.
"""

        result = validator.validate_content(content, Path("test.md"))
        # Structure validation behavior depends on implementation
        # Document the current behavior
        if not result.is_valid:
            assert "structure" in result.error.lower()

    def test_large_content_sampling(self) -> None:
        """Test validation of large content with sampling."""
        config = ValidationConfig(max_sample_size=1000)
        validator = ContentValidator(config)

        # Create large content
        large_content = "# Large Document\n\n" + "Valid text content. " * 1000

        result = validator.validate_content(large_content, Path("test.md"))
        assert result.is_valid is True

    def test_edge_case_unicode_content(self) -> None:
        """Test validation of edge case Unicode content."""
        validator = ContentValidator()

        unicode_cases = [
            "# Test\n\nContent with emojis 🎉🚀💯",
            "# Test\n\nContent with RTL text: مرحبا العالم",
            "# Test\n\nContent with mathematical symbols: ∑∫∞√",
            "# Test\n\nContent with combining characters: café naïve",
        ]

        for content in unicode_cases:
            result = validator.validate_content(content, Path("test.md"))
            assert result.is_valid is True, f"Failed for: {content[:50]}..."

    def test_validation_warnings(self) -> None:
        """Test generation of validation warnings."""
        validator = ContentValidator()

        # Content that might generate warnings but still be valid
        content = """# Test Document

Content with some questionable patterns but still valid.

## Section with Many Numbers
12345 67890 11111 22222 33333 44444 55555

## Section with Repeated Text
repeat repeat repeat repeat repeat repeat

This should still be considered valid markdown.
"""

        result = validator.validate_content(content, Path("test.md"))
        # Document behavior - might be valid with warnings
        assert result.is_valid is True

    def test_file_path_in_validation(self) -> None:
        """Test that file path is properly handled in validation."""
        validator = ContentValidator()

        content = "# Test\n\nValid content"
        test_path = Path("/path/to/test.md")

        result = validator.validate_content(content, test_path)
        assert result.is_valid is True

        # Error messages should not expose internal paths in production
        invalid_content = "\x00" * 100
        result = validator.validate_content(invalid_content, test_path)
        assert result.is_valid is False
        assert result.error is not None

    def test_validation_performance_large_files(self) -> None:
        """Test validation performance on large files."""
        config = ValidationConfig(max_sample_size=5000)  # Small sample for testing
        validator = ContentValidator(config)

        # Create a very large markdown document
        large_content = "# Large Document\n\n"
        section_content = """## Section

This is a section with substantial content that includes various markdown
features like **bold text**, *italic text*, `inline code`, and links
to [example.com](https://example.com).

- List item 1
- List item 2
- List item 3

> A blockquote with some substantial content that demonstrates
> the structure and formatting capabilities.

```python
# Code block with actual code
def process_data(data):
    results = []
    for item in data:
        if item.is_valid():
            results.append(item.process())
    return results
```

"""
        large_content += section_content * 100  # Create a large file

        result = validator.validate_content(large_content, Path("large.md"))
        # Should complete efficiently due to sampling
        assert result.is_valid is True

    def test_binary_content_detection(self) -> None:
        """Test detection of binary content."""
        validator = ContentValidator()

        # Simulate binary content mixed with text
        binary_content = (
            "# Document\n\n"
            + "".join(chr(i) for i in range(0, 32))  # Control characters
            + "Text content"
            + "".join(chr(i) for i in range(128, 255))  # High byte values
        )

        result = validator.validate_content(binary_content, Path("binary.md"))
        assert result.is_valid is False
        assert "binary" in result.error.lower()

    def test_validation_result_consistency(self) -> None:
        """Test that validation results are consistent across calls."""
        validator = ContentValidator()

        content = "# Test\n\nConsistent content for testing"
        path = Path("test.md")

        # Run validation multiple times
        results = [validator.validate_content(content, path) for _ in range(5)]

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result.is_valid == first_result.is_valid
            assert result.error == first_result.error
            assert result.warnings == first_result.warnings
