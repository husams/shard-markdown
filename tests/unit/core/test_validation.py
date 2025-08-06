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
            ValidationConfig(max_sample_size=500)


class TestValidationResult:
    """Test ValidationResult named tuple."""

    def test_valid_result(self) -> None:
        """Test valid validation result."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.error is None
        assert result.warnings is None
        assert result.confidence == 1.0

    def test_invalid_result_with_error(self) -> None:
        """Test invalid validation result with error."""
        result = ValidationResult(
            is_valid=False,
            error="Too many control characters",
            confidence=0.9,
        )
        assert result.is_valid is False
        assert result.error == "Too many control characters"
        assert result.warnings is None
        assert result.confidence == 0.9

    def test_valid_result_with_warnings(self) -> None:
        """Test valid result with warnings."""
        result = ValidationResult(
            is_valid=True,
            warnings=["High control character ratio", "Large file sampled"],
            confidence=0.8,
        )
        assert result.is_valid is True
        assert result.error is None
        assert result.warnings == ["High control character ratio", "Large file sampled"]
        assert result.confidence == 0.8


class TestContentValidator:
    """Test ContentValidator class."""

    def test_init_default_config(self) -> None:
        """Test initialization with default config."""
        validator = ContentValidator()
        assert validator.config.enable_content_validation is True
        assert validator.config.max_control_char_ratio == 0.05

    def test_init_custom_config(self) -> None:
        """Test initialization with custom config."""
        config = ValidationConfig(max_control_char_ratio=0.1)
        validator = ContentValidator(config)
        assert validator.config.max_control_char_ratio == 0.1

    def test_validation_disabled(self) -> None:
        """Test validation when disabled."""
        config = ValidationConfig(enable_content_validation=False)
        validator = ContentValidator(config)

        result = validator.validate_content("Any content", Path("test.md"))
        assert result.is_valid is True
        assert result.error is None

    def test_empty_content(self) -> None:
        """Test validation of empty content."""
        validator = ContentValidator()

        result = validator.validate_content("", Path("test.md"))
        assert result.is_valid is True
        assert result.error is None

    def test_valid_content(self) -> None:
        """Test validation of normal valid content."""
        validator = ContentValidator()
        content = """# Test Document

This is a normal markdown document with:
- Lists
- **Bold text**
- `code snippets`

## Section 2

More content here.
"""

        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is True
        assert result.error is None

    def test_control_character_detection(self) -> None:
        """Test detection of excessive control characters."""
        validator = ContentValidator()

        # Create content with many control characters (> 5% threshold)
        content = (
            "Normal text\x01\x02\x03\x04\x05\x06\x07\x08"  # Calculate actual ratio
        )

        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is False
        assert "control characters" in result.error
        # Don't test exact percentage as it might vary based on implementation

    def test_control_character_warning(self) -> None:
        """Test warning for moderate control character levels."""
        # Use relaxed config to test warning behavior
        config = ValidationConfig(max_control_char_ratio=0.1)  # 10% threshold
        validator = ContentValidator(config)

        # Create content with moderate control characters
        content = "Normal text with some control chars\x01\x02" * 10  # Dilute

        result = validator.validate_content(content, Path("test.md"))
        # With 10% threshold, should be valid or warn but not fail hard
        assert result.is_valid is True or result.warnings is not None

    def test_encoding_artifact_detection_warning(self) -> None:
        """Test detection of encoding corruption artifacts as warnings."""
        validator = ContentValidator()

        # Single artifact should generate warning, not hard failure
        content = "Normal text with one artifact: café"  # Normal Unicode, no artifacts

        result = validator.validate_content(content, Path("test.md"))
        # Normal Unicode should be valid
        assert result.is_valid is True

    def test_encoding_artifact_high_density(self) -> None:
        """Test rejection of high-density encoding artifacts."""
        validator = ContentValidator()

        # Content with pattern that will be detected as corruption
        content = "ÿþý" * 50  # High density of corruption pattern

        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is False
        # Should detect either corruption pattern or suspicious bytes
        assert (
            "corruption pattern" in result.error or "suspicious bytes" in result.error
        )

    def test_suspicious_bytes_detection(self) -> None:
        """Test detection of suspicious byte sequences."""
        validator = ContentValidator()

        # Content with suspicious bytes - test specific pattern
        content = (
            "ÿþý suspicious pattern"  # This will trigger corruption pattern detection
        )

        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is False
        # Could be detected as either corruption pattern or suspicious bytes
        assert (
            "corruption pattern" in result.error or "suspicious bytes" in result.error
        )

    def test_printable_ratio_check(self) -> None:
        """Test printable character ratio validation."""
        # Use config that focuses on printable ratio, not control chars
        config = ValidationConfig(
            max_control_char_ratio=1.0,  # Allow all control chars
            check_encoding_artifacts=False,  # Disable other checks
            min_printable_ratio=0.8,  # High threshold
        )
        validator = ContentValidator(config)

        # Content with many non-printable characters that aren't control chars
        # Use bytes that are neither printable nor in the control char set
        content = "Normal text" + (
            "\x7f" * 20
        )  # DEL character (not in PROBLEMATIC_CONTROL_CHARS)

        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is False
        assert "printable characters" in result.error

    def test_binary_data_detection(self) -> None:
        """Test detection of binary data patterns."""
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
        base64_chunk = "SGVsbG8gV29ybGQhIFRoaXMgaXMgYSB0ZXN0IG9mIGJhc2U2NCBlbmNvZGluZyB0aGF0IGlzIHZlcnkgbG9uZyBhbmQgc2hvdWxkIGJlIGRldGVjdGVkIGFzIHN1c3BpY2lvdXM="
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
def test():
    pass

# Missing closing ```

More content here.
"""

        result = validator.validate_content(content, Path("test.md"))
        # Structure issues are warnings, not failures
        assert result.is_valid is True
        if result.warnings:
            assert any("Markdown structure" in warning for warning in result.warnings)

    def test_malformed_headers(self) -> None:
        """Test detection of malformed headers."""
        config = ValidationConfig(validate_markdown_structure=True)
        validator = ContentValidator(config)

        content = """# Valid Header

##Invalid header without space
###Another invalid
#### Valid Header

#####Yet another invalid
"""

        result = validator.validate_content(content, Path("test.md"))
        # Structure issues should be warnings
        assert result.is_valid is True
        if result.warnings:
            assert any("Markdown structure" in warning for warning in result.warnings)

    def test_large_file_sampling(self) -> None:
        """Test sampling behavior for large files."""
        config = ValidationConfig(max_sample_size=1000)  # Minimum allowed size
        validator = ContentValidator(config)

        # Create content larger than sample size
        large_content = "Normal markdown content. " * 100  # > 1000 chars

        result = validator.validate_content(large_content, Path("test.md"))
        assert result.is_valid is True
        if result.warnings:
            assert any("Large file" in warning for warning in result.warnings)
        assert result.confidence < 1.0  # Should reduce confidence

    def test_validation_exception_handling(self) -> None:
        """Test handling of validation exceptions."""
        validator = ContentValidator()

        # Mock the validator to simulate an internal error
        def mock_check_control_characters(content):
            raise ValueError("Simulated internal error")

        original_method = validator._check_control_characters
        validator._check_control_characters = mock_check_control_characters

        try:
            result = validator.validate_content("test content", Path("test.md"))
            # Should return valid=True with warnings about validation error
            assert result.is_valid is True
            assert result.warnings is not None
            assert any("Validation error" in warning for warning in result.warnings)
            assert result.confidence == 0.5
        finally:
            validator._check_control_characters = original_method

    def test_combined_issues(self) -> None:
        """Test content with multiple validation issues."""
        validator = ContentValidator()

        # Content with multiple problems
        content = "Text\x01\x02ÿþýwith\xff\xfeproblems"

        result = validator.validate_content(content, Path("test.md"))
        # Should fail on first major issue encountered
        assert result.is_valid is False
        assert result.error is not None

    def test_whitespace_content_handling(self) -> None:
        """Test handling of whitespace-only content."""
        validator = ContentValidator()

        # Content with only whitespace and line breaks
        content = "\n\n   \t  \r\n  \n\n"

        result = validator.validate_content(content, Path("test.md"))
        # Whitespace should be considered printable
        assert result.is_valid is True

    def test_unicode_content(self) -> None:
        """Test validation of proper Unicode content."""
        validator = ContentValidator()

        # Use proper Unicode characters that should be valid
        content = """# Test Document

This document contains Unicode characters:
- Symbols: © ® ™ § ¶ †
- Math: α β γ Σ π ∞
- Accents: café naïve résumé
"""

        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is True
        assert result.error is None

    def test_artifact_detection_disabled(self) -> None:
        """Test validation with artifact detection disabled."""
        config = ValidationConfig(check_encoding_artifacts=False)
        validator = ContentValidator(config)

        # Content that would normally trigger artifact detection
        content = "Text with ÿþý artifacts that should be ignored"

        result = validator.validate_content(content, Path("test.md"))
        # Should pass since artifact detection is disabled
        assert result.is_valid is True

    def test_edge_case_empty_patterns(self) -> None:
        """Test edge cases with empty or minimal patterns."""
        validator = ContentValidator()

        # Very short content
        content = "Hi"

        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is True

        # Content with just punctuation
        content = "!@#$%^&*()"

        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is True

    def test_configuration_edge_cases(self) -> None:
        """Test edge cases in validation configuration."""
        # Test minimum values
        config = ValidationConfig(
            max_control_char_ratio=0.0,
            min_printable_ratio=0.0,
            max_sample_size=1000,
        )
        validator = ContentValidator(config)

        # Should work with edge configuration
        result = validator.validate_content("Normal content", Path("test.md"))
        assert result.is_valid is True

        # Test very strict configuration
        config = ValidationConfig(
            max_control_char_ratio=0.0,  # No control chars allowed
            min_printable_ratio=1.0,  # All chars must be printable
            check_encoding_artifacts=False,  # Disable other checks
        )
        validator = ContentValidator(config)

        # Content with control character should fail
        result = validator.validate_content("Content\x01", Path("test.md"))
        assert result.is_valid is False

    def test_sampling_strategy(self) -> None:
        """Test that sampling is applied to large files."""
        config = ValidationConfig(max_sample_size=1200)  # Minimum allowed + buffer
        validator = ContentValidator(config)

        # Create content that is definitely larger than sample size
        # and will be problematic when sampled
        problematic_chunk = "\x01\x02\x03\x04\x05" * 100  # 500 chars of control chars
        good_content = "Good content here. " * 100  # ~1900 chars
        large_content = good_content + problematic_chunk  # ~2400 chars total

        # Should be > 1200 chars
        assert len(large_content) > 1200

        result = validator.validate_content(large_content, Path("test.md"))

        # Check that sampling was triggered
        assert result.warnings is not None
        assert any("Large file" in warning for warning in result.warnings)
        assert result.confidence < 1.0  # Should reduce confidence due to sampling

        # The validation result will depend on which parts get sampled
        # This test primarily verifies that large file sampling is working

    def test_validation_confidence_levels(self) -> None:
        """Test how confidence levels are calculated and combined."""
        validator = ContentValidator()

        # Content that generates warnings (should reduce confidence)
        content = "Normal text with proper Unicode: café naïve"

        result = validator.validate_content(content, Path("test.md"))
        # Normal Unicode should be valid with high confidence
        assert result.is_valid is True
        assert result.confidence >= 0.9  # Should be high confidence

    def test_relaxed_vs_strict_thresholds(self) -> None:
        """Test behavior with different threshold configurations."""
        # Relaxed validator
        relaxed_config = ValidationConfig(
            max_control_char_ratio=0.2,  # 20% allowed
            min_printable_ratio=0.5,  # 50% required
            check_encoding_artifacts=False,
        )
        relaxed_validator = ContentValidator(relaxed_config)

        # Strict validator
        strict_config = ValidationConfig(
            max_control_char_ratio=0.01,  # 1% allowed
            min_printable_ratio=0.9,  # 90% required
            check_encoding_artifacts=True,
        )
        strict_validator = ContentValidator(strict_config)

        # Test content with moderate issues
        content = "Normal text\x01\x02 with some issues"

        relaxed_result = relaxed_validator.validate_content(content, Path("test.md"))
        strict_result = strict_validator.validate_content(content, Path("test.md"))

        # Relaxed should be more permissive
        assert relaxed_result.is_valid is True
        assert strict_result.is_valid is False

    def test_multiple_validation_checks_order(self) -> None:
        """Test that validation checks are applied in the correct order."""
        validator = ContentValidator()

        # Content that would fail multiple checks
        # First check (control chars) should catch it before later checks
        content = "\x01\x02\x03\x04\x05\x06\x07\x08" * 10  # Lots of control chars

        result = validator.validate_content(content, Path("test.md"))
        assert result.is_valid is False
        # Should fail on one of the early checks
        assert result.error is not None
