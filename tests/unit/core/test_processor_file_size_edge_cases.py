"""Comprehensive tests for file size edge cases in DocumentProcessor."""

from pathlib import Path

import pytest

from shard_markdown.config.settings import ProcessingConfig
from shard_markdown.core.models import ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor


class TestFileSizeEdgeCases:
    """Test suite for file size-related edge cases."""

    @pytest.fixture
    def small_limit_config(self) -> ProcessingConfig:
        """Create config with small file size limit for testing."""
        return ProcessingConfig(max_file_size=1000)  # 1KB limit

    @pytest.fixture
    def tiny_limit_config(self) -> ProcessingConfig:
        """Create config with very small file size limit."""
        return ProcessingConfig(max_file_size=100)  # 100 bytes limit

    @pytest.fixture
    def large_limit_config(self) -> ProcessingConfig:
        """Create config with large file size limit."""
        return ProcessingConfig(max_file_size=10 * 1024 * 1024)  # 10MB limit

    def test_file_at_exact_size_limit(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test file exactly at the configured size limit."""
        limit = 500  # 500 bytes
        config = ProcessingConfig(max_file_size=limit)
        processor = DocumentProcessor(chunking_config, config)

        # Create content exactly at the limit
        base_content = "# Test Document\n\nThis content is sized exactly at the limit."
        padding_needed = limit - len(base_content.encode("utf-8"))

        if padding_needed > 0:
            # Add padding to reach exact limit
            padding = " " * (padding_needed - 1) + "\n"  # -1 for final newline
            exact_content = base_content + padding
        else:
            exact_content = base_content[:limit]

        exact_file = temp_dir / "exact_limit.md"
        exact_file.write_text(exact_content, encoding="utf-8")

        # Verify file size is exactly at limit
        file_size = exact_file.stat().st_size
        assert file_size == limit

        result = processor.process_document(exact_file, "exact-limit-test")

        # Should succeed at exact limit
        assert result.success is True
        assert result.chunks_created >= 0
        assert result.error is None

    def test_file_just_under_limit(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test file 1 byte under the size limit."""
        limit = 500
        config = ProcessingConfig(max_file_size=limit)
        processor = DocumentProcessor(chunking_config, config)

        # Create content 1 byte under the limit
        base_content = "# Test Document\n\nThis content is just under the limit."
        target_size = limit - 1
        current_size = len(base_content.encode("utf-8"))

        if current_size < target_size:
            padding_needed = target_size - current_size
            padding = " " * padding_needed
            under_content = base_content + padding
        else:
            under_content = base_content[:target_size]

        under_file = temp_dir / "under_limit.md"
        under_file.write_text(under_content, encoding="utf-8")

        # Verify file size is exactly 1 under limit
        file_size = under_file.stat().st_size
        assert file_size == limit - 1

        result = processor.process_document(under_file, "under-limit-test")

        # Should succeed
        assert result.success is True
        assert result.chunks_created >= 0
        assert result.error is None

    def test_file_just_over_limit(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test file 1 byte over the size limit."""
        limit = 500
        config = ProcessingConfig(max_file_size=limit)
        processor = DocumentProcessor(chunking_config, config)

        # Create content 1 byte over the limit
        base_content = "# Test Document\n\nThis content is just over the limit."
        current_size = len(base_content.encode("utf-8"))
        target_size = limit + 1

        if current_size < target_size:
            padding_needed = target_size - current_size
            padding = " " * padding_needed
            over_content = base_content + padding
        else:
            over_content = base_content + "X"  # Ensure it's over

        over_file = temp_dir / "over_limit.md"
        over_file.write_text(over_content, encoding="utf-8")

        # Verify file size is over limit
        file_size = over_file.stat().st_size
        assert file_size > limit

        result = processor.process_document(over_file, "over-limit-test")

        # Should fail due to size limit
        assert result.success is False
        assert result.error is not None
        assert "too large" in result.error.lower()
        assert result.chunks_created == 0

    def test_empty_files(self, chunking_config: ChunkingConfig, temp_dir: Path) -> None:
        """Test handling of empty files."""
        processor = DocumentProcessor(chunking_config)

        empty_file = temp_dir / "empty.md"
        empty_file.write_text("", encoding="utf-8")

        # Verify file is empty
        assert empty_file.stat().st_size == 0

        result = processor.process_document(empty_file, "empty-test")

        # Should fail as empty
        assert result.success is False
        assert result.error is not None
        assert "empty" in result.error.lower()

    def test_very_large_files_memory_stress(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test very large files (memory stress testing)."""
        # Create processor with large file limit
        config = ProcessingConfig(max_file_size=5 * 1024 * 1024)  # 5MB limit
        processor = DocumentProcessor(chunking_config, config)

        # Create a large file (1MB content)
        large_file = temp_dir / "large_stress.md"

        # Build large content efficiently
        content_parts = ["# Large Document for Memory Stress Test\n\n"]

        # Create substantial content sections
        section_template = """## Section {section_num}

This is section {section_num} of a large document designed to test memory handling
and processing performance. Each section contains substantial content to ensure
the document reaches a significant size while remaining valid markdown.

### Subsection {section_num}.1

Here's some detailed content for subsection {section_num}.1. This content
includes multiple paragraphs and various markdown elements to make it realistic.

```python
def section_{section_num}_function():
    '''Function for section {section_num}.'''
    return f"Processing section {section_num}"

# Example usage
result = section_{section_num}_function()
print(result)
```

### Subsection {section_num}.2

More content for subsection {section_num}.2 with lists:

1. First item in section {section_num}
2. Second item in section {section_num}
3. Third item in section {section_num}

- Bullet point one
- Bullet point two
- Bullet point three

### Conclusion for Section {section_num}

This concludes section {section_num} of our large document.

"""

        # Add many sections to reach ~1MB
        for i in range(1, 200):  # Approximately 1MB when fully rendered
            content_parts.append(section_template.format(section_num=i))

        content = "".join(content_parts)
        large_file.write_text(content, encoding="utf-8")

        # Verify file is indeed large
        file_size = large_file.stat().st_size
        assert file_size > 500 * 1024  # At least 500KB
        assert file_size < 5 * 1024 * 1024  # Under 5MB limit

        result = processor.process_document(large_file, "large-stress-test")

        # Should succeed and create many chunks
        assert result.success is True
        assert result.chunks_created > 10  # Should create many chunks
        assert result.error is None
        assert result.processing_time > 0

    def test_size_limit_enforcement_order(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test that size limit is checked before other processing."""
        # Very small limit to trigger size check quickly
        config = ProcessingConfig(max_file_size=50)  # 50 bytes
        processor = DocumentProcessor(chunking_config, config)

        # Create a file that's over the limit but has other issues too
        problem_file = temp_dir / "size_and_encoding_issue.md"

        with open(problem_file, "wb") as f:
            # Write content that exceeds 50 bytes and has encoding issues
            f.write(b"# Document with Multiple Issues\n\n")  # ~30 bytes
            f.write(
                b"This content exceeds the size limit "
            )  # ~30 bytes more = ~60 total
            f.write(b"and also has corruption: ")  # More bytes
            f.write(b"\xff\xfe\xfd")  # Encoding issues
            f.write(b" more content to ensure size limit is hit first")

        result = processor.process_document(problem_file, "size-first-test")

        # Should fail due to size limit, not encoding
        assert result.success is False
        assert result.error is not None
        assert "too large" in result.error.lower()
        assert "corrupted" not in result.error.lower()  # Size check happens first

    @pytest.mark.parametrize("size_limit", [10, 50, 100, 500, 1000])
    def test_various_size_limits(
        self, chunking_config: ChunkingConfig, temp_dir: Path, size_limit: int
    ) -> None:
        """Test processing with various size limits."""
        config = ProcessingConfig(max_file_size=size_limit)
        processor = DocumentProcessor(chunking_config, config)

        # Create content that varies based on the limit
        if size_limit < 50:
            content = "# Small\n\nTiny content."
        elif size_limit < 200:
            content = "# Medium\n\nSome medium content here for testing purposes."
        else:
            content = "# Large\n\n" + "Substantial content for larger limits. " * 10

        test_file = temp_dir / f"limit_{size_limit}.md"
        test_file.write_text(content, encoding="utf-8")

        file_size = test_file.stat().st_size
        result = processor.process_document(test_file, f"limit-{size_limit}-test")

        if file_size <= size_limit:
            # Should succeed if within limit
            assert result.success is True
            assert result.chunks_created >= 0
        else:
            # Should fail if over limit
            assert result.success is False
            assert result.error is not None
            assert "too large" in result.error.lower()

    def test_unicode_size_calculation(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test size limits with Unicode content (byte vs character count)."""
        config = ProcessingConfig(max_file_size=100)  # 100 bytes limit
        processor = DocumentProcessor(chunking_config, config)

        # Create content with multi-byte Unicode characters
        unicode_content = (
            "# Test\n\n" + "café résumé naïve " * 5
        )  # Each accent char is 2 bytes in UTF-8

        unicode_file = temp_dir / "unicode_size.md"
        unicode_file.write_text(unicode_content, encoding="utf-8")

        # Check actual file size in bytes
        file_size = unicode_file.stat().st_size
        char_count = len(unicode_content)

        # Byte size should be larger than character count due to UTF-8 encoding
        assert file_size > char_count

        result = processor.process_document(unicode_file, "unicode-size-test")

        # Result should depend on byte size, not character count
        if file_size <= 100:
            assert result.success is True
        else:
            assert result.success is False
            assert "too large" in result.error.lower()

    def test_concurrent_large_file_processing(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test concurrent processing of multiple large files."""
        config = ProcessingConfig(max_file_size=2 * 1024 * 1024)  # 2MB limit
        processor = DocumentProcessor(chunking_config, config)

        # Create multiple moderately large files
        large_files = []
        for i in range(5):
            large_file = temp_dir / f"concurrent_large_{i}.md"

            # Create ~100KB content per file
            content_parts = [f"# Large Document {i}\n\n"]
            for j in range(50):
                content_parts.append(f"## Section {j}\n\n")
                content_parts.append(f"Content for section {j} in document {i}. " * 20)
                content_parts.append("\n\n")

            content = "".join(content_parts)
            large_file.write_text(content, encoding="utf-8")
            large_files.append(large_file)

        # Process files concurrently
        batch_result = processor.process_batch(
            large_files, "concurrent-large-test", max_workers=3
        )

        # All should succeed
        assert batch_result.total_files == 5
        assert batch_result.successful_files == 5
        assert batch_result.failed_files == 0
        assert batch_result.total_chunks > 0

    def test_size_limit_with_empty_content(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test size limits combined with empty content detection."""
        config = ProcessingConfig(max_file_size=1000)
        processor = DocumentProcessor(chunking_config, config)

        # Create file that's within size limit but effectively empty
        whitespace_file = temp_dir / "whitespace_within_limit.md"
        whitespace_content = (
            " " * 500 + "\n" * 100 + "\t" * 50
        )  # 650 bytes of whitespace
        whitespace_file.write_text(whitespace_content, encoding="utf-8")

        # Verify size is within limit
        file_size = whitespace_file.stat().st_size
        assert file_size < 1000

        result = processor.process_document(whitespace_file, "whitespace-limit-test")

        # Should fail due to empty content, not size
        assert result.success is False
        assert result.error is not None
        assert "empty" in result.error.lower()
        assert "too large" not in result.error.lower()

    def test_size_check_performance(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test that size checking is performant and doesn't read entire file."""
        config = ProcessingConfig(max_file_size=1000)
        processor = DocumentProcessor(chunking_config, config)

        # Create a file that's much larger than the limit
        huge_file = temp_dir / "huge_file.md"

        # Create large content efficiently without loading into memory
        with open(huge_file, "w", encoding="utf-8") as f:
            f.write("# Huge Document\n\n")
            # Write content that will exceed limit quickly
            for i in range(1000):
                f.write(f"Line {i} with sufficient content to exceed the size limit.\n")

        # Verify file is much larger than limit
        file_size = huge_file.stat().st_size
        assert file_size > 10 * 1000  # Much larger than 1000 byte limit

        import time

        start_time = time.time()

        result = processor.process_document(huge_file, "huge-performance-test")

        end_time = time.time()
        processing_time = end_time - start_time

        # Should fail quickly due to size check
        assert result.success is False
        assert "too large" in result.error.lower()
        # Should be very fast since it only checks file size, doesn't read content
        assert processing_time < 1.0  # Should complete in under 1 second


class TestMemoryManagement:
    """Test memory management with various file sizes."""

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create processor for memory testing."""
        config = ProcessingConfig(max_file_size=10 * 1024 * 1024)  # 10MB limit
        return DocumentProcessor(chunking_config, config)

    def test_streaming_like_behavior(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test that large files don't cause memory issues."""
        # Create a moderately large file (500KB)
        large_file = temp_dir / "memory_test.md"

        content_parts = ["# Memory Management Test\n\n"]

        # Create content with repeated patterns
        base_section = (
            """## Section {num}

This section contains substantial content designed to test memory usage patterns.
The content is structured to be realistic markdown while being large enough to
test memory management capabilities of the document processor.

### Code Examples

```python
def process_section_{num}():
    '''Process section {num} efficiently.'''
    data = []
    for i in range(100):
        data.append(f"Item {{i}} in section {num}")
    return data

# Usage example
result = process_section_{num}()
print(f"Processed {{len(result)}} items")
```

### Lists and Content

"""
            + "\n".join(
                [f"{i}. List item {i} in section {{num}}" for i in range(1, 21)]
            )
            + "\n\n"
        )

        # Add enough sections to reach ~500KB
        for i in range(1, 100):
            content_parts.append(base_section.format(num=i))

        content = "".join(content_parts)
        large_file.write_text(content, encoding="utf-8")

        file_size = large_file.stat().st_size
        assert file_size > 400 * 1024  # At least 400KB

        # Process and monitor basic performance
        import time

        start_time = time.time()

        result = processor.process_document(large_file, "memory-test")

        end_time = time.time()
        processing_time = end_time - start_time

        # Should succeed efficiently
        assert result.success is True
        assert result.chunks_created > 0
        # Should complete in reasonable time (adjust threshold as needed)
        assert processing_time < 10.0  # Should complete within 10 seconds

    def test_multiple_large_files_memory(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing multiple large files to check for memory leaks."""
        files = []

        # Create several moderately sized files
        for i in range(3):  # 3 files to avoid excessive test time
            test_file = temp_dir / f"memory_batch_{i}.md"

            # Create ~200KB content per file
            sections = []
            sections.append(f"# Memory Test Document {i}\n\n")

            for j in range(50):
                sections.append(f"## Section {j}\n\n")
                sections.append(f"Content for section {j} of document {i}. " * 30)
                sections.append("\n\n")

                if j % 10 == 0:  # Add code blocks periodically
                    sections.append(f"""```python
def function_{i}_{j}():
    '''Function {j} in document {i}.'''
    return f"Result from document {i}, section {j}"
```

""")

            content = "".join(sections)
            test_file.write_text(content, encoding="utf-8")
            files.append(test_file)

        # Verify files are substantial
        total_size = sum(f.stat().st_size for f in files)
        assert total_size > 500 * 1024  # At least 500KB total

        # Process batch
        batch_result = processor.process_batch(
            files, "memory-batch-test", max_workers=2
        )

        # Should succeed for all files
        assert batch_result.total_files == 3
        assert batch_result.successful_files == 3
        assert batch_result.failed_files == 0
        assert batch_result.total_chunks > 0
