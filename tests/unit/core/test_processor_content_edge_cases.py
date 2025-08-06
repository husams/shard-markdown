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
                "content": (
                    "# Document\n\nText with\x00null\x00chars\n\n## Section\n"
                    "More content"
                ),
            },
            {
                "name": "bell_characters",
                "content": (
                    "# Alert\n\nText with\x07bell\x07sounds\n\nContent continues"
                ),
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
                "content": (
                    "# Unix Header\n\nUnix paragraph.\n\r\n## Windows Header\r\n"
                    "\r\nWindows paragraph.\r\n"
                ),
            },
            {
                "name": "old_mac_style",
                "content": (
                    "# Old Mac\rContent with old Mac line endings\rAnother line\r"
                    "## Section\rMore content\r"
                ),
            },
            {
                "name": "all_three_mixed",
                "content": (
                    "# Mixed\nUnix line\r\nWindows line\rOld Mac line\n\n"
                    "Another Unix\r\n\r\nWindows paragraph\r"
                ),
            },
            {
                "name": "inconsistent_spacing",
                "content": (
                    "# Header\n \n  \n\t\n## Section\r\n  \r\n\t\r\n"
                    "### Subsection\r \r  \rContent\n"
                ),
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

```

### Tables with Complex Content

| Column 1 | Complex Column | Another |
|----------|----------------|---------|
| Simple   | > Quote in table | `code` |
| Lists    | - Item 1<br>- Item 2 | More |
| **Bold** | *Emphasis* | ~~Strike~~ |

"""

        complex_file = temp_dir / "complex_nesting.md"
        complex_file.write_text(complex_markdown, encoding="utf-8")

        result = processor.process_document(complex_file, "complex-nesting-test")

        # Complex nesting should be handled
        assert result.success is True
        assert result.chunks_created > 0
        assert result.error is None

    def test_markdown_with_edge_case_formatting(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test markdown with edge case formatting patterns."""
        edge_case_formatting = [
            {
                "name": "empty_headers",
                "content": (
                    "# \n\n## \n\n### Empty headers with content after\n\nContent"
                ),
            },
            {
                "name": "headers_with_special_chars",
                "content": (
                    "# Header with !@#$%^&*() symbols\n\n## Another @#$%\n\nContent"
                ),
            },
            {
                "name": "excessive_emphasis",
                "content": (
                    "***Bold and italic*** and **bold** and *italic* and ***more***"
                ),
            },
            {
                "name": "broken_markdown_syntax",
                "content": (
                    "# Valid header\n\n**Unclosed bold\n\n*Unclosed italic\n\nContent"
                ),
            },
            {
                "name": "mixed_code_styles",
                "content": (
                    "`inline` and ```block``` and ~~~fenced~~~ code styles mixed"
                ),
            },
        ]

        for case in edge_case_formatting:
            formatting_file = temp_dir / f"format_{case['name']}.md"
            formatting_file.write_text(case["content"], encoding="utf-8")

            result = processor.process_document(
                formatting_file, f"format-{case['name']}-test"
            )

            # Should handle formatting edge cases gracefully
            assert result.success is True
            assert result.chunks_created > 0
            assert result.error is None

    def test_files_with_unicode_edge_cases(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of various Unicode edge cases."""
        unicode_cases = [
            {
                "name": "emoji_heavy",
                "content": (
                    "# 🎉 Document with 😀 many 🚀 emojis 🌟\n\n"
                    "Content with 💯 emojis 🔥"
                ),
            },
            {
                "name": "mixed_scripts",
                "content": (
                    "# English, 中文, العربية, русский\n\nMixed script content here."
                ),
            },
            {
                "name": "right_to_left",
                "content": "# العنوان الرئيسي\n\nمحتوى باللغة العربية مع نص إضافي",
            },
            {
                "name": "combining_characters",
                "content": "# Café naïve résumé\n\nContent with combining diacritics",
            },
            {
                "name": "mathematical_symbols",
                "content": "# Math: α + β = γ, ∑, ∫, ∞\n\nMathematical content",
            },
            {
                "name": "currency_symbols",
                "content": "# Money: $, €, £, ¥, ₹, ₿\n\nFinancial content",
            },
        ]

        for case in unicode_cases:
            unicode_file = temp_dir / f"unicode_{case['name']}.md"
            unicode_file.write_text(case["content"], encoding="utf-8")

            result = processor.process_document(
                unicode_file, f"unicode-{case['name']}-test"
            )

            # Unicode should be handled properly
            assert result.success is True
            assert result.chunks_created > 0
            assert result.error is None

    def test_files_with_unusual_sizes(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test files with unusual sizes."""
        size_cases = [
            {
                "name": "extremely_long_line",
                "content": "# Header\n\n" + "x" * 10000 + "\n\nMore content",
            },
            {
                "name": "many_short_lines",
                "content": "# Header\n\n" + "Line.\n" * 1000,
            },
            {
                "name": "single_character",
                "content": "x",  # Single character (should fail validation)
            },
            {
                "name": "just_header",
                "content": "# Header Only",  # Just a header
            },
        ]

        for case in size_cases:
            size_file = temp_dir / f"size_{case['name']}.md"
            size_file.write_text(case["content"], encoding="utf-8")

            result = processor.process_document(size_file, f"size-{case['name']}-test")

            if case["name"] in ("single_character",):
                # These should fail validation
                assert result.success is False
                assert result.error is not None
            else:
                # Others should succeed
                assert result.success is True
                assert result.chunks_created > 0

    def test_files_with_malformed_markdown_structures(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test files with malformed markdown structures."""
        malformed_cases = [
            {
                "name": "unclosed_code_blocks",
                "content": (
                    "# Header\n\n```python\ncode without closing\n\nMore content"
                ),
            },
            {
                "name": "nested_code_blocks",
                "content": (
                    "# Header\n\n```\nOuter\n```inner```\nstill outer\n```\n\nContent"
                ),
            },
            {
                "name": "malformed_tables",
                "content": (
                    "# Header\n\n| Col 1 | Col 2\n|---|\nIncomplete table\n\nContent"
                ),
            },
            {
                "name": "broken_links",
                "content": (
                    "# Header\n\n[Broken link](incomplete\n\n[Another broken]()\n\n"
                    "Content"
                ),
            },
        ]

        for case in malformed_cases:
            malformed_file = temp_dir / f"malformed_{case['name']}.md"
            malformed_file.write_text(case["content"], encoding="utf-8")

            result = processor.process_document(
                malformed_file, f"malformed-{case['name']}-test"
            )

            # Should handle malformed markdown gracefully
            assert result.success is True
            assert result.chunks_created > 0
            assert result.error is None

    def test_files_with_minimal_meaningful_content(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test files with minimal but meaningful content."""
        minimal_cases = [
            {
                "name": "single_word_paragraph",
                "content": "# Header\n\nWord.",
            },
            {
                "name": "minimal_list",
                "content": "# Items\n\n- One\n- Two",
            },
            {
                "name": "just_quote",
                "content": "# Quote\n\n> Wisdom.",
            },
            {
                "name": "code_only",
                "content": "# Code\n\n```\nprint('hi')\n```",
            },
        ]

        for case in minimal_cases:
            minimal_file = temp_dir / f"minimal_{case['name']}.md"
            minimal_file.write_text(case["content"], encoding="utf-8")

            result = processor.process_document(
                minimal_file, f"minimal-{case['name']}-test"
            )

            # Minimal meaningful content should succeed
            assert result.success is True
            assert result.chunks_created > 0
            assert result.error is None

    def test_files_with_extensive_special_characters(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test files with extensive use of special characters."""
        special_char_cases = [
            {
                "name": "punctuation_heavy",
                "content": (
                    "# Title!!!\n\nContent with... many??? punctuation!!! marks???"
                ),
            },
            {
                "name": "markdown_symbols",
                "content": (
                    "# * ** *** _ __ ___ ` ``` > >> >>> - -- --- + ++ +++ "
                    "= == === ~ ~~ ~~~"
                ),
            },
            {
                "name": "brackets_and_parens",
                "content": "# [Title] (with) {various} <bracket> types\n\nContent",
            },
            {
                "name": "unicode_symbols",
                "content": (
                    "© ® ™ § ¶ † ‡ • … ‰ ′ ″ ‹ › « » ¡ ¿ ¢ £ ¤ ¥ ¦ § ¨ © ª « ¬ ® ¯"
                ),
            },
            {
                "name": "programming_symbols",
                "content": "# Code: && || != == >= <= ++ -- += -= *= /= %= &= |= ^=",
            },
            {
                "name": "mixed_symbols_minimal_text",
                "content": (
                    "# @@@\n\n*** !!! $$$ %%% &&& ((( ))) [[[ ]]] {{{ }}} ||| "
                    "\\\\\\\n\n## ???"
                ),
            },
        ]

        for case in special_char_cases:
            special_file = temp_dir / f"special_{case['name']}.md"
            special_file.write_text(case["content"], encoding="utf-8")

            result = processor.process_document(
                special_file, f"special-{case['name']}-test"
            )

            # Special characters should be handled
            assert result.success is True
            assert result.chunks_created > 0
            assert result.error is None

    def test_content_processing_consistency_across_modes(
        self,
        processor: DocumentProcessor,
        strict_processor: DocumentProcessor,
        temp_dir: Path,
    ) -> None:
        """Test that content processing is consistent across processing modes."""
        test_content = """# Test Document

This is a test document with some edge cases that should be handled
consistently across different processing modes.

## Section with Various Content

- List item with *emphasis*
- Another item with **strong** text
- `Code` in list item

> Quote with some content
> and multiple lines

```python
# Code block
def test_function():
    return "test"
```

### Subsection

More content here with [links](http://example.com) and other elements.

Final paragraph with various formatting: **bold**, *italic*, `code`, and normal text.
"""

        test_file = temp_dir / "consistency_test.md"
        test_file.write_text(test_content, encoding="utf-8")

        strict_result = strict_processor.process_document(test_file, "strict-test")
        graceful_result = processor.process_document(test_file, "graceful-test")

        # Both should succeed for content issues (vs file system issues)
        # The difference should be in how they handle edge cases, not basic
        # malformed markdown
        assert strict_result.success is True
        assert graceful_result.success is True

        # Both should produce chunks
        assert strict_result.chunks_created > 0
        assert graceful_result.chunks_created > 0

        # No errors for well-formed content
        assert strict_result.error is None
        assert graceful_result.error is None
