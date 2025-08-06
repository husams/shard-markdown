"""Advanced encoding detection and handling system."""

import hashlib
import time
from pathlib import Path
from typing import Any

import chardet
from pydantic import BaseModel, Field

from ..utils.errors import FileSystemError
from ..utils.logging import get_logger


logger = get_logger(__name__)


class EncodingDetectionResult(BaseModel):
    """Result of encoding detection."""

    encoding: str = Field(description="Detected encoding name")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Detection confidence (0.0-1.0)"
    )
    language: str | None = Field(
        default=None, description="Detected language (if available)"
    )
    detection_time: float = Field(
        default=0.0, description="Time taken for detection in seconds"
    )
    method: str = Field(description="Detection method used")
    sample_size: int = Field(description="Size of sample used for detection")


class EncodingDetectorConfig(BaseModel):
    """Configuration for encoding detector."""

    # Detection settings
    min_confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for auto-detection",
    )
    sample_size: int = Field(
        default=8192,
        ge=1024,
        le=65536,
        description="Sample size for detection (bytes)",
    )
    cache_size: int = Field(
        default=1000, ge=0, description="Maximum cache entries (0 to disable)"
    )
    cache_ttl: int = Field(
        default=3600, ge=0, description="Cache TTL in seconds (0 for no expiry)"
    )

    # Security settings
    allowed_encodings: set[str] = Field(
        default={
            "utf-8",
            "utf-16",
            "utf-32",
            "ascii",
            "iso-8859-1",
            "iso-8859-15",
            "windows-1252",
            "cp1252",
            "latin-1",
        },
        description="Whitelist of allowed encodings for security",
    )
    block_suspicious: bool = Field(
        default=True, description="Block suspicious/exotic encodings"
    )

    # Fallback chain
    fallback_encodings: list[str] = Field(
        default=["utf-8", "iso-8859-1", "windows-1252"],
        description="Fallback encoding chain",
    )
    strict_fallback: bool = Field(
        default=False, description="Use strict fallback without auto-detection"
    )


class CacheEntry(BaseModel):
    """Cache entry for encoding detection results."""

    result: EncodingDetectionResult
    timestamp: float
    file_hash: str


class EncodingDetector:
    """Advanced encoding detection system."""

    def __init__(self, config: EncodingDetectorConfig | None = None) -> None:
        """Initialize encoding detector.

        Args:
            config: Configuration for the detector
        """
        self.config = config or EncodingDetectorConfig()
        self._cache: dict[str, CacheEntry] = {}
        self._stats = {
            "detections": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "failures": 0,
            "total_time": 0.0,
        }

    def detect_encoding(self, file_path: Path) -> EncodingDetectionResult:
        """Detect file encoding with caching and confidence scoring.

        Args:
            file_path: Path to file to analyze

        Returns:
            EncodingDetectionResult with detection details

        Raises:
            FileSystemError: If file cannot be read or analyzed
        """
        start_time = time.time()
        self._stats["detections"] += 1

        try:
            # Check cache first
            if self.config.cache_size > 0:
                cache_key = str(file_path)
                cached_result = self._get_cached_result(file_path, cache_key)
                if cached_result:
                    self._stats["cache_hits"] += 1
                    return cached_result

            self._stats["cache_misses"] += 1

            # Read sample for detection
            sample_data = self._read_sample(file_path)
            if not sample_data:
                # Empty file - assume UTF-8
                result = EncodingDetectionResult(
                    encoding="utf-8",
                    confidence=1.0,
                    method="empty_file",
                    sample_size=0,
                    detection_time=time.time() - start_time,
                )
            else:
                # Perform detection
                result = self._detect_from_sample(sample_data, start_time)

            # Validate against security whitelist
            self._validate_encoding_security(result)

            # Cache result if caching enabled
            if self.config.cache_size > 0:
                self._cache_result(file_path, cache_key, result)

            self._stats["total_time"] += result.detection_time
            return result

        except Exception as e:
            self._stats["failures"] += 1
            if isinstance(e, FileSystemError):
                raise
            raise FileSystemError(
                f"Encoding detection failed for {file_path}: {e}",
                error_code=1250,
                context={"file_path": str(file_path)},
            ) from e

    def get_fallback_chain(
        self, detected_result: EncodingDetectionResult | None = None
    ) -> list[str]:
        """Get encoding fallback chain based on detection result.

        Args:
            detected_result: Optional detection result to influence chain

        Returns:
            List of encodings to try in order
        """
        chain = []

        # Add detected encoding first if confidence is reasonable
        if (
            detected_result
            and detected_result.confidence >= 0.5
            and detected_result.encoding in self.config.allowed_encodings
        ):
            chain.append(detected_result.encoding)

        # Add configured fallbacks
        for encoding in self.config.fallback_encodings:
            if encoding not in chain and encoding in self.config.allowed_encodings:
                chain.append(encoding)

        # Ensure we have at least utf-8 as final fallback
        if "utf-8" not in chain:
            chain.append("utf-8")

        return chain

    def validate_content_encoding(self, content: str, encoding: str) -> bool:
        """Validate that content was properly decoded from encoding.

        Args:
            content: Decoded content to validate
            encoding: Encoding that was used

        Returns:
            True if content appears properly decoded
        """
        if not content:
            return True

        # Check for common encoding corruption indicators
        corruption_indicators = [
            "\ufffd",  # Unicode replacement character
            "\x00",  # Null bytes (unusual in text)
        ]

        for indicator in corruption_indicators:
            if indicator in content:
                logger.warning(
                    f"Found encoding corruption indicator '{repr(indicator)}' "
                    f"when using encoding '{encoding}'"
                )
                return False

        # Check for suspicious byte patterns that indicate wrong encoding
        if self._has_encoding_artifacts(content):
            logger.warning(f"Found encoding artifacts when using encoding '{encoding}'")
            return False

        return True

    def clear_cache(self) -> None:
        """Clear the detection cache."""
        self._cache.clear()
        logger.debug("Encoding detection cache cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get detection statistics.

        Returns:
            Dictionary with statistics
        """
        stats = self._stats.copy()
        stats["cache_size"] = len(self._cache)
        stats["average_detection_time"] = (
            stats["total_time"] / stats["detections"]
            if stats["detections"] > 0
            else 0.0
        )
        stats["cache_hit_rate"] = (
            stats["cache_hits"] / (stats["cache_hits"] + stats["cache_misses"])
            if (stats["cache_hits"] + stats["cache_misses"]) > 0
            else 0.0
        )
        return stats

    def _read_sample(self, file_path: Path) -> bytes:
        """Read sample from file for detection.

        Args:
            file_path: Path to file

        Returns:
            Sample bytes for detection
        """
        if not file_path.exists():
            raise FileSystemError(
                f"File not found: {file_path}",
                error_code=1251,
                context={"file_path": str(file_path)},
            )

        try:
            with open(file_path, "rb") as f:
                return f.read(self.config.sample_size)
        except PermissionError:
            raise FileSystemError(
                f"Permission denied: {file_path}",
                error_code=1252,
                context={"file_path": str(file_path)},
            ) from None
        except Exception as e:
            raise FileSystemError(
                f"Error reading file sample: {file_path}: {e}",
                error_code=1253,
                context={"file_path": str(file_path)},
            ) from e

    def _detect_from_sample(
        self, sample_data: bytes, start_time: float
    ) -> EncodingDetectionResult:
        """Perform encoding detection from sample data.

        Args:
            sample_data: Sample bytes to analyze
            start_time: Start time for timing

        Returns:
            EncodingDetectionResult with detection details
        """
        # Use chardet for detection
        detection = chardet.detect(sample_data)

        # Extract results with defaults
        encoding = detection.get("encoding", "utf-8") or "utf-8"
        confidence = detection.get("confidence", 0.0) or 0.0
        language = detection.get("language")

        # Normalize encoding name
        encoding = self._normalize_encoding_name(encoding)

        detection_time = time.time() - start_time

        return EncodingDetectionResult(
            encoding=encoding,
            confidence=confidence,
            language=language,
            method="chardet",
            sample_size=len(sample_data),
            detection_time=detection_time,
        )

    def _normalize_encoding_name(self, encoding: str) -> str:
        """Normalize encoding name to standard form.

        Args:
            encoding: Raw encoding name

        Returns:
            Normalized encoding name
        """
        if not encoding:
            return "utf-8"

        # Convert to lowercase and handle common aliases
        encoding = encoding.lower().strip()

        # Common normalization mappings
        normalizations = {
            "utf8": "utf-8",
            "utf16": "utf-16",
            "utf32": "utf-32",
            "iso8859-1": "iso-8859-1",
            "iso-latin-1": "iso-8859-1",
            "latin1": "iso-8859-1",
            "cp1252": "windows-1252",
            "windows1252": "windows-1252",
        }

        return normalizations.get(encoding, encoding)

    def _validate_encoding_security(self, result: EncodingDetectionResult) -> None:
        """Validate encoding against security whitelist.

        Args:
            result: Detection result to validate

        Raises:
            FileSystemError: If encoding is not allowed
        """
        if (
            self.config.block_suspicious
            and result.encoding not in self.config.allowed_encodings
        ):
            # Check if it's a reasonable encoding that should be allowed
            safe_patterns = ["utf", "iso-8859", "windows-125", "cp125", "ascii"]
            is_safe = any(pattern in result.encoding for pattern in safe_patterns)

            if not is_safe:
                raise FileSystemError(
                    f"Encoding '{result.encoding}' is not in the security whitelist",
                    error_code=1254,
                    context={
                        "detected_encoding": result.encoding,
                        "confidence": result.confidence,
                        "allowed_encodings": list(self.config.allowed_encodings),
                    },
                )

    def _get_cached_result(
        self, file_path: Path, cache_key: str
    ) -> EncodingDetectionResult | None:
        """Get cached detection result if valid.

        Args:
            file_path: Path to file
            cache_key: Cache key

        Returns:
            Cached result or None if not available/valid
        """
        entry = self._cache.get(cache_key)
        if not entry:
            return None

        # Check TTL if configured
        if self.config.cache_ttl > 0:
            age = time.time() - entry.timestamp
            if age > self.config.cache_ttl:
                del self._cache[cache_key]
                return None

        # Verify file hasn't changed (basic check using mtime)
        try:
            current_hash = self._get_file_hash(file_path)
            if current_hash != entry.file_hash:
                del self._cache[cache_key]
                return None
        except Exception:
            # If we can't verify, assume invalid
            del self._cache[cache_key]
            return None

        return entry.result

    def _cache_result(
        self, file_path: Path, cache_key: str, result: EncodingDetectionResult
    ) -> None:
        """Cache detection result.

        Args:
            file_path: Path to file
            cache_key: Cache key
            result: Detection result to cache
        """
        # Enforce cache size limit
        if len(self._cache) >= self.config.cache_size:
            # Remove oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].timestamp)
            del self._cache[oldest_key]

        try:
            file_hash = self._get_file_hash(file_path)
            entry = CacheEntry(
                result=result, timestamp=time.time(), file_hash=file_hash
            )
            self._cache[cache_key] = entry
        except Exception:
            # Cache failure shouldn't break detection
            logger.debug(f"Failed to cache encoding result for {file_path}")

    def _get_file_hash(self, file_path: Path) -> str:
        """Get simple file hash for cache validation.

        Args:
            file_path: Path to file

        Returns:
            File hash string
        """
        # Use file size + mtime as simple hash
        stat = file_path.stat()
        data = f"{stat.st_size}:{stat.st_mtime}".encode()
        return hashlib.md5(data, usedforsecurity=False).hexdigest()[:8]

    def _has_encoding_artifacts(self, content: str) -> bool:
        """Check for encoding artifacts in content.

        Args:
            content: Content to check

        Returns:
            True if artifacts detected
        """
        if not content:
            return False

        # Common UTF-8 to latin-1 corruption patterns
        corruption_patterns = [
            "â€™",  # UTF-8 right single quote in latin-1
            "â€œ",  # UTF-8 left double quote in latin-1
            "â€",  # UTF-8 right double quote in latin-1
            "Ã©",  # UTF-8 é in latin-1
            "Ã¡",  # UTF-8 á in latin-1
            "Ã­",  # UTF-8 í in latin-1
            "Ã³",  # UTF-8 ó in latin-1
            "Ãº",  # UTF-8 ú in latin-1
        ]

        artifact_count = 0
        for pattern in corruption_patterns:
            artifact_count += content.count(pattern)

        # For longer content, use density-based detection
        if len(content) > 100:
            # If more than 5% of content is artifacts, likely corrupted
            return (artifact_count / len(content)) > 0.05

        # For shorter content, use count-based detection
        return artifact_count > 1
