"""Tests for advanced encoding detection system."""

import os
import tempfile
import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from shard_markdown.core.encoding import (
    EncodingDetectionResult,
    EncodingDetector,
    EncodingDetectorConfig,
)
from shard_markdown.utils.errors import (
    BinaryContentError,
    CharsetDetectionError,
    EncodingError,
)


class TestEncodingDetectorConfig:
    """Test configuration for encoding detector."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = EncodingDetectorConfig()

        assert config.confidence_threshold == 0.8
        assert config.fallback_encoding == "utf-8"
        assert config.sample_size == 50000
        assert config.enable_advanced_detection is True
        assert config.enable_binary_detection is True
        assert config.max_binary_ratio == 0.3
        assert config.binary_chunk_size == 8192

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = EncodingDetectorConfig(
            confidence_threshold=0.9,
            fallback_encoding="latin-1",
            sample_size=10000,
            enable_advanced_detection=False,
            enable_binary_detection=False,
            max_binary_ratio=0.1,
            binary_chunk_size=4096,
        )

        assert config.confidence_threshold == 0.9
        assert config.fallback_encoding == "latin-1"
        assert config.sample_size == 10000
        assert config.enable_advanced_detection is False
        assert config.enable_binary_detection is False
        assert config.max_binary_ratio == 0.1
        assert config.binary_chunk_size == 4096

    def test_config_validation(self) -> None:
        """Test configuration validation."""
        # Test invalid confidence threshold
        with pytest.raises(ValueError):
            EncodingDetectorConfig(confidence_threshold=-0.1)

        with pytest.raises(ValueError):
            EncodingDetectorConfig(confidence_threshold=1.1)

        # Test invalid sample size
        with pytest.raises(ValueError):
            EncodingDetectorConfig(sample_size=0)

        # Test invalid binary ratio
        with pytest.raises(ValueError):
            EncodingDetectorConfig(max_binary_ratio=-0.1)

        with pytest.raises(ValueError):
            EncodingDetectorConfig(max_binary_ratio=1.1)

        # Test invalid binary chunk size
        with pytest.raises(ValueError):
            EncodingDetectorConfig(binary_chunk_size=0)


class TestEncodingDetectionResult:
    """Test encoding detection result."""

    def test_result_creation(self) -> None:
        """Test result creation."""
        result = EncodingDetectionResult(
            encoding="utf-8",
            confidence=0.95,
            is_binary=False,
            errors=[],
        )

        assert result.encoding == "utf-8"
        assert result.confidence == 0.95
        assert result.is_binary is False
        assert result.errors == []

    def test_result_with_errors(self) -> None:
        """Test result with errors."""
        result = EncodingDetectionResult(
            encoding="utf-8",
            confidence=0.5,
            is_binary=False,
            errors=["Low confidence detection"],
        )

        assert result.encoding == "utf-8"
        assert result.confidence == 0.5
        assert result.is_binary is False
        assert result.errors == ["Low confidence detection"]


class TestEncodingDetector:
    """Test the main encoding detector class."""

    @pytest.fixture
    def detector(self) -> EncodingDetector:
        """Create a detector instance for testing."""
        config = EncodingDetectorConfig(
            sample_size=1000,  # Smaller sample for testing
            binary_chunk_size=512,
        )
        return EncodingDetector(config)

    @pytest.fixture
    def temp_dir(self) -> Generator[Path, None, None]:
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_detector_initialization(self) -> None:
        """Test detector initialization."""
        detector = EncodingDetector()

        assert detector.config is not None
        assert isinstance(detector.config, EncodingDetectorConfig)

    def test_utf8_detection(self, detector: EncodingDetector, temp_dir: Path) -> None:
        """Test UTF-8 encoding detection."""
        content = "Hello World! 🌍 Unicode test with émojis"
        test_file = temp_dir / "utf8_test.txt"
        test_file.write_text(content, encoding="utf-8")

        result = detector.detect_encoding(test_file)

        assert result.encoding.lower() == "utf-8"
        assert result.confidence > 0.8
        assert result.is_binary is False
        assert len(result.errors) == 0

    def test_latin1_detection(self, detector: EncodingDetector, temp_dir: Path) -> None:
        """Test Latin-1 encoding detection."""
        content = "Héllo wörld with spëcial charâcters"
        test_file = temp_dir / "latin1_test.txt"
        test_file.write_bytes(content.encode("latin-1"))

        result = detector.detect_encoding(test_file)

        # Should detect latin-1 or similar
        assert result.encoding.lower() in ["latin-1", "iso-8859-1", "windows-1252"]
        assert result.confidence > 0.5
        assert result.is_binary is False

    def test_binary_file_detection(
        self, detector: EncodingDetector, temp_dir: Path
    ) -> None:
        """Test binary file detection."""
        # Create a file with binary content
        binary_data = bytes(range(256)) * 10  # Binary pattern
        test_file = temp_dir / "binary_test.bin"
        test_file.write_bytes(binary_data)

        with pytest.raises(BinaryContentError):
            detector.detect_encoding(test_file)

    def test_empty_file_handling(
        self, detector: EncodingDetector, temp_dir: Path
    ) -> None:
        """Test handling of empty files."""
        test_file = temp_dir / "empty_test.txt"
        test_file.write_text("", encoding="utf-8")

        result = detector.detect_encoding(test_file)

        # Should default to UTF-8 for empty files
        assert result.encoding == "utf-8"
        assert result.is_binary is False

    def test_large_file_sampling(
        self, detector: EncodingDetector, temp_dir: Path
    ) -> None:
        """Test encoding detection on large files with sampling."""
        # Create a large file
        large_content = "Test content with unicode: 🚀\n" * 10000
        test_file = temp_dir / "large_test.txt"
        test_file.write_text(large_content, encoding="utf-8")

        result = detector.detect_encoding(test_file)

        assert result.encoding.lower() == "utf-8"
        assert result.confidence > 0.8
        assert result.is_binary is False

    def test_mixed_encoding_detection(
        self, detector: EncodingDetector, temp_dir: Path
    ) -> None:
        """Test detection of files with mixed encoding issues."""
        # Create content that might be ambiguous
        content = "Regular ASCII text mixed with special chars: café naïve résumé"
        test_file = temp_dir / "mixed_test.txt"
        test_file.write_bytes(content.encode("utf-8"))

        result = detector.detect_encoding(test_file)

        assert result.encoding.lower() in ["utf-8", "ascii"]
        assert result.confidence > 0.5
        assert result.is_binary is False

    def test_nonexistent_file_handling(self, detector: EncodingDetector) -> None:
        """Test handling of non-existent files."""
        nonexistent_file = Path("/path/to/nonexistent/file.txt")

        with pytest.raises(FileNotFoundError):
            detector.detect_encoding(nonexistent_file)

    def test_permission_denied_handling(
        self, detector: EncodingDetector, temp_dir: Path
    ) -> None:
        """Test handling of permission denied errors."""
        test_file = temp_dir / "restricted_test.txt"
        test_file.write_text("Test content", encoding="utf-8")

        # Remove read permissions
        os.chmod(test_file, 0o000)

        try:
            with pytest.raises(PermissionError):
                detector.detect_encoding(test_file)
        finally:
            # Restore permissions for cleanup
            os.chmod(test_file, 0o644)

    def test_confidence_threshold_handling(
        self, detector: EncodingDetector, temp_dir: Path
    ) -> None:
        """Test handling of low confidence detection."""
        # Create content that might have ambiguous encoding
        ambiguous_content = b"\x80\x81\x82\x83" * 100  # Ambiguous bytes
        test_file = temp_dir / "ambiguous_test.txt"
        test_file.write_bytes(ambiguous_content)

        try:
            result = detector.detect_encoding(test_file)
            # If detection succeeds, check that it falls back appropriately
            assert result.encoding is not None
            if result.confidence < detector.config.confidence_threshold:
                assert result.encoding == detector.config.fallback_encoding
        except (EncodingError, CharsetDetectionError, BinaryContentError):
            # These exceptions are acceptable for ambiguous content
            pass

    def test_bom_detection(self, detector: EncodingDetector, temp_dir: Path) -> None:
        """Test Byte Order Mark (BOM) detection."""
        # UTF-8 with BOM
        content = "Test content with BOM"
        utf8_bom = b"\xef\xbb\xbf" + content.encode("utf-8")
        test_file = temp_dir / "bom_test.txt"
        test_file.write_bytes(utf8_bom)

        result = detector.detect_encoding(test_file)

        assert result.encoding.lower() in ["utf-8", "utf-8-sig"]
        assert result.confidence > 0.8
        assert result.is_binary is False

    def test_corrupted_file_handling(
        self, detector: EncodingDetector, temp_dir: Path
    ) -> None:
        """Test handling of corrupted or partially written files."""
        # Create a file with invalid UTF-8 sequences
        invalid_utf8 = b"Valid start \xff\xfe Invalid UTF-8 sequence"
        test_file = temp_dir / "corrupted_test.txt"
        test_file.write_bytes(invalid_utf8)

        # Should either detect with low confidence or raise an error
        try:
            result = detector.detect_encoding(test_file)
            # If successful, should have some encoding
            assert result.encoding is not None
        except (EncodingError, CharsetDetectionError, BinaryContentError):
            # These errors are acceptable for corrupted content
            pass

    def test_performance_timing(
        self, detector: EncodingDetector, temp_dir: Path
    ) -> None:
        """Test performance characteristics of encoding detection."""
        # Create a moderately large file
        content = "Performance test content with unicode: 🎯\n" * 1000
        test_file = temp_dir / "performance_test.txt"
        test_file.write_text(content, encoding="utf-8")

        start_time = time.time()
        result = detector.detect_encoding(test_file)
        end_time = time.time()

        # Detection should complete reasonably quickly
        assert end_time - start_time < 1.0  # Should be under 1 second
        assert result.encoding.lower() == "utf-8"
        assert result.confidence > 0.8

    @patch("chardet.detect")
    def test_chardet_fallback(
        self, mock_detect: pytest.Mock, detector: EncodingDetector, temp_dir: Path
    ) -> None:
        """Test fallback to chardet when built-in detection fails."""
        mock_detect.return_value = {"encoding": "utf-8", "confidence": 0.95}

        content = "Test content for chardet fallback"
        test_file = temp_dir / "chardet_test.txt"
        test_file.write_text(content, encoding="utf-8")

        result = detector.detect_encoding(test_file)

        assert result.encoding == "utf-8"
        # Should have called chardet as fallback
        mock_detect.assert_called()

    def test_config_override(self) -> None:
        """Test detector with custom configuration."""
        custom_config = EncodingDetectorConfig(
            confidence_threshold=0.95,
            fallback_encoding="latin-1",
            sample_size=2000,
        )
        detector = EncodingDetector(custom_config)

        assert detector.config.confidence_threshold == 0.95
        assert detector.config.fallback_encoding == "latin-1"
        assert detector.config.sample_size == 2000
