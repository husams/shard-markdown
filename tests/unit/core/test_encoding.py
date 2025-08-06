"""Tests for advanced encoding detection system."""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from shard_markdown.core.encoding import (
    EncodingDetectionResult,
    EncodingDetector,
    EncodingDetectorConfig,
)
from shard_markdown.utils.errors import FileSystemError


class TestEncodingDetectorConfig:
    """Test EncodingDetectorConfig model."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = EncodingDetectorConfig()

        assert config.min_confidence == 0.8
        assert config.sample_size == 8192
        assert config.cache_size == 1000
        assert config.cache_ttl == 3600
        assert config.block_suspicious is True
        assert "utf-8" in config.allowed_encodings
        assert "iso-8859-1" in config.allowed_encodings
        assert config.fallback_encodings == ["utf-8", "iso-8859-1", "windows-1252"]
        assert config.strict_fallback is False

    def test_config_validation(self) -> None:
        """Test configuration validation."""
        # Valid config
        config = EncodingDetectorConfig(
            min_confidence=0.9,
            sample_size=4096,
            cache_size=500,
        )
        assert config.min_confidence == 0.9
        assert config.sample_size == 4096
        assert config.cache_size == 500

        # Invalid confidence (out of range)
        with pytest.raises(ValueError):
            EncodingDetectorConfig(min_confidence=1.5)

        # Invalid sample size (too small)
        with pytest.raises(ValueError):
            EncodingDetectorConfig(sample_size=500)


class TestEncodingDetectionResult:
    """Test EncodingDetectionResult model."""

    def test_result_creation(self) -> None:
        """Test creation of detection result."""
        result = EncodingDetectionResult(
            encoding="utf-8",
            confidence=0.95,
            language="en",
            method="chardet",
            sample_size=8192,
            detection_time=0.001,
        )

        assert result.encoding == "utf-8"
        assert result.confidence == 0.95
        assert result.language == "en"
        assert result.method == "chardet"
        assert result.sample_size == 8192
        assert result.detection_time == 0.001

    def test_result_validation(self) -> None:
        """Test result validation."""
        # Invalid confidence
        with pytest.raises(ValueError):
            EncodingDetectionResult(
                encoding="utf-8",
                confidence=1.5,
                method="test",
                sample_size=100,
            )


class TestEncodingDetector:
    """Test EncodingDetector functionality."""

    @pytest.fixture
    def detector(self) -> EncodingDetector:
        """Create detector with default config."""
        return EncodingDetector()

    @pytest.fixture
    def strict_detector(self) -> EncodingDetector:
        """Create detector with strict config."""
        config = EncodingDetectorConfig(
            min_confidence=0.9,
            block_suspicious=True,
            cache_size=0,  # Disable cache for testing
        )
        return EncodingDetector(config)

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_detector_initialization(self) -> None:
        """Test detector initialization."""
        detector = EncodingDetector()

        assert detector.config is not None
        assert isinstance(detector.config, EncodingDetectorConfig)
        assert len(detector._cache) == 0
        assert detector._stats["detections"] == 0

    def test_detect_empty_file(
        self, detector: EncodingDetector, temp_dir: Path
    ) -> None:
        """Test detection of empty file."""
        empty_file = temp_dir / "empty.md"
        empty_file.write_text("", encoding="utf-8")

        result = detector.detect_encoding(empty_file)

        assert result.encoding == "utf-8"
        assert result.confidence == 1.0
        assert result.method == "empty_file"
        assert result.sample_size == 0

    def test_detect_utf8_file(self, detector: EncodingDetector, temp_dir: Path) -> None:
        """Test detection of UTF-8 file."""
        content = "# Test Document\n\nThis is a test with unicode: café, naïve, résumé"
        utf8_file = temp_dir / "utf8.md"
        utf8_file.write_text(content, encoding="utf-8")

        result = detector.detect_encoding(utf8_file)

        assert result.encoding in ["utf-8", "ascii"]  # ASCII is subset of UTF-8
        assert result.confidence > 0.7
        assert result.method == "chardet"
        assert result.sample_size == len(content.encode("utf-8"))

    def test_detect_latin1_file(
        self, detector: EncodingDetector, temp_dir: Path
    ) -> None:
        """Test detection of Latin-1 file."""
        # Content with Latin-1 specific characters
        content = "# Document\n\nText with special chars: café, naïve, résumé, ñoño"
        latin1_file = temp_dir / "latin1.md"
        latin1_file.write_text(content, encoding="iso-8859-1")

        result = detector.detect_encoding(latin1_file)

        # chardet should detect this as some form of ISO or Windows encoding
        assert result.encoding in ["iso-8859-1", "windows-1252", "latin-1", "cp1252"]
        assert result.method == "chardet"
        assert result.sample_size > 0

    def test_nonexistent_file(self, detector: EncodingDetector, temp_dir: Path) -> None:
        """Test handling of non-existent file."""
        nonexistent = temp_dir / "nonexistent.md"

        with pytest.raises(FileSystemError) as exc_info:
            detector.detect_encoding(nonexistent)

        assert exc_info.value.error_code == 1251
        assert "not found" in str(exc_info.value)

    def test_permission_denied(
        self, detector: EncodingDetector, temp_dir: Path
    ) -> None:
        """Test handling of permission denied."""
        restricted_file = temp_dir / "restricted.md"
        restricted_file.write_text("content", encoding="utf-8")

        # Make file unreadable
        os.chmod(restricted_file, 0o000)

        try:
            with pytest.raises(FileSystemError) as exc_info:
                detector.detect_encoding(restricted_file)

            assert exc_info.value.error_code == 1252
            assert "permission denied" in str(exc_info.value).lower()
        finally:
            # Restore permissions for cleanup
            os.chmod(restricted_file, 0o644)

    def test_encoding_normalization(self, detector: EncodingDetector) -> None:
        """Test encoding name normalization."""
        test_cases = [
            ("UTF8", "utf-8"),
            ("utf8", "utf-8"),
            ("UTF-8", "utf-8"),
            ("ISO8859-1", "iso-8859-1"),
            ("latin1", "iso-8859-1"),
            ("cp1252", "windows-1252"),
            ("windows1252", "windows-1252"),
            ("unknown", "unknown"),  # Unknown stays as-is
        ]

        for input_encoding, expected in test_cases:
            normalized = detector._normalize_encoding_name(input_encoding)
            assert normalized == expected

    def test_security_whitelist(
        self, strict_detector: EncodingDetector, temp_dir: Path
    ) -> None:
        """Test security whitelist blocking."""
        test_file = temp_dir / "test.md"
        test_file.write_text("test content", encoding="utf-8")

        # Mock chardet to return a suspicious encoding
        with patch("chardet.detect") as mock_detect:
            mock_detect.return_value = {
                "encoding": "some-exotic-encoding",
                "confidence": 0.95,
                "language": None,
            }

            with pytest.raises(FileSystemError) as exc_info:
                strict_detector.detect_encoding(test_file)

            assert exc_info.value.error_code == 1254
            assert "not in the security whitelist" in str(exc_info.value)

    def test_fallback_chain_generation(self, detector: EncodingDetector) -> None:
        """Test fallback chain generation."""
        # Test with high-confidence detection result
        good_result = EncodingDetectionResult(
            encoding="iso-8859-1",
            confidence=0.9,
            method="test",
            sample_size=100,
        )

        chain = detector.get_fallback_chain(good_result)
        assert "iso-8859-1" == chain[0]  # Detected encoding first
        assert "utf-8" in chain  # Always include utf-8

        # Test with low-confidence result
        bad_result = EncodingDetectionResult(
            encoding="iso-8859-1",
            confidence=0.3,
            method="test",
            sample_size=100,
        )

        chain = detector.get_fallback_chain(bad_result)
        # Low confidence, so detected encoding might not be first
        assert "utf-8" in chain

    def test_content_validation(self, detector: EncodingDetector) -> None:
        """Test content encoding validation."""
        # Valid content
        good_content = "# Test\n\nThis is normal markdown content."
        assert detector.validate_content_encoding(good_content, "utf-8") is True

        # Content with replacement characters (corruption indicator)
        bad_content = "# Test\n\nThis has \ufffd replacement chars"
        assert detector.validate_content_encoding(bad_content, "utf-8") is False

        # Content with null bytes
        null_content = "# Test\n\nThis has \x00 null bytes"
        assert detector.validate_content_encoding(null_content, "utf-8") is False

        # Content with encoding artifacts
        artifact_content = "# Test\n\nThis has â€™ artifacts from UTF-8 corruption"
        assert detector.validate_content_encoding(artifact_content, "latin-1") is False

    def test_caching_functionality(self, temp_dir: Path) -> None:
        """Test encoding detection caching."""
        config = EncodingDetectorConfig(cache_size=10, cache_ttl=1)
        detector = EncodingDetector(config)

        test_file = temp_dir / "cached.md"
        test_file.write_text("# Test\n\nCached content", encoding="utf-8")

        # First detection - should be cache miss
        result1 = detector.detect_encoding(test_file)
        stats1 = detector.get_stats()
        assert stats1["cache_misses"] == 1
        assert stats1["cache_hits"] == 0

        # Second detection - should be cache hit
        result2 = detector.detect_encoding(test_file)
        stats2 = detector.get_stats()
        assert stats2["cache_hits"] == 1
        assert result1.encoding == result2.encoding

        # Wait for cache expiry
        time.sleep(1.1)

        # Third detection - cache expired, should be miss
        detector.detect_encoding(test_file)
        stats3 = detector.get_stats()
        assert stats3["cache_misses"] == 2

    def test_cache_invalidation_on_file_change(self, temp_dir: Path) -> None:
        """Test cache invalidation when file changes."""
        config = EncodingDetectorConfig(cache_size=10, cache_ttl=3600)
        detector = EncodingDetector(config)

        test_file = temp_dir / "changing.md"
        test_file.write_text("# Original\n\nOriginal content", encoding="utf-8")

        # First detection
        detector.detect_encoding(test_file)

        # Modify file (this changes mtime)
        time.sleep(0.1)  # Ensure different mtime
        test_file.write_text("# Modified\n\nModified content", encoding="utf-8")

        # Second detection - cache should be invalidated
        detector.detect_encoding(test_file)
        stats = detector.get_stats()
        assert stats["cache_misses"] == 2  # Both were cache misses

    def test_cache_size_limit(self, temp_dir: Path) -> None:
        """Test cache size limit enforcement."""
        config = EncodingDetectorConfig(cache_size=2)
        detector = EncodingDetector(config)

        # Create multiple files
        files = []
        for i in range(3):
            file_path = temp_dir / f"file_{i}.md"
            file_path.write_text(f"# File {i}\n\nContent {i}", encoding="utf-8")
            files.append(file_path)

        # Detect all files
        for file_path in files:
            detector.detect_encoding(file_path)

        # Cache should only have 2 entries (size limit)
        stats = detector.get_stats()
        assert stats["cache_size"] <= 2

    def test_statistics_collection(
        self, detector: EncodingDetector, temp_dir: Path
    ) -> None:
        """Test statistics collection."""
        test_file = temp_dir / "stats.md"
        test_file.write_text("# Test\n\nContent for stats", encoding="utf-8")

        # Initial stats
        stats = detector.get_stats()
        assert stats["detections"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["failures"] == 0

        # After detection
        detector.detect_encoding(test_file)
        stats = detector.get_stats()
        assert stats["detections"] == 1
        assert stats["cache_misses"] == 1
        assert stats["average_detection_time"] > 0
        assert stats["cache_hit_rate"] == 0.0  # First detection

        # After cache hit
        detector.detect_encoding(test_file)
        stats = detector.get_stats()
        assert stats["detections"] == 2
        assert stats["cache_hits"] == 1
        assert stats["cache_hit_rate"] == 0.5  # 1 hit out of 2 total

    def test_cache_clear(self, detector: EncodingDetector, temp_dir: Path) -> None:
        """Test cache clearing."""
        test_file = temp_dir / "clear_test.md"
        test_file.write_text("# Test\n\nContent", encoding="utf-8")

        # Populate cache
        detector.detect_encoding(test_file)
        stats_before = detector.get_stats()
        assert stats_before["cache_size"] > 0

        # Clear cache
        detector.clear_cache()
        stats_after = detector.get_stats()
        assert stats_after["cache_size"] == 0

    def test_encoding_artifacts_detection(self, detector: EncodingDetector) -> None:
        """Test detection of encoding artifacts."""
        # Content without artifacts
        clean_content = "# Normal Document\n\nThis is clean content without issues."
        assert detector._has_encoding_artifacts(clean_content) is False

        # Content with UTF-8 corruption patterns
        corrupted_content = "# Document\n\nThis has â€™ and â€œ corruption patterns."
        assert detector._has_encoding_artifacts(corrupted_content) is True

        # Content with high density of artifacts
        dense_artifacts = "â€™" * 100  # Many artifacts
        assert detector._has_encoding_artifacts(dense_artifacts) is True

        # Content with few artifacts (should not trigger)
        few_artifacts = "Normal content with one â€™ artifact in lots of text." * 10
        assert detector._has_encoding_artifacts(few_artifacts) is False

    @pytest.mark.parametrize(
        "encoding,content",
        [
            ("utf-8", "# UTF-8\n\nContent with unicode: café, naïve"),
            ("iso-8859-1", "# Latin-1\n\nContent with: café, naïve"),
            ("windows-1252", "# Windows\n\nContent with: café, naïve"),
        ],
    )
    def test_multiple_encodings(
        self, detector: EncodingDetector, temp_dir: Path, encoding: str, content: str
    ) -> None:
        """Test detection with multiple encodings."""
        test_file = temp_dir / f"{encoding.replace('-', '_')}.md"
        test_file.write_text(content, encoding=encoding)

        result = detector.detect_encoding(test_file)

        # Result should be reasonable
        assert result.encoding is not None
        assert result.confidence >= 0.0
        assert result.sample_size > 0
        assert result.detection_time >= 0.0

    def test_large_file_sampling(
        self, detector: EncodingDetector, temp_dir: Path
    ) -> None:
        """Test that large files are properly sampled."""
        # Create content larger than sample size
        large_content = "# Large File\n\n" + "Lorem ipsum dolor sit amet. " * 1000
        large_file = temp_dir / "large.md"
        large_file.write_text(large_content, encoding="utf-8")

        result = detector.detect_encoding(large_file)

        # Should have sampled only part of the file
        assert result.sample_size <= detector.config.sample_size
        assert result.sample_size > 0

    def test_disabled_caching(self, temp_dir: Path) -> None:
        """Test detector with caching disabled."""
        config = EncodingDetectorConfig(cache_size=0)
        detector = EncodingDetector(config)

        test_file = temp_dir / "no_cache.md"
        test_file.write_text("# Test\n\nNo caching", encoding="utf-8")

        # Multiple detections
        detector.detect_encoding(test_file)
        detector.detect_encoding(test_file)

        stats = detector.get_stats()
        assert stats["cache_size"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 2  # No caching, so both are "misses"
