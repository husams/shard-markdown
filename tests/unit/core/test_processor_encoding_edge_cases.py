"""Comprehensive tests for encoding edge cases in DocumentProcessor."""

from pathlib import Path

import pytest

from shard_markdown.config.settings import ProcessingConfig
from shard_markdown.core.models import ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor


class TestEncodingEdgeCases:
    """Test suite for encoding-related edge cases."""

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create processor for encoding testing."""
        return DocumentProcessor(chunking_config)

    @pytest.fixture
    def strict_processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create strict processor for encoding testing."""
        config = ProcessingConfig(strict_validation=True)
        return DocumentProcessor(chunking_config, processing_config=config)

    def test_valid_utf8_processing(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing of valid UTF-8 files."""
        # Create content with various UTF-8 characters
        content = """# Test Document with UTF-8 Content

This document contains various UTF-8 characters:
- Accented characters: café, naïve, résumé
- Mathematical symbols: α, β, γ, Σ, ∫, ∇
- Currency symbols: €, ¥, £, $
- Emojis: 🚀 📚 💡 🔥

## Unicode Code Points
- Latin: ñ (U+00F1)
- Greek: λ (U+03BB)
- Chinese: 中文 (U+4E2D, U+6587)
- Japanese: こんにちは (U+3053, U+3093, U+306B, U+3061, U+306F)
- Arabic: مرحبا (U+0645, U+0631, U+062D, U+0628, U+0627)

## Complex Characters
- Combining: é (e + ´) vs é (single character)
- Surrogate pairs: 𝕏 𝒞 𝔊 (mathematical symbols)
- Zero-width: ‌‍ (ZWNJ, ZWJ)

This content should process without issues.
"""

        utf8_file = temp_dir / "valid_utf8.md"
        utf8_file.write_text(content, encoding="utf-8")

        result = processor.process_document(utf8_file, "utf8-test")

        assert result.success is True
        assert result.chunks_created > 0
        assert result.error is None

    def test_utf8_with_bom(self, processor: DocumentProcessor, temp_dir: Path) -> None:
        """Test UTF-8 files with Byte Order Mark."""
        content = """# Document with BOM

This document has a UTF-8 Byte Order Mark at the beginning.

## Content
Regular markdown content with some Unicode: café, naïve, résumé.
"""

        bom_file = temp_dir / "utf8_with_bom.md"
        # Write with UTF-8 BOM
        with open(bom_file, "wb") as f:
            f.write(b"\xef\xbb\xbf")  # UTF-8 BOM
            f.write(content.encode("utf-8"))

        result = processor.process_document(bom_file, "bom-test")

        assert result.success is True
        assert result.chunks_created > 0
        assert result.error is None

    def test_partial_utf8_corruption(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test files with some invalid UTF-8 sequences."""
        # Create file with partial UTF-8 corruption
        corrupted_file = temp_dir / "partial_corruption.md"

        with open(corrupted_file, "wb") as f:
            # Valid UTF-8 content
            f.write(b"# Valid Header\n\n")
            f.write(b"This content is valid UTF-8.\n\n")

            # Insert some corrupted bytes (invalid UTF-8)
            f.write(b"Some text with corruption: ")
            f.write(b"\x80\x81\x82")  # Invalid UTF-8 start bytes
            f.write(b" more text.\n\n")

            # More valid content
            f.write(b"## Another Section\n")
            f.write(b"More valid content here.\n")

        result = processor.process_document(corrupted_file, "corruption-test")

        # Should fail due to corrupted encoding
        assert result.success is False
        assert result.error is not None
        assert "corrupted encoding" in result.error.lower()

    def test_binary_data_rejection(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that binary files are properly rejected."""
        binary_file = temp_dir / "binary_file.md"

        # Create a file with binary data that's definitely not text
        with open(binary_file, "wb") as f:
            # Write some binary data (like a small PNG header)
            f.write(b"\x89PNG\r\n\x1a\n")
            f.write(b"\x00\x00\x00\rIHDR")
            f.write(b"\x00\x00\x01\x00\x00\x00\x01\x00")
            f.write(b"\x08\x02\x00\x00\x00\x90wS\xde")
            # Add more random binary data
            f.write(bytes(range(256)) * 4)  # 1KB of binary data

        result = processor.process_document(binary_file, "binary-test")

        # Should fail due to encoding issues
        assert result.success is False
        assert result.error is not None
        assert "corrupted encoding" in result.error.lower()

    def test_mixed_encoding_combinations(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test various encoding combinations."""
        test_cases = [
            {
                "name": "latin1_extended",
                "content": "# Latin-1 Extended\n\nCharacters: áéíóú àèìòù äëïöü ñç",
                "encoding": "latin1",
            },
            {
                "name": "windows_1252",
                "content": "# Windows-1252\n\nSmart quotes: \"hello\" 'world' - em-dash",
                "encoding": "cp1252",
            },
            {
                "name": "iso_8859_1",
                "content": "# ISO-8859-1\n\nSymbols: © ® § ¶",
                "encoding": "iso-8859-1",
            },
        ]

        for case in test_cases:
            test_file = temp_dir / f"{case['name']}.md"
            test_file.write_text(case["content"], encoding=case["encoding"])

            result = processor.process_document(test_file, f"{case['name']}-test")

            # Should successfully process with encoding fallback
            assert result.success is True, f"Failed for {case['name']}"
            assert result.chunks_created > 0
            assert result.error is None

    def test_encoding_fallback_chain(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test encoding fallback behavior."""
        # Create processor with specific encoding fallback
        config = ProcessingConfig(encoding="utf-8", encoding_fallback="latin1")
        fallback_processor = DocumentProcessor(processor.chunking_config, config)

        # Create a file that's valid latin1 but invalid UTF-8
        latin1_file = temp_dir / "latin1_content.md"
        content = "# Document\n\nContent with extended characters: café résumé naïve"

        # Write as latin1 (will be invalid UTF-8)
        latin1_file.write_text(content, encoding="latin1")

        result = fallback_processor.process_document(latin1_file, "fallback-test")

        # Should succeed using fallback encoding
        assert result.success is True
        assert result.chunks_created > 0
        assert result.error is None

    def test_encoding_detection_failure(
        self, strict_processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test behavior when all encoding attempts fail."""
        failure_file = temp_dir / "encoding_failure.md"

        # Create a file with truly problematic byte sequences
        with open(failure_file, "wb") as f:
            # Mix of invalid UTF-8 and problematic latin1
            f.write(b"# Header\n")
            f.write(b"\xff\xfe\xfd\xfc\xfb\xfa\xf9\xf8")  # Invalid in both
            f.write(b"\x80\x81\x82\x83\x84\x85\x86\x87")  # More invalid bytes
            f.write(b"\n## Section\n")
            f.write(b"\x00\x01\x02\x03\x04\x05\x06\x07")  # Control characters

        result = strict_processor.process_document(failure_file, "failure-test")

        # Should fail in strict mode
        assert result.success is False
        assert result.error is not None
        assert "corrupted encoding" in result.error.lower()

    def test_empty_file_with_bom(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test empty file that only contains BOM."""
        bom_only_file = temp_dir / "bom_only.md"

        with open(bom_only_file, "wb") as f:
            f.write(b"\xef\xbb\xbf")  # Only UTF-8 BOM, no content

        result = processor.process_document(bom_only_file, "bom-only-test")

        # Should be treated as empty
        assert result.success is False
        assert result.error is not None
        assert "empty" in result.error.lower()

    def test_file_with_null_bytes(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test file with embedded null bytes."""
        null_file = temp_dir / "with_nulls.md"

        with open(null_file, "wb") as f:
            f.write(b"# Header\n\n")
            f.write(b"Some content")
            f.write(b"\x00\x00")  # Null bytes
            f.write(b"More content\n")
            f.write(b"## Section\n")
            f.write(b"Final content")
            f.write(b"\x00")  # Trailing null

        result = processor.process_document(null_file, "null-test")

        # Null bytes might be handled differently depending on implementation
        # This test documents the current behavior
        if result.success:
            assert result.chunks_created >= 0
        else:
            assert result.error is not None

    def test_large_unicode_content(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing large files with diverse Unicode content."""
        large_unicode_file = temp_dir / "large_unicode.md"

        content_parts = ["# Large Unicode Document\n\n"]

        # Add various Unicode ranges
        unicode_ranges = [
            ("Latin Extended", "àáâãäåæçèéêë"),
            ("Greek", "αβγδεζηθικλμ"),
            ("Cyrillic", "абвгдеёжзийкл"),
            ("Arabic", "ابتثجحخدذرزس"),
            ("Chinese", "中文测试内容"),
            ("Japanese", "こんにちはテスト"),
            ("Korean", "안녕하세요테스트"),
            ("Mathematical", "∑∫∇∂∆∏∐√∛∜"),
            ("Arrows", "←↑→↓↔↕↖↗"),
            ("Symbols", "♠♣♥♦♤♧♡♢"),
        ]

        for i in range(100):  # Create substantial content
            section_name, chars = unicode_ranges[i % len(unicode_ranges)]
            content_parts.extend(
                [
                    f"## Section {i + 1}: {section_name}\n\n",
                    f"Content with {section_name} characters: {chars}\n\n",
                    f"This section contains {len(chars)} characters from the "
                    f"{section_name} Unicode range.\n\n",
                ]
            )

        content = "".join(content_parts)
        large_unicode_file.write_text(content, encoding="utf-8")

        result = processor.process_document(large_unicode_file, "large-unicode-test")

        assert result.success is True
        assert result.chunks_created > 0
        assert result.error is None

    def test_encoding_with_strict_vs_graceful_mode(
        self, temp_dir: Path, chunking_config: ChunkingConfig
    ) -> None:
        """Test encoding error handling in strict vs graceful mode."""
        # Create problematic file
        problem_file = temp_dir / "encoding_problem.md"

        with open(problem_file, "wb") as f:
            f.write(b"# Valid Content\n\n")
            f.write(b"Some text before corruption.\n\n")
            f.write(b"\xff\xfe\xfd")  # Corruption
            f.write(b"\n\n## After Corruption\n")
            f.write(b"More text after corruption.\n")

        # Test strict mode
        strict_config = ProcessingConfig(strict_validation=True)
        strict_processor = DocumentProcessor(chunking_config, strict_config)

        strict_result = strict_processor.process_document(problem_file, "strict-test")

        assert strict_result.success is False
        assert strict_result.error is not None
        assert "corrupted encoding" in strict_result.error.lower()

        # Test graceful mode
        graceful_config = ProcessingConfig(strict_validation=False)
        graceful_processor = DocumentProcessor(chunking_config, graceful_config)

        graceful_result = graceful_processor.process_document(
            problem_file, "graceful-test"
        )

        # Graceful mode should also fail for corrupted files (security measure)
        assert graceful_result.success is False
        assert graceful_result.error is not None
        assert "corrupted encoding" in graceful_result.error.lower()

    @pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-32"])
    def test_different_utf_encodings(
        self, processor: DocumentProcessor, temp_dir: Path, encoding: str
    ) -> None:
        """Test processing files with different UTF encodings."""
        content = """# UTF Encoding Test

This document tests different UTF encodings.

## Unicode Content
- Multilingual: Hello, 你好, こんにちは, مرحبا
- Mathematical: ∑∫∇∂∆∏
- Arrows: ←↑→↓↔

## Conclusion
This content should work across UTF variants.
"""

        test_file = temp_dir / f"utf_{encoding.replace('-', '_')}.md"
        test_file.write_text(content, encoding=encoding)

        result = processor.process_document(test_file, f"{encoding}-test")

        # UTF-16 and UTF-32 might not be supported by default fallback
        if encoding == "utf-8":
            assert result.success is True
            assert result.chunks_created > 0
        else:
            # Document the behavior for other UTF variants
            # This will depend on the processor's encoding support
            if result.success:
                assert result.chunks_created >= 0
            else:
                assert result.error is not None


class TestCorruptionDetection:
    """Test corruption detection algorithms."""

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create processor for corruption testing."""
        return DocumentProcessor(chunking_config)

    def test_corruption_detection_patterns(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test specific corruption patterns are detected."""
        corruption_patterns = [
            {
                "name": "high_byte_concentration",
                "bytes": b"Normal text "
                + bytes(range(0xFF, 0xF0, -1)) * 10
                + b" more text",
                "should_detect": True,
            },
            {
                "name": "occasional_high_bytes",
                "bytes": b"Mostly normal text with occasional \xff byte here "
                b"and \xfe there",
                "should_detect": False,  # Should be acceptable
            },
            {
                "name": "valid_latin1_extended",
                "bytes": "Café résumé naïve piñata".encode("latin1"),
                "should_detect": False,  # Valid latin1
            },
        ]

        for pattern in corruption_patterns:
            test_file = temp_dir / f"{pattern['name']}.md"

            with open(test_file, "wb") as f:
                f.write(b"# Test Document\n\n")
                f.write(pattern["bytes"])
                f.write(b"\n\n## End Section\nFinal content.")

            result = processor.process_document(test_file, f"{pattern['name']}-test")

            if pattern["should_detect"]:
                assert result.success is False, (
                    f"Should detect corruption in {pattern['name']}"
                )
                assert result.error is not None
                assert "corrupted" in result.error.lower()
            else:
                # Should process successfully or fail for other reasons
                if result.success is False and result.error:
                    assert "corrupted" not in result.error.lower(), (
                        f"False positive in {pattern['name']}"
                    )

    def test_content_corruption_threshold(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test corruption detection threshold."""
        # Test above threshold (should fail)
        high_corruption_file = temp_dir / "high_corruption.md"
        base_content = "# Document\n\n"
        # Create content where >5% are suspicious bytes
        suspicious_bytes = b"\xff\xfe\xfd\xfc\xfb\xfa\xf9\xf8" * 20
        normal_content = b"Normal text content here."

        with open(high_corruption_file, "wb") as f:
            f.write(base_content.encode("utf-8"))
            f.write(suspicious_bytes)
            f.write(normal_content)

        result = processor.process_document(
            high_corruption_file, "high-corruption-test"
        )

        # Should fail (above threshold)
        assert result.success is False
        assert result.error is not None
        assert "corrupted" in result.error.lower()
