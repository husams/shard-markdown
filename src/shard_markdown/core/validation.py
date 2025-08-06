"""Content validation module for document processing."""

import re
from pathlib import Path
from typing import NamedTuple

from pydantic import BaseModel, Field

from ..utils.logging import get_logger


logger = get_logger(__name__)


class ValidationConfig(BaseModel):
    """Configuration for content validation."""

    enable_content_validation: bool = Field(
        default=True, description="Enable content validation after decoding"
    )
    max_control_char_ratio: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Maximum ratio of control characters allowed",
    )
    check_encoding_artifacts: bool = Field(
        default=True, description="Check for encoding artifact patterns"
    )
    validate_markdown_structure: bool = Field(
        default=False, description="Validate basic markdown structure"
    )
    max_sample_size: int = Field(
        default=50000,
        ge=1000,
        description="Maximum size for validation sampling on large files",
    )
    min_printable_ratio: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum ratio of printable characters required",
    )


class ValidationResult(NamedTuple):
    """Result of content validation."""

    is_valid: bool
    error: str | None = None
    warnings: list[str] | None = None
    confidence: float = 1.0  # Confidence level in validation (0.0-1.0)


class ContentValidator:
    """Content validator for checking decoded content safety."""

    # Control characters that are typically problematic
    PROBLEMATIC_CONTROL_CHARS = set(range(0, 32)) - {9, 10, 13}  # Exclude tab, LF, CR

    # Common encoding corruption patterns
    CORRUPTION_PATTERNS = [
        # UTF-8 corruption patterns when decoded as latin-1
        "ÿþý",  # 0xFF 0xFE 0xFD sequence
        "â€™",  # UTF-8 right single quote (U+2019) as latin-1
        "â€œ",  # UTF-8 left double quote (U+201C) as latin-1
        "â€\x9d",  # UTF-8 right double quote (U+201D) as latin-1
        "â€¢",  # UTF-8 bullet (U+2022) as latin-1
        "â€¦",  # UTF-8 ellipsis (U+2026) as latin-1
        "â€\x94",  # UTF-8 em dash (U+2014) as latin-1
        "â€\x93",  # UTF-8 en dash (U+2013) as latin-1
        # Binary file signatures that might leak through
        "\x00\x00",  # Null byte sequences
        "\xff\xfe",  # UTF-16 LE BOM
        "\xfe\xff",  # UTF-16 BE BOM
        # PDF/binary signatures
        "%PDF",
        "\x89PNG",
        "GIF8",
        "\xff\xd8\xff",  # JPEG
    ]

    # Suspicious byte sequences that indicate corruption
    SUSPICIOUS_BYTES = {
        "\xff",  # 0xFF - often appears in corrupted files
        "\xfe",  # 0xFE - often appears in corrupted files
        "\xfd",  # 0xFD - often appears in corrupted files
        "\x80",  # 0x80 - invalid UTF-8 start byte
        "\x81",  # 0x81 - invalid UTF-8 start byte
        "\x82",  # 0x82 - invalid UTF-8 start byte
        "\x83",  # 0x83 - invalid UTF-8 start byte
        "\x84",  # 0x84 - invalid UTF-8 start byte
        "\x85",  # 0x85 - invalid UTF-8 start byte
    }

    # Binary file signatures to detect early
    BINARY_SIGNATURES = [
        # Image formats
        b"\x89PNG",  # PNG
        b"\xff\xd8\xff",  # JPEG
        b"GIF8",  # GIF
        b"\x42\x4d",  # BMP
        b"\x00\x00\x01\x00",  # ICO
        b"\x49\x49\x2a\x00",  # TIFF (little endian)
        b"\x4d\x4d\x00\x2a",  # TIFF (big endian)
        b"RIFF",  # WebP (starts with RIFF)
        # Document formats
        b"%PDF",  # PDF
        b"\xd0\xcf\x11\xe0",  # Microsoft Office
        b"PK\x03\x04",  # ZIP-based formats (DOCX, XLSX, etc)
        # Archive formats
        b"\x1f\x8b",  # GZIP
        b"\x50\x4b",  # ZIP
        b"\x52\x61\x72",  # RAR
        b"7z\xbc\xaf",  # 7-Zip
        # Executable formats
        b"MZ",  # PE/EXE
        b"\x7fELF",  # ELF
        b"\xca\xfe\xba\xbe",  # Mach-O
        b"\xfe\xed\xfa",  # Mach-O
        # Media formats
        b"ID3",  # MP3
        b"OggS",  # Ogg
        b"\x00\x00\x00\x20ftypM4A",  # M4A
        b"\x00\x00\x00\x18ftypmp42",  # MP4
        # Other binary formats
        b"\x00\x00\x02\x00",  # CUR (cursor)
        b"\x46\x4c\x56",  # FLV
        b"\x1a\x45\xdf\xa3",  # EBML (used by MKV, WebM)
        # Note: UTF-8 BOM removed from binary signatures
        # as it should be handled as text after decoding
    ]

    def __init__(self, config: ValidationConfig | None = None) -> None:
        """Initialize content validator.

        Args:
            config: Validation configuration
        """
        self.config = config or ValidationConfig()

    def detect_binary_content(self, content_bytes: bytes) -> bool:
        """Detect if content is binary based on file signatures.

        Args:
            content_bytes: Raw file content as bytes

        Returns:
            True if content appears to be binary data
        """
        if not content_bytes:
            return False

        # Skip BOM detection - BOM files should be handled as text
        # Check for known binary file signatures (excluding UTF-8 BOM)
        for signature in self.BINARY_SIGNATURES:
            if content_bytes.startswith(signature):
                return True

        # Special case: if the content is just UTF-8 BOM or BOM + whitespace,
        # don't treat as binary (will be handled as empty after decoding)
        if content_bytes.startswith(b"\xef\xbb\xbf"):
            # Check if it's just BOM + whitespace
            try:
                decoded = content_bytes.decode("utf-8")
                # Remove BOM and check if only whitespace remains
                content_without_bom = decoded.lstrip("\ufeff")
                if not content_without_bom.strip():  # Just BOM and/or whitespace
                    return False
            except UnicodeDecodeError:
                pass  # If can't decode, continue with binary checks

        # Check for high ratio of null bytes (common in binary files)
        null_count = content_bytes.count(b"\x00")
        if len(content_bytes) > 0 and (null_count / len(content_bytes)) > 0.01:
            return True

        # Check for high ratio of bytes outside printable ASCII range
        # But be more lenient for small files that might just be whitespace
        non_printable_count = sum(
            1 for byte in content_bytes if byte < 32 or byte > 126
        )
        if (
            len(content_bytes) > 100
            and (non_printable_count / len(content_bytes)) > 0.3
        ):
            return True

        return False

    def _is_effectively_empty(self, content: str) -> bool:
        """Check if content is effectively empty after removing BOM and whitespace.

        Args:
            content: String content to check

        Returns:
            True if content is empty or contains only BOM/whitespace
        """
        if not content:
            return True

        # Remove UTF-8 BOM if present
        content_without_bom = content.lstrip("\ufeff")

        # Check if only whitespace remains
        return not content_without_bom.strip()

    def validate_content(self, content: str, file_path: Path) -> ValidationResult:
        """Validate decoded content for processing safety.

        Args:
            content: The decoded content to validate
            file_path: Path to the source file for context

        Returns:
            ValidationResult with validation outcome and details
        """
        if not self.config.enable_content_validation:
            return ValidationResult(is_valid=True)

        # Fix empty content handling - should be invalid for processing
        if self._is_effectively_empty(content):
            return ValidationResult(
                is_valid=False,
                error="File is empty or contains no processable content",
            )

        warnings = []
        confidence = 1.0

        # Sample content for large files to improve performance
        sample_content, is_sampled = self._get_content_sample(content)
        if is_sampled:
            warnings.append("Large file: validation performed on sample")
            confidence *= 0.9

        try:
            # Early binary content detection using file signatures
            # (if we can access raw bytes)
            try:
                raw_bytes = file_path.read_bytes() if file_path.exists() else None
                if raw_bytes and self.detect_binary_content(raw_bytes):
                    return ValidationResult(
                        is_valid=False,
                        error=(
                            "File appears to contain binary data "
                            "(unsupported content type)"
                        ),
                        warnings=warnings,
                        confidence=confidence,
                    )
            except (OSError, PermissionError):
                # If we can't read the file, continue with string-based validation
                pass

            # Check for control character problems (with improved binary detection)
            control_check = self._check_control_characters(sample_content)
            if not control_check.is_valid:
                # Enhance error message to mention binary content for high
                # control char ratio
                error = control_check.error
                if error is not None and "control characters" in error.lower():
                    error = (
                        "File contains binary-like content with excessive "
                        f"control characters ({error.split('(')[1]}"
                    )

                return ValidationResult(
                    is_valid=False,
                    error=error,
                    warnings=warnings,
                    confidence=confidence,
                )

            # Check for encoding artifacts
            if self.config.check_encoding_artifacts:
                artifact_check = self._check_encoding_artifacts(sample_content)
                if not artifact_check.is_valid:
                    return ValidationResult(
                        is_valid=False,
                        error=artifact_check.error,
                        warnings=warnings,
                        confidence=confidence,
                    )
                if artifact_check.warnings:
                    warnings.extend(artifact_check.warnings)
                confidence *= artifact_check.confidence

            # Check printable character ratio (enhanced for binary detection)
            printable_check = self._check_printable_ratio(sample_content)
            if not printable_check.is_valid:
                return ValidationResult(
                    is_valid=False,
                    error=printable_check.error,
                    warnings=warnings,
                    confidence=confidence,
                )

            # Check for suspicious patterns
            suspicious_check = self._check_suspicious_patterns(sample_content)
            if not suspicious_check.is_valid:
                return ValidationResult(
                    is_valid=False,
                    error=suspicious_check.error,
                    warnings=warnings,
                    confidence=confidence,
                )

            # Optional markdown structure validation
            if self.config.validate_markdown_structure:
                structure_check = self._check_markdown_structure(sample_content)
                if not structure_check.is_valid:
                    # Structure validation failures are warnings, not hard failures
                    warnings.append(
                        f"Markdown structure issue: {structure_check.error}"
                    )
                    confidence *= 0.8

            return ValidationResult(
                is_valid=True,
                warnings=warnings if warnings else None,
                confidence=confidence,
            )

        except Exception as e:
            logger.warning(f"Content validation error for {file_path}: {e}")
            # Validation errors shouldn't block processing
            return ValidationResult(
                is_valid=True,
                warnings=[f"Validation error: {e}"],
                confidence=0.5,
            )

    def _get_content_sample(self, content: str) -> tuple[str, bool]:
        """Get a sample of content for validation.

        For large files, validates first, middle, and last chunks to balance
        performance with detection accuracy.

        Args:
            content: Full content string

        Returns:
            Tuple of (sample_content, is_sampled)
        """
        if len(content) <= self.config.max_sample_size:
            return content, False

        # Sample strategy: first 1/3, middle 1/3, last 1/3 of max sample size
        chunk_size = self.config.max_sample_size // 3
        content_len = len(content)

        # Get three chunks
        first_chunk = content[:chunk_size]
        middle_start = (content_len - chunk_size) // 2
        middle_chunk = content[middle_start : middle_start + chunk_size]
        last_chunk = content[-chunk_size:]

        # Combine chunks
        sample = first_chunk + middle_chunk + last_chunk

        return sample, True

    def _check_control_characters(self, content: str) -> ValidationResult:
        """Check for excessive control characters.

        Args:
            content: Content to check

        Returns:
            ValidationResult for control character check
        """
        if not content:
            return ValidationResult(is_valid=True)

        control_count = 0
        for char in content:
            if ord(char) in self.PROBLEMATIC_CONTROL_CHARS:
                control_count += 1

        control_ratio = control_count / len(content)

        if control_ratio > self.config.max_control_char_ratio:
            return ValidationResult(
                is_valid=False,
                error=f"Too many control characters: {control_ratio:.2%} "
                f"(max: {self.config.max_control_char_ratio:.2%})",
            )

        if control_ratio > self.config.max_control_char_ratio * 0.5:
            return ValidationResult(
                is_valid=True,
                warnings=[
                    f"High control character ratio: {control_ratio:.2%}",
                ],
                confidence=0.8,
            )

        return ValidationResult(is_valid=True)

    def _check_encoding_artifacts(self, content: str) -> ValidationResult:
        """Check for common encoding corruption artifacts.

        Args:
            content: Content to check

        Returns:
            ValidationResult for encoding artifact check
        """
        warnings = []
        confidence = 1.0

        for pattern in self.CORRUPTION_PATTERNS:
            if pattern in content:
                # Count occurrences to determine severity
                count = content.count(pattern)
                pattern_ratio = count * len(pattern) / len(content)

                if pattern_ratio > 0.01:  # More than 1% of content
                    return ValidationResult(
                        is_valid=False,
                        error=f"High density of encoding corruption pattern "
                        f"'{pattern}': {count} occurrences "
                        f"({pattern_ratio:.2%} of content)",
                    )
                elif count > 5:  # More than 5 occurrences
                    warnings.append(
                        f"Multiple encoding corruption patterns detected: '{pattern}' "
                        f"({count} occurrences)"
                    )
                    confidence *= 0.9
                else:
                    warnings.append(f"Potential encoding artifact: '{pattern}'")
                    confidence *= 0.95

        # Check for suspicious byte sequences
        suspicious_count = 0
        for char in content:
            if char in self.SUSPICIOUS_BYTES:
                suspicious_count += 1

        if suspicious_count > 0:
            suspicious_ratio = suspicious_count / len(content)
            if suspicious_ratio > 0.05:  # More than 5%
                return ValidationResult(
                    is_valid=False,
                    error=f"High density of suspicious bytes: {suspicious_ratio:.2%}",
                )
            elif suspicious_ratio > 0.01:  # More than 1%
                warnings.append(
                    f"Suspicious byte sequences detected: {suspicious_ratio:.2%}"
                )
                confidence *= 0.8

        return ValidationResult(
            is_valid=True,
            warnings=warnings if warnings else None,
            confidence=confidence,
        )

    def _check_printable_ratio(self, content: str) -> ValidationResult:
        """Check ratio of printable characters.

        Args:
            content: Content to check

        Returns:
            ValidationResult for printable character ratio check
        """
        if not content:
            return ValidationResult(is_valid=True)

        printable_count = 0
        for char in content:
            # Consider printable: letters, digits, punctuation, whitespace
            # Also consider UTF-8 BOM as printable for this check
            if (
                char.isprintable()
                or char in {" ", "\t", "\n", "\r", "\ufeff"}  # Include BOM
                or ord(char) in {0x0A, 0x0D, 0x09}  # LF, CR, TAB
            ):
                printable_count += 1

        printable_ratio = printable_count / len(content)

        if printable_ratio < self.config.min_printable_ratio:
            return ValidationResult(
                is_valid=False,
                error=(
                    "File appears to contain binary data with too few "
                    f"printable characters: {printable_ratio:.2%} "
                    f"(min: {self.config.min_printable_ratio:.2%})"
                ),
            )

        return ValidationResult(is_valid=True)

    def _check_suspicious_patterns(self, content: str) -> ValidationResult:
        """Check for suspicious byte patterns that might indicate binary data.

        Args:
            content: Content to check

        Returns:
            ValidationResult for suspicious pattern check
        """
        # Look for long sequences of the same byte (common in binary files)
        if re.search(r"(.)\1{50,}", content):
            return ValidationResult(
                is_valid=False,
                error=(
                    "File appears to contain binary data with long sequences "
                    "of repeated bytes"
                ),
            )

        # Look for patterns that suggest base64 or hex encoding
        base64_pattern = r"[A-Za-z0-9+/]{100,}={0,2}"
        if re.search(base64_pattern, content):
            matches = len(re.findall(base64_pattern, content))
            if matches > 3:  # Multiple long base64-like sequences
                return ValidationResult(
                    is_valid=False,
                    error="File appears to contain encoded binary data",
                )

        return ValidationResult(is_valid=True)

    def _check_markdown_structure(self, content: str) -> ValidationResult:
        """Validate basic markdown structure.

        This is an optional, more lenient check for markdown validity.

        Args:
            content: Content to check

        Returns:
            ValidationResult for markdown structure check
        """
        lines = content.split("\n")
        issues = []

        # Check for unclosed code blocks
        code_block_count = 0
        for line in lines:
            if line.strip().startswith("```"):
                code_block_count += 1

        if code_block_count % 2 != 0:
            issues.append("Unclosed code blocks detected")

        # Check for malformed headers (multiple # at start but not proper header)
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") and not re.match(r"^#{1,6}\s+.+", stripped):
                if len(stripped) > 1 and stripped[1] != " ":
                    issues.append(f"Malformed header at line {i}: '{line.strip()}'")

        if issues:
            return ValidationResult(
                is_valid=False,
                error="; ".join(issues),
            )

        return ValidationResult(is_valid=True)
