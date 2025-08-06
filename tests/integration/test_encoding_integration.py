"""Integration tests for advanced encoding detection with DocumentProcessor."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from shard_markdown.config.settings import ProcessingConfig
from shard_markdown.core.encoding import EncodingDetectorConfig
from shard_markdown.core.models import ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor


class TestEncodingDetectionIntegration:
    """Integration tests for encoding detection with document processing."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def processor_with_detection(self) -> DocumentProcessor:
        """Create processor with encoding detection enabled."""
        chunking_config = ChunkingConfig(chunk_size=500, overlap=100)
        processing_config = ProcessingConfig(
            enable_encoding_detection=True,
            encoding_detection=EncodingDetectorConfig(
                min_confidence=0.7,
                cache_size=10,
            ),
        )
        return DocumentProcessor(chunking_config, processing_config)

    @pytest.fixture
    def processor_without_detection(self) -> DocumentProcessor:
        """Create processor with encoding detection disabled."""
        chunking_config = ChunkingConfig(chunk_size=500, overlap=100)
        processing_config = ProcessingConfig(
            enable_encoding_detection=False,
        )
        return DocumentProcessor(chunking_config, processing_config)

    def test_utf8_document_processing(
        self, processor_with_detection: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing UTF-8 document with detection enabled."""
        content = """# UTF-8 Document

This document contains unicode characters: café, naïve, résumé.

## Section with Emoji

Welcome to the 🌟 advanced encoding system! 🚀

## Code Example

```python
def process_file(path: str) -> str:
    return "Processed successfully!"
```

This should be chunked properly with UTF-8 encoding detection.
"""

        utf8_file = temp_dir / "utf8_test.md"
        utf8_file.write_text(content, encoding="utf-8")

        result = processor_with_detection.process_document(utf8_file, "utf8-test")

        assert result.success is True
        assert result.chunks_created > 0
        assert result.error is None

        # Check encoding stats
        encoding_stats = processor_with_detection.get_encoding_stats()
        assert encoding_stats["detections"] >= 1

    def test_latin1_document_processing(
        self, processor_with_detection: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing Latin-1 document with detection."""
        # Content with Latin-1 specific characters
        content = """# Document en Español

Este documento contiene caracteres especiales: café, niño, señor.

## Sección de Ejemplo

Los caracteres acentuados son comunes en español:
- José, María, Ángel
- Comunicación, información, educación

## Notas

El sistema debe detectar automáticamente la codificación ISO-8859-1.
"""

        latin1_file = temp_dir / "latin1_test.md"
        latin1_file.write_text(content, encoding="iso-8859-1")

        result = processor_with_detection.process_document(latin1_file, "latin1-test")

        assert result.success is True
        assert result.chunks_created > 0
        assert result.error is None

    def test_encoding_detection_vs_fallback_comparison(
        self,
        processor_with_detection: DocumentProcessor,
        processor_without_detection: DocumentProcessor,
        temp_dir: Path,
    ) -> None:
        """Compare processing with and without encoding detection."""
        # Create a file that would benefit from detection
        content = """# Mixed Encoding Test

This file has some tricky characters that might cause issues
with simple fallback: café, naïve, résumé, piñata.

## Section Two

More content to ensure proper chunking with encoding detection.
The advanced system should handle this better than simple fallback.
"""

        test_file = temp_dir / "mixed_encoding.md"
        test_file.write_text(content, encoding="utf-8")

        # Process with detection
        result_with_detection = processor_with_detection.process_document(
            test_file, "with-detection"
        )

        # Process without detection
        result_without_detection = processor_without_detection.process_document(
            test_file, "without-detection"
        )

        # Both should succeed for UTF-8, but with detection should have better stats
        assert result_with_detection.success is True
        assert result_without_detection.success is True

        # Check that detection was actually used
        encoding_stats = processor_with_detection.get_encoding_stats()
        assert encoding_stats["detections"] >= 1

        # Without detection should show disabled
        no_detection_stats = processor_without_detection.get_encoding_stats()
        assert no_detection_stats["encoding_detection"] == "disabled"

    def test_corrupted_encoding_handling(
        self, processor_with_detection: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of files with encoding corruption."""
        # Create a file with intentional corruption
        corrupted_file = temp_dir / "corrupted.md"

        # Write bytes that would be invalid UTF-8
        with open(corrupted_file, "wb") as f:
            f.write(b"# Corrupted File\n\n")
            f.write(b"This has invalid UTF-8: \xff\xfe\xfd")
            f.write(b"\n\nMore content after corruption.")

        result = processor_with_detection.process_document(corrupted_file, "corrupted")

        # Should fail gracefully
        assert result.success is False
        assert "encoding" in result.error.lower()

    def test_empty_file_with_detection(
        self, processor_with_detection: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test empty file handling with detection enabled."""
        empty_file = temp_dir / "empty.md"
        empty_file.write_text("", encoding="utf-8")

        result = processor_with_detection.process_document(empty_file, "empty-test")

        # Should handle empty file gracefully
        assert result.success is False  # Empty files are considered failures
        assert result.chunks_created == 0
        assert "empty" in result.error.lower()

    def test_large_file_sampling(
        self, processor_with_detection: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that large files are properly sampled for encoding detection."""
        # Create a large file
        base_content = """# Large Document Section

This section contains a reasonable amount of text to test encoding detection
on larger files. The system should sample only part of the file for detection
to maintain performance.

## Subsection with Unicode

Here we have some unicode content: café, naïve, résumé, piñata.
This helps ensure the sample contains enough variety for detection.

"""

        # Repeat to make it large
        large_content = base_content * 200  # Should exceed sample size

        large_file = temp_dir / "large_file.md"
        large_file.write_text(large_content, encoding="utf-8")

        result = processor_with_detection.process_document(large_file, "large-test")

        assert result.success is True
        assert result.chunks_created > 0

        # Verify detection was used
        encoding_stats = processor_with_detection.get_encoding_stats()
        assert encoding_stats["detections"] >= 1

    def test_encoding_detection_caching(
        self, processor_with_detection: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that encoding detection results are properly cached."""
        content = """# Cached Detection Test

This file will be processed multiple times to test caching.
Content includes: café, naïve, résumé for encoding variety.
"""

        cached_file = temp_dir / "cached_detection.md"
        cached_file.write_text(content, encoding="utf-8")

        # Process file multiple times
        result1 = processor_with_detection.process_document(cached_file, "cache-1")
        result2 = processor_with_detection.process_document(cached_file, "cache-2")

        assert result1.success is True
        assert result2.success is True

        # Check cache statistics
        encoding_stats = processor_with_detection.get_encoding_stats()
        assert (
            encoding_stats["cache_hits"] >= 1
        )  # Second processing should be cache hit

    def test_security_whitelist_enforcement(self, temp_dir: Path) -> None:
        """Test that security whitelist is enforced."""
        # Create processor with strict security settings
        chunking_config = ChunkingConfig(chunk_size=500)
        processing_config = ProcessingConfig(
            enable_encoding_detection=True,
            encoding_detection=EncodingDetectorConfig(
                block_suspicious=True,
                allowed_encodings={"utf-8", "ascii"},  # Very restrictive
            ),
        )
        strict_processor = DocumentProcessor(chunking_config, processing_config)

        test_file = temp_dir / "security_test.md"
        test_file.write_text("# Security Test\n\nContent", encoding="utf-8")

        # Mock chardet to return a suspicious encoding
        with patch("chardet.detect") as mock_detect:
            mock_detect.return_value = {
                "encoding": "suspicious-encoding",
                "confidence": 0.9,
                "language": None,
            }

            result = strict_processor.process_document(test_file, "security")

            # Should fail due to security restriction
            assert result.success is False
            assert "whitelist" in result.error.lower()

    def test_confidence_threshold_handling(self, temp_dir: Path) -> None:
        """Test handling of low-confidence detection results."""
        # Create processor with high confidence threshold
        chunking_config = ChunkingConfig(chunk_size=500)
        processing_config = ProcessingConfig(
            enable_encoding_detection=True,
            encoding_detection=EncodingDetectorConfig(
                min_confidence=0.95,  # Very high threshold
            ),
        )
        high_confidence_processor = DocumentProcessor(
            chunking_config, processing_config
        )

        test_file = temp_dir / "confidence_test.md"
        test_file.write_text("# Confidence Test\n\nContent", encoding="utf-8")

        # Mock chardet to return low confidence
        with patch("chardet.detect") as mock_detect:
            mock_detect.return_value = {
                "encoding": "utf-8",
                "confidence": 0.5,  # Below threshold
                "language": None,
            }

            result = high_confidence_processor.process_document(test_file, "confidence")

            # Should still succeed using fallback chain
            assert result.success is True
            assert result.chunks_created > 0

    def test_batch_processing_with_encoding_detection(
        self, processor_with_detection: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test batch processing with encoding detection."""
        # Create multiple files with different encodings
        files = []

        # UTF-8 file
        utf8_file = temp_dir / "batch_utf8.md"
        utf8_file.write_text("# UTF-8\n\nContent with café", encoding="utf-8")
        files.append(utf8_file)

        # ASCII file
        ascii_file = temp_dir / "batch_ascii.md"
        ascii_file.write_text("# ASCII\n\nPlain ASCII content", encoding="ascii")
        files.append(ascii_file)

        # Latin-1 file
        latin1_file = temp_dir / "batch_latin1.md"
        latin1_file.write_text("# Latin-1\n\nContent with café", encoding="iso-8859-1")
        files.append(latin1_file)

        batch_result = processor_with_detection.process_batch(files, "batch-encoding")

        assert (
            batch_result.successful_files >= 2
        )  # At least UTF-8 and ASCII should work
        assert batch_result.total_chunks > 0

        # Check that detection was used for all files
        encoding_stats = processor_with_detection.get_encoding_stats()
        assert encoding_stats["detections"] >= len(files)

    def test_encoding_validation_integration(
        self, processor_with_detection: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test integration of encoding validation with content validation."""
        # Create file that might have encoding issues
        problematic_file = temp_dir / "validation_test.md"

        # Write content that could be problematic
        with open(problematic_file, "wb") as f:
            f.write(b"# Test Document\n\n")
            f.write("Content with unicode: café".encode())
            f.write(b"\n\n")
            # Add some potential corruption
            f.write(b"End of document")

        result = processor_with_detection.process_document(
            problematic_file, "validation"
        )

        # Should process successfully with proper detection
        assert result.success is True
        assert result.chunks_created > 0

    def test_processor_encoding_method_selection(self, temp_dir: Path) -> None:
        """Test that processor selects correct encoding method."""
        test_file = temp_dir / "method_selection.md"
        test_file.write_text("# Method Test\n\nContent", encoding="utf-8")

        # Test with detection enabled
        chunking_config = ChunkingConfig(chunk_size=500)

        config_with_detection = ProcessingConfig(enable_encoding_detection=True)
        processor_with = DocumentProcessor(chunking_config, config_with_detection)

        config_without_detection = ProcessingConfig(enable_encoding_detection=False)
        processor_without = DocumentProcessor(chunking_config, config_without_detection)

        # Verify initialization
        assert processor_with.encoding_detector is not None
        assert processor_without.encoding_detector is None

        # Both should process successfully
        result_with = processor_with.process_document(test_file, "with")
        result_without = processor_without.process_document(test_file, "without")

        assert result_with.success is True
        assert result_without.success is True
