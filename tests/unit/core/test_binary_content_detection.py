"""Tests for binary content detection and handling."""

from pathlib import Path

import pytest

from shard_markdown.config.settings import ProcessingConfig
from shard_markdown.core.models import ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor
from shard_markdown.core.validation import ContentValidator, ValidationConfig


class TestBinaryContentDetection:
    """Test suite for binary content detection."""

    @pytest.fixture
    def chunking_config(self) -> ChunkingConfig:
        """Create basic chunking configuration."""
        return ChunkingConfig(
            chunk_size=500,
            overlap=50,
            method="structure",
            respect_boundaries=True,
        )

    @pytest.fixture
    def validator(self) -> ContentValidator:
        """Create content validator for testing."""
        return ContentValidator(ValidationConfig())

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create processor for testing."""
        return DocumentProcessor(chunking_config)

    @pytest.fixture
    def strict_processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create strict processor for testing."""
        config = ProcessingConfig(strict_validation=True)
        return DocumentProcessor(chunking_config, config)

    def test_detect_png_binary_content(self, validator: ContentValidator) -> None:
        """Test detection of PNG binary content."""
        # PNG file signature
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"fake png data" * 100

        assert validator.detect_binary_content(png_bytes) is True

    def test_detect_jpeg_binary_content(self, validator: ContentValidator) -> None:
        """Test detection of JPEG binary content."""
        # JPEG file signature
        jpeg_bytes = b"\xff\xd8\xff" + b"fake jpeg data" * 100

        assert validator.detect_binary_content(jpeg_bytes) is True

    def test_detect_pdf_binary_content(self, validator: ContentValidator) -> None:
        """Test detection of PDF binary content."""
        # PDF file signature
        pdf_bytes = b"%PDF-1.4" + b"fake pdf data" * 100

        assert validator.detect_binary_content(pdf_bytes) is True

    def test_detect_exe_binary_content(self, validator: ContentValidator) -> None:
        """Test detection of executable binary content."""
        # Windows PE file signature
        exe_bytes = b"MZ" + b"fake exe data" * 100

        assert validator.detect_binary_content(exe_bytes) is True

    def test_detect_zip_binary_content(self, validator: ContentValidator) -> None:
        """Test detection of ZIP binary content."""
        # ZIP file signature
        zip_bytes = b"PK\x03\x04" + b"fake zip data" * 100

        assert validator.detect_binary_content(zip_bytes) is True

    def test_detect_null_bytes_binary_content(
        self, validator: ContentValidator
    ) -> None:
        """Test detection of binary content with many null bytes."""
        # Content with high ratio of null bytes
        null_bytes = b"some text\x00\x00\x00\x00" * 50

        assert validator.detect_binary_content(null_bytes) is True

    def test_detect_high_non_printable_binary_content(
        self, validator: ContentValidator
    ) -> None:
        """Test detection of binary content with high non-printable byte ratio."""
        # Content with many non-printable bytes
        non_printable_bytes = bytes(range(0, 20)) * 20 + b"some text"

        assert validator.detect_binary_content(non_printable_bytes) is True

    def test_valid_text_not_detected_as_binary(
        self, validator: ContentValidator
    ) -> None:
        """Test that valid text content is not detected as binary."""
        # Regular markdown text
        text_bytes = """# Test Document

This is a normal markdown document with regular text content.

## Section 1

Content here with some special chars: áéíóú ñ €£¥

```python
# Code block
def hello_world():
    return "Hello, World!"
```

- List item 1
- List item 2
- List item 3

> This is a blockquote with normal text.

The end.
""".encode()

        assert validator.detect_binary_content(text_bytes) is False

    def test_empty_content_not_binary(self, validator: ContentValidator) -> None:
        """Test that empty content is not detected as binary."""
        assert validator.detect_binary_content(b"") is False

    def test_process_png_file_fails(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that PNG files are rejected by the processor."""
        png_file = temp_dir / "test.png"
        # Create a fake PNG file
        png_data = b"\x89PNG\r\n\x1a\n" + b"fake png data" * 100
        png_file.write_bytes(png_data)

        result = processor.process_document(png_file)

        assert result.success is False
        assert result.chunks_created == 0
        assert result.error is not None
        assert "binary data" in result.error.lower()
        assert "unsupported content type" in result.error.lower()

    def test_process_jpeg_file_fails(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that JPEG files are rejected by the processor."""
        jpeg_file = temp_dir / "test.jpg"
        # Create a fake JPEG file
        jpeg_data = b"\xff\xd8\xff" + b"fake jpeg data" * 100
        jpeg_file.write_bytes(jpeg_data)

        result = processor.process_document(jpeg_file)

        assert result.success is False
        assert result.chunks_created == 0
        assert result.error is not None
        assert "binary data" in result.error.lower()
        assert "unsupported content type" in result.error.lower()

    def test_process_pdf_file_fails(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that PDF files are rejected by the processor."""
        pdf_file = temp_dir / "test.pdf"
        # Create a fake PDF file
        pdf_data = b"%PDF-1.4" + b"fake pdf data" * 100
        pdf_file.write_bytes(pdf_data)

        result = processor.process_document(pdf_file)

        assert result.success is False
        assert result.chunks_created == 0
        assert result.error is not None
        assert "binary data" in result.error.lower()
        assert "unsupported content type" in result.error.lower()

    def test_process_exe_file_fails(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that executable files are rejected by the processor."""
        exe_file = temp_dir / "test.exe"
        # Create a fake executable file
        exe_data = b"MZ" + b"fake exe data" * 100
        exe_file.write_bytes(exe_data)

        result = processor.process_document(exe_file)

        assert result.success is False
        assert result.chunks_created == 0
        assert result.error is not None
        assert "binary data" in result.error.lower()
        assert "unsupported content type" in result.error.lower()

    def test_process_binary_fails_strict_mode(
        self, strict_processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that binary files fail in strict mode."""
        binary_file = temp_dir / "test.bin"
        # Create a binary file with mixed content
        binary_data = b"\x89PNG\r\n\x1a\n" + b"binary content" * 50
        binary_file.write_bytes(binary_data)

        result = strict_processor.process_document(binary_file)

        assert result.success is False
        assert result.chunks_created == 0
        assert result.error is not None
        assert "binary data" in result.error.lower()

    def test_process_binary_fails_graceful_mode(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that binary files fail even in graceful mode."""
        binary_file = temp_dir / "test.bin"
        # Create a binary file with mixed content
        binary_data = b"\xff\xd8\xff" + b"binary content" * 50
        binary_file.write_bytes(binary_data)

        result = processor.process_document(binary_file)

        # Binary files should fail even in graceful mode
        assert result.success is False
        assert result.chunks_created == 0
        assert result.error is not None
        assert "binary data" in result.error.lower()

    def test_binary_content_string_validation(
        self, validator: ContentValidator
    ) -> None:
        """Test string-based binary content validation."""
        # Content with high control character ratio should fail
        binary_string_content = (
            "# Document\n\n" + "".join(chr(i) for i in range(0, 32)) + "text content"
        )

        result = validator.validate_content(binary_string_content, Path("test.md"))

        assert result.is_valid is False
        assert result.error is not None
        assert "binary-like content" in result.error.lower()

    def test_high_control_char_ratio_detected(
        self, validator: ContentValidator
    ) -> None:
        """Test detection of high control character ratio."""
        # Create content with many control characters
        control_content = (
            "# Test\n\n" + "\x00\x01\x02\x03\x04\x05" * 20 + "\n\nSome text"
        )

        result = validator.validate_content(control_content, Path("test.md"))

        assert result.is_valid is False
        assert result.error is not None
        assert "binary-like content" in result.error.lower()
        assert "control characters" in result.error.lower()

    def test_low_printable_ratio_detected(self, validator: ContentValidator) -> None:
        """Test detection of low printable character ratio."""
        # Create content with many DEL characters (chr(127)) which are non-printable
        # but won't trigger control char check (since 127 is not < 32) or
        # suspicious bytes
        non_printable_content = (
            "# Test\n\n" + chr(127) * 200 + "Some text"  # High ratio of DEL chars
        )

        result = validator.validate_content(non_printable_content, Path("test.md"))

        assert result.is_valid is False
        assert result.error is not None
        assert "binary data" in result.error.lower()
        assert "printable characters" in result.error.lower()

    def test_repeated_bytes_pattern_detected(self, validator: ContentValidator) -> None:
        """Test detection of repeated byte patterns."""
        # Create content with long repeated sequences
        repeated_content = "A" * 60  # Long sequence of same character

        result = validator.validate_content(repeated_content, Path("test.md"))

        assert result.is_valid is False
        assert result.error is not None
        assert "binary data" in result.error.lower()
        assert "repeated bytes" in result.error.lower()

    def test_base64_encoded_content_detected(self, validator: ContentValidator) -> None:
        """Test detection of base64-encoded content."""
        # Create content with multiple long base64-like sequences
        base64_chunk = (
            "SGVsbG8gV29ybGQhIFRoaXMgaXMgYSB0ZXN0IG9mIGJhc2U2NCBlbmNvZGluZyB0aGF0"
            "IGlzIHZlcnkgbG9uZyBhbmQgc2hvdWxkIGJlIGRldGVjdGVkIGFzIHN1c3BpY2lvdXM="
        )
        content = (
            f"# Document\n{base64_chunk}\n\n"
            f"## Section 2\n{base64_chunk}\n\n"
            f"## Section 3\n{base64_chunk}\n\n"
            f"## Section 4\n{base64_chunk}\n"
        )

        result = validator.validate_content(content, Path("test.md"))

        assert result.is_valid is False
        assert result.error is not None
        assert "encoded binary data" in result.error.lower()

    def test_valid_markdown_not_detected_as_binary(
        self, validator: ContentValidator
    ) -> None:
        """Test that valid markdown is not detected as binary."""
        valid_markdown = """# Test Document

This is a valid markdown document with normal content.

## Features

- Lists work fine
- **Bold** and *italic* text
- `Code snippets`

> Blockquotes are supported

```python
# Code blocks are fine
def hello():
    return "world"
```

### Links and Images

[Link text](https://example.com)

Regular text with punctuation: Hello, world! How are you?

Unicode characters work: café, naïve, résumé, 中文, العربية

Mathematical symbols: α, β, γ, ∑, ∫, ∞

Emoji: 🎉 🚀 💯 🔥

The end.
"""

        result = validator.validate_content(valid_markdown, Path("test.md"))

        assert result.is_valid is True
        assert result.error is None
