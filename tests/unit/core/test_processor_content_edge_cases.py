"""Comprehensive tests for content processing edge cases in DocumentProcessor."""

from pathlib import Path

import pytest

from shard_markdown.config.settings import ProcessingConfig
from shard_markdown.core.models import ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor


class TestContentProcessingEdgeCases:
    """Test suite for content processing edge cases."""

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create processor for content testing."""
        return DocumentProcessor(chunking_config)

    @pytest.fixture
    def strict_processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create strict processor for content testing."""
        config = ProcessingConfig(strict_validation=True)
        return DocumentProcessor(chunking_config, config)

    def test_files_with_only_whitespace(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test files containing only whitespace characters."""
        whitespace_cases = [
            {
                "name": "spaces_only",
                "content": "    " * 100,  # Only spaces
            },
            {
                "name": "tabs_only",
                "content": "\t" * 50,  # Only tabs
            },
            {
                "name": "newlines_only",
                "content": "\n" * 20,  # Only newlines
            },
            {
                "name": "mixed_whitespace",
                "content": "   \n\n\t\t\n   \n\t  \n\n\t",  # Mixed whitespace
            },
            {
                "name": "carriage_returns",
                "content": "\r\n\r\n\r\n\r\n",  # Windows-style line endings
            },
            {
                "name": "unicode_whitespace",
                "content": "\u00a0\u2000\u2001\u2002\u2003",  # Unicode whitespace chars
            },
        ]

        for case in whitespace_cases:
            whitespace_file = temp_dir / f"{case['name']}.md"
            whitespace_file.write_text(case["content"], encoding="utf-8")

            result = processor.process_document(whitespace_file, f"{case['name']}-test")

            # Should fail as empty content
            assert result.success is False, f"Should fail for {case['name']}"
            assert result.error is not None
            assert "empty" in result.error.lower()
            assert result.chunks_created == 0

    def test_files_with_control_characters(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of files with control characters."""
        control_cases = [
            {
                "name": "embedded_nulls",
                "content": "# Document\n\nText with\x00null\x00chars\n\n## Section\nMore content",
            },
            {
                "name": "bell_characters",
                "content": "# Alert\n\nText with\x07bell\x07sounds\n\nContent continues",
            },
            {
                "name": "backspace_chars",
                "content": "# Document\n\nText\x08with\x08backspace\n\nMore content",
            },
            {
                "name": "form_feed",
                "content": "# Page 1\n\nContent\x0cPage 2\n\nMore content",
            },
            {
                "name": "vertical_tab",
                "content": "# Document\n\nText\x0bwith\x0bvertical\x0btabs\n\nEnd",
            },
            {
                "name": "escape_sequences",
                "content": "# Document\n\nText with\x1b[31mANSI\x1b[0mcolors\n\nEnd",
            },
        ]

        for case in control_cases:
            control_file = temp_dir / f"control_{case['name']}.md"
            control_file.write_text(case["content"], encoding="utf-8")

            result = processor.process_document(
                control_file, f"control-{case['name']}-test"
            )

            # Control characters might be handled differently
            # Document the current behavior
            if result.success:
                assert result.chunks_created >= 0
            else:
                assert result.error is not None

    def test_files_with_mixed_line_endings(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test files with mixed line endings."""
        mixed_line_endings = [
            {
                "name": "unix_windows_mix",
                "content": "# Unix Header\n\nUnix paragraph.\n\r\n## Windows Header\r\n\r\nWindows paragraph.\r\n",
            },
            {
                "name": "old_mac_style",
                "content": "# Old Mac\rContent with old Mac line endings\rAnother line\r## Section\rMore content\r",
            },
            {
                "name": "all_three_mixed",
                "content": "# Mixed\nUnix line\r\nWindows line\rOld Mac line\n\nAnother Unix\r\n\r\nWindows paragraph\r",
            },
            {
                "name": "inconsistent_spacing",
                "content": "# Header\n \n  \n\t\n## Section\r\n  \r\n\t\r\n### Subsection\r \r  \rContent\n",
            },
        ]

        for case in mixed_line_endings:
            mixed_file = temp_dir / f"mixed_{case['name']}.md"
            mixed_file.write_text(case["content"], encoding="utf-8")

            result = processor.process_document(
                mixed_file, f"mixed-{case['name']}-test"
            )

            # Should handle mixed line endings gracefully
            assert result.success is True
            assert result.chunks_created > 0
            assert result.error is None

    def test_markdown_with_complex_nesting(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test markdown with complex nesting structures."""
        complex_markdown = """# Complex Nested Document

This document tests complex markdown nesting patterns.

## Lists with Deep Nesting

1. First level item
   1. Second level numbered
      - Third level bullet
        - Fourth level bullet
          - Fifth level bullet
            1. Sixth level numbered
               - Seventh level bullet
                 > Eighth level quote
                 >
                 > With multiple paragraphs

2. Back to first level
   - Mixed list types
     1. Numbered in bullet
        > Quote in numbered
        >
        > ```python
        > # Code in quote in numbered in bullet
        > def deeply_nested():
        >     return "very deep"
        > ```

## Blockquotes with Complex Content

> This is a blockquote
>
> > With nested blockquotes
> >
> > > And triple nesting
> > >
> > > ```markdown
> > > # Code block in triple nested quote
> > >
> > > - List in code in quote
> > >   - With nesting
> > > ```
>
> Back to single level quote
>
> 1. List in quote
>    - Bullet in numbered in quote
>      > Quote in bullet in numbered in quote

## Code Blocks with Various Nesting

```markdown
# This is markdown in a code block

## With its own structure

- Lists in code blocks
  - With nesting

> And quotes

```python
# Nested code blocks (though this won't render as nested)
print("Hello from nested code")
```

More markdown content after nested code.
```

## Tables with Complex Content

| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Simple   | **Bold** | *Italic* |
| `Code`   | [Link](http://example.com) | ![Image](img.jpg) |
| Multi<br>Line | List:<br>- Item 1<br>- Item 2 | Quote:<br>> Text |

## Definition Lists (if supported)

Term 1
: Definition with **formatting**
: Multiple definitions

  With paragraphs

Term 2
: Definition with code `inline`

```python
# Code block in definition
def example():
    return "definition"
```

## Footnotes and References

This text has a footnote[^1] and another[^complex].

[^1]: Simple footnote

[^complex]: Complex footnote with **formatting**, `code`, and [links](http://example.com).

    Multiple paragraphs in footnote.

    - Lists in footnotes
    - With multiple items

    > Quotes in footnotes too

## HTML Mixed with Markdown

<div class="custom">
<h3>HTML Header</h3>

**Markdown** still works in HTML blocks sometimes.

<ul>
<li>HTML list item with **markdown**</li>
<li>Another item with <code>HTML code</code></li>
</ul>
</div>

### Final Complex Example

<details>
<summary>Click to expand complex content</summary>

This is inside an HTML details element.

> With quotes
>
> ```python
> # And code
> def in_details():
>     return "complex"
> ```

- And lists
  - With nesting
    1. Mixed types
       > More quotes

</details>

## Conclusion

This document tests the limits of nested markdown parsing.
"""

        complex_file = temp_dir / "complex_nesting.md"
        complex_file.write_text(complex_markdown, encoding="utf-8")

        result = processor.process_document(complex_file, "complex-nesting-test")

        # Should handle complex nesting successfully
        assert result.success is True
        assert result.chunks_created > 0
        assert result.error is None

    def test_malformed_markdown_structures(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of malformed or broken markdown structures."""
        malformed_cases = [
            {
                "name": "unclosed_code_blocks",
                "content": """# Document

```python
def function():
    return "unclosed code block"
    # No closing ```

## Next Section
This follows an unclosed code block.
""",
            },
            {
                "name": "mismatched_emphasis",
                "content": """# Document

**Bold start but no end

*Italic start but no end

__Another bold start but no end

_Another italic start but no end

## Section
Normal content after mismatched emphasis.
""",
            },
            {
                "name": "broken_links",
                "content": """# Document

[Broken link with no URL]

[Another broken](

[Incomplete](http://example.com

![Broken image](

![Another broken

## Section
Content after broken links.
""",
            },
            {
                "name": "malformed_tables",
                "content": """# Document

| Header 1 | Header 2
|----------|
| Row 1 | Too many cells | Extra |
| Row 2 |

| Another | Table |
| No separator row |
| Data | Here |

## Section
Content after malformed tables.
""",
            },
            {
                "name": "invalid_html",
                "content": """# Document

<div>
<p>Unclosed paragraph
<span>Unclosed span

<invalid-tag>Content</invalid-tag>

<script>alert('test');</script>

## Section
Content after invalid HTML.
""",
            },
        ]

        for case in malformed_cases:
            malformed_file = temp_dir / f"malformed_{case['name']}.md"
            malformed_file.write_text(case["content"], encoding="utf-8")

            result = processor.process_document(
                malformed_file, f"malformed-{case['name']}-test"
            )

            # Should handle malformed markdown gracefully
            # Parser should be robust enough to extract some content
            assert result.success is True  # Should not crash
            if result.success:
                assert result.chunks_created >= 0  # May or may not create chunks
            assert result.error is None

    def test_extremely_long_lines(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of files with extremely long lines."""
        long_line_cases = [
            {
                "name": "single_long_paragraph",
                "content": "# Document\n\n"
                + "This is an extremely long paragraph. " * 1000
                + "\n\n## End\n",
            },
            {
                "name": "long_code_line",
                "content": """# Document

```python
def function_with_very_long_line():
    return '"""
                + "very_long_string_" * 100
                + """'
```

## End
""",
            },
            {
                "name": "long_url",
                "content": "# Document\n\n[Link](http://example.com/"
                + "path/" * 500
                + "file.html)\n\n## End\n",
            },
            {
                "name": "long_header",
                "content": "# " + "Very Long Header " * 100 + "\n\nContent\n\n## End\n",
            },
        ]

        for case in long_line_cases:
            long_file = temp_dir / f"long_{case['name']}.md"
            long_file.write_text(case["content"], encoding="utf-8")

            result = processor.process_document(long_file, f"long-{case['name']}-test")

            # Should handle long lines without issues
            assert result.success is True
            assert result.chunks_created > 0
            assert result.error is None

    def test_files_with_only_punctuation_and_symbols(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test files containing only punctuation and symbols."""
        symbol_cases = [
            {
                "name": "markdown_symbols",
                "content": "# * ** *** _ __ ___ ` ``` > >> >>> - -- --- + ++ +++ = == === ~ ~~ ~~~",
            },
            {
                "name": "special_chars",
                "content": "!@#$%^&*()[]{}|\\:;\"'<>,.?/`~",
            },
            {
                "name": "unicode_symbols",
                "content": "© ® ™ § ¶ † ‡ • … ‰ ′ ″ ‹ › « » ¡ ¿ ¢ £ ¤ ¥ ¦ § ¨ © ª « ¬ ® ¯",
            },
            {
                "name": "mathematical_symbols",
                "content": "± × ÷ ∂ ∆ ∏ ∑ − ∕ ∙ √ ∝ ∞ ∠ ∧ ∨ ∩ ∪ ∫ ∴ ∵ ∶ ∷ ≈ ≠ ≡ ≤ ≥",
            },
            {
                "name": "mixed_symbols_minimal_text",
                "content": "# @@@\n\n*** !!! $$$ %%% &&& ((( ))) [[[ ]]] {{{ }}} ||| \\\\\\\n\n## ???",
            },
        ]

        for case in symbol_cases:
            symbol_file = temp_dir / f"symbols_{case['name']}.md"
            symbol_file.write_text(case["content"], encoding="utf-8")

            result = processor.process_document(
                symbol_file, f"symbols-{case['name']}-test"
            )

            # Should handle symbol-heavy content
            if result.success:
                assert result.chunks_created >= 0
            # Some cases might legitimately fail if they're too sparse

    def test_binary_like_content_in_text(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test text files that contain binary-like content."""
        binary_like_cases = [
            {
                "name": "base64_content",
                "content": """# Document with Base64

Here's some base64 encoded content:

```
iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAGA6VP+lQAAAABJRU5ErkJggg==
```

More content after base64.
""",
            },
            {
                "name": "hex_dump",
                "content": """# Hex Dump Content

00000000  7f 45 4c 46 02 01 01 00  00 00 00 00 00 00 00 00  |.ELF............|
00000010  02 00 3e 00 01 00 00 00  78 00 40 00 00 00 00 00  |..>.....x.@.....|
00000020  40 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |@...............|

This is a hex dump in markdown.
""",
            },
            {
                "name": "uuencoded_content",
                "content": """# UUEncoded Content

begin 644 test.txt
%:&5L;&\\@=V]R;&0-
end

Content after UUEncode.
""",
            },
            {
                "name": "long_hash_strings",
                "content": """# Hash Values

SHA-256: a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3
MD5: 098f6bcd4621d373cade4e832627b4f6
SHA-1: 5d41402abc4b2a76b9719d911017c592

More hashes:
"""
                + "\n".join([f"Hash {i}: {'a1b2c3d4e5f6' * 10}" for i in range(100)]),
            },
        ]

        for case in binary_like_cases:
            binary_like_file = temp_dir / f"binary_like_{case['name']}.md"
            binary_like_file.write_text(case["content"], encoding="utf-8")

            result = processor.process_document(
                binary_like_file, f"binary-like-{case['name']}-test"
            )

            # Should handle binary-like text content successfully
            assert result.success is True
            assert result.chunks_created > 0
            assert result.error is None

    def test_content_with_zero_width_characters(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test content with zero-width Unicode characters."""
        zero_width_content = """# Document with Zero-Width Characters

This text contains zero-width characters that might cause issues:

- Zero Width Space (U+200B): ​between​words​
- Zero Width Non-Joiner (U+200C): ‌between‌words‌
- Zero Width Joiner (U+200D): ‍between‍words‍
- Word Joiner (U+2060): ⁠between⁠words⁠
- Invisible Separator (U+2063): ⁣between⁣words⁣

## Text with Mixed Zero-Width

Normal​text​with​zero​width​spaces​everywhere​in​this​paragraph.
This‌makes‌text‌look‌normal‌but‌has‌hidden‌characters.

### Code with Zero-Width

```python
def​function​with​zero​width():
    return​"hidden​characters"
```

## Conclusion

Zero-width characters can be tricky to handle.
"""

        zero_width_file = temp_dir / "zero_width.md"
        zero_width_file.write_text(zero_width_content, encoding="utf-8")

        result = processor.process_document(zero_width_file, "zero-width-test")

        # Should handle zero-width characters without issues
        assert result.success is True
        assert result.chunks_created > 0
        assert result.error is None

    def test_content_processing_with_different_validation_modes(
        self, temp_dir: Path, chunking_config: ChunkingConfig
    ) -> None:
        """Test content processing in strict vs graceful validation modes."""
        # Create problematic content that might behave differently in different modes
        problematic_content = """# Problematic Content

This document has various issues that might trigger different behaviors:

## Malformed Elements

**Bold without closing

*Italic without closing

[Link with no URL]

## Code Issues

```
Unclosed code block

## Next Section

This should test how different validation modes handle problematic content.

```python
# This code block is properly closed
def test():
    return "ok"
```

## Final Section

End of problematic document.
"""

        problem_file = temp_dir / "problematic_content.md"
        problem_file.write_text(problematic_content, encoding="utf-8")

        # Test strict mode
        strict_config = ProcessingConfig(strict_validation=True)
        strict_processor = DocumentProcessor(chunking_config, strict_config)

        strict_result = strict_processor.process_document(
            problem_file, "strict-content-test"
        )

        # Test graceful mode
        graceful_config = ProcessingConfig(strict_validation=False)
        graceful_processor = DocumentProcessor(chunking_config, graceful_config)

        graceful_result = graceful_processor.process_document(
            problem_file, "graceful-content-test"
        )

        # Both should succeed for content issues (vs file system issues)
        # The difference should be in how they handle edge cases, not basic malformed markdown
        assert strict_result.success is True
        assert graceful_result.success is True

        # Both should create some chunks
        assert strict_result.chunks_created > 0
        assert graceful_result.chunks_created > 0

    def test_extremely_nested_markdown(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of extremely deep nesting beyond normal use cases."""
        # Create deeply nested content
        nested_parts = ["# Extreme Nesting Test\n\n"]

        # Create 20 levels of nested blockquotes
        for i in range(20):
            nested_parts.append(">" * (i + 1) + f" Level {i + 1} blockquote\n")
            nested_parts.append(">" * (i + 1) + "\n")

        # Create 20 levels of nested lists
        nested_parts.append("\n## Deep List Nesting\n\n")
        for i in range(20):
            indent = "  " * i
            nested_parts.append(f"{indent}- Level {i + 1} list item\n")

        # Create deeply nested HTML-style structure
        nested_parts.append("\n## Deep HTML Nesting\n\n")
        for i in range(10):
            nested_parts.append(
                "<div>" * (i + 1)
                + f"Content at level {i + 1}"
                + "</div>" * (i + 1)
                + "\n\n"
            )

        extreme_content = "".join(nested_parts)

        extreme_file = temp_dir / "extreme_nesting.md"
        extreme_file.write_text(extreme_content, encoding="utf-8")

        result = processor.process_document(extreme_file, "extreme-nesting-test")

        # Should handle extreme nesting without crashing
        assert result.success is True
        assert result.chunks_created > 0
        assert result.error is None

    @pytest.mark.parametrize("chunk_size", [50, 100, 500, 1000, 5000])
    def test_content_processing_with_various_chunk_sizes(
        self, temp_dir: Path, chunk_size: int
    ) -> None:
        """Test content processing with different chunk sizes."""
        # Create content with known structure
        content = f"""# Test Document for Chunk Size {chunk_size}

This document is designed to test chunking behavior with different chunk sizes.

## Section 1

{"Content for section 1. " * 10}

## Section 2

{"Content for section 2. " * 10}

### Subsection 2.1

{"Content for subsection 2.1. " * 10}

### Subsection 2.2

{"Content for subsection 2.2. " * 10}

## Section 3

{"Content for section 3. " * 20}

```python
def example_function():
    '''This is a code example.'''
    return "Code content that should be chunked appropriately"
```

## Section 4

{"Final section content. " * 15}

### Conclusion

This concludes our test document.
"""

        # Create chunking config with specified size
        chunking_config = ChunkingConfig(
            chunk_size=chunk_size,
            overlap=min(50, chunk_size // 4),  # Reasonable overlap
            method="structure",
            respect_boundaries=True,
        )

        processor = DocumentProcessor(chunking_config)

        test_file = temp_dir / f"chunk_size_{chunk_size}.md"
        test_file.write_text(content, encoding="utf-8")

        result = processor.process_document(test_file, f"chunk-size-{chunk_size}-test")

        # Should succeed regardless of chunk size
        assert result.success is True
        assert result.chunks_created > 0
        assert result.error is None

        # Smaller chunk sizes should generally create more chunks
        # (though structure-based chunking might override this)
        if chunk_size <= 100:
            assert result.chunks_created >= 3  # Should create several small chunks
        elif chunk_size >= 5000:
            # Very large chunks might contain most content in fewer chunks
            assert result.chunks_created >= 1  # At least one chunk
