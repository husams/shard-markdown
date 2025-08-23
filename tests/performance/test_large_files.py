"""Performance tests for large file processing - NOT run in CI/CD."""

import time
from pathlib import Path
from typing import Any

import pytest

from shard_markdown.config.settings import Settings
from shard_markdown.core.processor import DocumentProcessor


@pytest.mark.performance
@pytest.mark.skip(
    reason="Run manually: uv run pytest tests/performance/test_large_files.py"
)
class TestLargeFiles:
    """Test processing of extremely large markdown files."""

    @pytest.fixture
    def generate_large_markdown(self, tmp_path: Path) -> Any:
        """Generate large markdown files for testing."""

        def _generate(size_mb: int) -> Path:
            """Generate a markdown file of specified size in MB."""
            file_path = tmp_path / f"large_{size_mb}mb.md"

            # Calculate approximate content needed
            target_bytes = size_mb * 1024 * 1024

            content = ["# Large Document Test\n\n"]
            content.append("## Table of Contents\n\n")

            # Add TOC entries
            for i in range(100):
                content.append(f"{i + 1}. [Section {i + 1}](#section-{i + 1})\n")

            content.append("\n---\n\n")

            # Generate sections with content
            section_template = """## Section {num}

### Overview of Section {num}

This is section number {num} of the large document. It contains substantial
content to test the processing capabilities of the markdown processor with
large files.

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
consequat.

### Details for Section {num}

#### Subsection {num}.1

Detailed content for subsection {num}.1. This includes various markdown
elements to test comprehensive parsing:

- **Bold text** for emphasis
- *Italic text* for subtle emphasis
- `Inline code` for technical terms
- [Links](https://example.com) to external resources

#### Subsection {num}.2

```python
# Code block for section {num}
def process_section_{num}(data):
    \"\"\"Process data for section {num}.\"\"\"
    result = []
    for item in data:
        if item > {num}:
            result.append(item * {num})
    return result
```

#### Subsection {num}.3

| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Data {num}A | Value {num}1 | Result {num}X |
| Data {num}B | Value {num}2 | Result {num}Y |
| Data {num}C | Value {num}3 | Result {num}Z |

### Summary of Section {num}

This concludes section {num}. The key points covered were:

1. Point one about topic {num}
2. Point two regarding aspect {num}
3. Point three concerning element {num}

---

"""

            current_size = len("".join(content).encode())
            section_num = 1

            while current_size < target_bytes:
                section_content = section_template.format(num=section_num)
                content.append(section_content)
                current_size += len(section_content.encode())
                section_num += 1

            # Write to file
            file_path.write_text("".join(content))
            return file_path

        return _generate

    def test_10mb_markdown_processing(self, generate_large_markdown):
        """Test processing of 10MB markdown file."""
        large_file = generate_large_markdown(10)

        settings = Settings(chunk_size=1000, chunk_method="structure")
        processor = DocumentProcessor(settings)

        start_time = time.time()
        result = processor.process_document(large_file)
        elapsed = time.time() - start_time

        assert result.success is True
        assert elapsed < 30  # Should process in under 30 seconds
        assert result.chunks_created > 0

        # Memory usage should stay reasonable
        # This is a basic check - more sophisticated memory profiling
        # would require additional tools

        print(f"\n10MB file processed in {elapsed:.2f} seconds")
        print(f"Chunks created: {result.chunks_created}")
        print(f"Chunks per second: {result.chunks_per_second:.2f}")

    def test_50mb_markdown_processing(self, generate_large_markdown):
        """Test processing of 50MB markdown file."""
        large_file = generate_large_markdown(50)

        settings = Settings(chunk_size=2000, chunk_method="fixed")
        processor = DocumentProcessor(settings)

        start_time = time.time()
        result = processor.process_document(large_file)
        elapsed = time.time() - start_time

        assert result.success is True
        assert elapsed < 120  # Should process in under 2 minutes
        assert result.chunks_created > 0

        print(f"\n50MB file processed in {elapsed:.2f} seconds")
        print(f"Chunks created: {result.chunks_created}")
        print(f"Processing rate: {50 / elapsed:.2f} MB/s")

    def test_deeply_nested_markdown(self, tmp_path: Path) -> None:
        """Test processing markdown with deeply nested structures (>20 levels)."""
        # Generate deeply nested markdown
        content = ["# Root Document\n\n"]

        # Create nested headers
        for level in range(1, 21):
            header = "#" * min(level, 6)  # Markdown supports up to 6 levels
            indent = "  " * (level - 1)
            content.append(f"{header} Level {level} Header\n\n")
            content.append(f"Content at level {level}.\n\n")

            # Add nested list
            for i in range(3):
                list_indent = "  " * level
                content.append(f"{list_indent}- Item {i + 1} at level {level}\n")

            content.append("\n")

            # Add nested blockquote
            quote_marker = ">" * min(level, 10)
            content.append(f"{quote_marker} Nested quote at level {level}\n\n")

        # Add deeply nested code blocks
        content.append("```python\n")
        for i in range(20):
            indent = "    " * i
            content.append(f"{indent}if condition_{i}:\n")

        for i in range(19, -1, -1):
            indent = "    " * (i + 1)
            content.append(f"{indent}process_{i}()\n")

        content.append("```\n\n")

        nested_file = tmp_path / "deeply_nested.md"
        nested_file.write_text("".join(content))

        settings = Settings(chunk_size=500)
        processor = DocumentProcessor(settings)

        start_time = time.time()
        result = processor.process_document(nested_file)
        elapsed = time.time() - start_time

        assert result.success is True
        assert result.chunks_created > 0

        print(f"\nDeeply nested document processed in {elapsed:.2f} seconds")

    def test_processing_time_per_mb(self, generate_large_markdown):
        """Measure processing time per MB across different file sizes."""
        sizes = [1, 5, 10, 20]
        results = []

        settings = Settings(chunk_size=1000)
        processor = DocumentProcessor(settings)

        for size_mb in sizes:
            large_file = generate_large_markdown(size_mb)

            start_time = time.time()
            result = processor.process_document(large_file)
            elapsed = time.time() - start_time

            assert result.success is True

            mb_per_second = size_mb / elapsed
            results.append(
                {
                    "size_mb": size_mb,
                    "time_seconds": elapsed,
                    "mb_per_second": mb_per_second,
                    "chunks": result.chunks_created,
                }
            )

        print("\n=== Processing Speed Analysis ===")
        for r in results:
            print(
                f"{r['size_mb']}MB: {r['time_seconds']:.2f}s "
                f"({r['mb_per_second']:.2f} MB/s, {r['chunks']} chunks)"
            )

        # Processing speed should be relatively consistent
        speeds = [r["mb_per_second"] for r in results]
        avg_speed = sum(speeds) / len(speeds)

        # All speeds should be within 50% of average (allowing for variance)
        for speed in speeds:
            assert 0.5 * avg_speed <= speed <= 1.5 * avg_speed

    def test_maximum_chunk_count(self, tmp_path: Path) -> None:
        """Test handling of files that generate maximum number of chunks."""
        # Create a file with many small sections
        content = ["# Document with Many Sections\n\n"]

        for i in range(1000):
            content.append(f"## Section {i}\n\n")
            content.append(f"Brief content for section {i}.\n\n")

        many_chunks_file = tmp_path / "many_chunks.md"
        many_chunks_file.write_text("".join(content))

        # Use very small chunk size to create many chunks
        settings = Settings(chunk_size=50, chunk_method="fixed")
        processor = DocumentProcessor(settings)

        start_time = time.time()
        result = processor.process_document(many_chunks_file)
        elapsed = time.time() - start_time

        assert result.success is True
        assert result.chunks_created > 100  # Should create many chunks

        print(
            f"\nFile with {result.chunks_created} chunks processed in "
            f"{elapsed:.2f} seconds"
        )
        print(f"Chunks per second: {result.chunks_created / elapsed:.2f}")

    def test_unicode_heavy_content(self, tmp_path: Path) -> None:
        """Test processing files with heavy Unicode content."""
        # Create file with various Unicode characters
        content = ["# Unicode-Heavy Document 📚\n\n"]

        # Add content in various languages and scripts
        content.append("## Multiple Languages\n\n")
        content.append("### English\n")
        content.append("The quick brown fox jumps over the lazy dog.\n\n")

        content.append("### 中文\n")
        content.append("快速的棕色狐狸跳过懒惰的狗。\n\n")

        content.append("### 日本語\n")
        content.append("素早い茶色のキツネは怠け者の犬を飛び越える。\n\n")

        content.append("### العربية\n")
        content.append("الثعلب البني السريع يقفز فوق الكلب الكسول。\n\n")

        content.append("### हिन्दी\n")
        content.append("तेज़ भूरी लोमड़ी आलसी कुत्ते के ऊपर कूदती है।\n\n")

        content.append("### Emoji Heavy Section 🎉🎊🎈\n")
        content.append("Testing with emojis: 😀😃😄😁😆😅😂🤣😊😇🙂🙃😉😌\n\n")

        # Add mathematical symbols
        content.append("## Mathematical Symbols\n")
        content.append("∀x ∈ ℝ: x² ≥ 0\n")
        content.append("∑(i=1 to n) i = n(n+1)/2\n")
        content.append("∫₀^∞ e^(-x²) dx = √π/2\n\n")

        # Repeat to create larger file
        full_content = "".join(content) * 100

        unicode_file = tmp_path / "unicode_heavy.md"
        unicode_file.write_text(full_content)

        settings = Settings(chunk_size=500)
        processor = DocumentProcessor(settings)

        start_time = time.time()
        result = processor.process_document(unicode_file)
        elapsed = time.time() - start_time

        assert result.success is True
        assert result.chunks_created > 0

        print(f"\nUnicode-heavy file processed in {elapsed:.2f} seconds")
        print(f"File size: {len(full_content.encode('utf-8')) / 1024:.2f} KB")
