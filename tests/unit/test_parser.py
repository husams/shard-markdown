"""Unit tests for markdown parser - real parsing, no mocks."""

from shard_markdown.core.models import MarkdownAST
from shard_markdown.core.parser import MarkdownParser


class TestMarkdownParser:
    """Test MarkdownParser with real markdown content."""

    def test_parse_simple_markdown(self) -> None:
        """Test parsing simple markdown content."""
        content = """# Main Title

This is a paragraph with some text.

## Section Header

Another paragraph here."""

        parser = MarkdownParser()
        ast = parser.parse(content)

        assert isinstance(ast, MarkdownAST)
        assert len(ast.elements) > 0

        # Check headers
        headers = [e for e in ast.elements if e.type == "header"]
        assert len(headers) >= 2
        assert headers[0].level == 1
        assert "Main Title" in headers[0].text

    def test_parse_with_frontmatter(self) -> None:
        """Test parsing markdown with YAML frontmatter."""
        content = """---
title: "Test Document"
author: "Test Author"
tags: [markdown, test]
date: 2024-01-01
---

# Document Title

Content goes here."""

        parser = MarkdownParser()
        ast = parser.parse(content)

        assert isinstance(ast, MarkdownAST)
        assert ast.frontmatter["title"] == "Test Document"
        assert ast.frontmatter["author"] == "Test Author"
        assert "tags" in ast.frontmatter

        # Should still parse the content after frontmatter
        headers = [e for e in ast.elements if e.type == "header"]
        assert len(headers) >= 1

    def test_parse_code_blocks(self) -> None:
        """Test parsing various code blocks with languages."""
        content = """# Code Examples

Here's some Python code:

```python
def hello():
    return "Hello, World!"
```

And some JavaScript:

```javascript
function greet() {
    return "Hello!";
}
```

Inline code: `print("test")` is also supported."""

        parser = MarkdownParser()
        ast = parser.parse(content)

        code_blocks = [e for e in ast.elements if e.type == "code_block"]
        assert len(code_blocks) >= 2

        # Check language detection
        python_blocks = [cb for cb in code_blocks if cb.language == "python"]
        js_blocks = [cb for cb in code_blocks if cb.language == "javascript"]

        assert len(python_blocks) >= 1
        assert len(js_blocks) >= 1
        assert "def hello()" in python_blocks[0].text
        assert "function greet()" in js_blocks[0].text

    def test_parse_lists(self) -> None:
        """Test parsing various list types."""
        content = """# Lists

## Unordered List
- Item 1
- Item 2
- Item 3

## Ordered List
1. First
2. Second
3. Third

## Nested List
- Top level
  - Nested item 1
  - Nested item 2
- Back to top level"""

        parser = MarkdownParser()
        ast = parser.parse(content)

        # Parser creates list_item elements
        list_items = [e for e in ast.elements if e.type == "list_item"]
        assert len(list_items) >= 6  # At least 6 list items total

    def test_parse_empty_content(self) -> None:
        """Test parsing empty or whitespace-only content."""
        parser = MarkdownParser()

        # Empty string
        ast = parser.parse("")
        assert isinstance(ast, MarkdownAST)
        assert len(ast.elements) == 0

        # Whitespace only
        ast = parser.parse("   \n\n  \t  \n")
        assert isinstance(ast, MarkdownAST)
        # May have minimal elements or none

    def test_parse_complex_structure(self) -> None:
        """Test parsing complex nested structures."""
        content = """# Main Document

## Section 1

### Subsection 1.1

Content here with **bold** and *italic* text.

#### Sub-subsection 1.1.1

More content with a [link](https://example.com).

## Section 2

Back to level 2.

### Subsection 2.1

> This is a blockquote
> with multiple lines

Final content."""

        parser = MarkdownParser()
        ast = parser.parse(content)

        headers = [e for e in ast.elements if e.type == "header"]

        # Should have headers at different levels
        levels = [h.level for h in headers]
        assert 1 in levels
        assert 2 in levels
        assert 3 in levels
        assert 4 in levels

        # Check that content was parsed
        # (parser may not extract blockquotes as separate elements)
        # Just verify that the content exists somewhere in the parsed elements
        all_text = " ".join(e.text for e in ast.elements if e.text)
        assert "blockquote" in all_text or "multiple lines" in all_text

    def test_parse_malformed_frontmatter(self) -> None:
        """Test handling of malformed YAML frontmatter."""
        content = """---
title: "Test
author: Invalid YAML
---

# Document Title

Content goes here."""

        parser = MarkdownParser()
        # Should not raise exception, just handle gracefully
        ast = parser.parse(content)

        assert isinstance(ast, MarkdownAST)
        # Should still parse the content
        headers = [e for e in ast.elements if e.type == "header"]
        assert len(headers) >= 1

    def test_parse_tables(self) -> None:
        """Test parsing markdown tables."""
        content = """# Tables

| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Row 1    | Data     | Value    |
| Row 2    | More     | Info     |

More content after table."""

        parser = MarkdownParser()
        ast = parser.parse(content)

        # Tables might be parsed as table elements or paragraphs
        # depending on parser implementation
        assert len(ast.elements) > 0

    def test_parse_mixed_content(self) -> None:
        """Test parsing document with mixed content types."""
        content = """---
title: Mixed Content Test
---

# Main Title

Introduction paragraph with **bold** and *italic* text.

## Code Section

```python
# Python example
def process(data):
    return [x * 2 for x in data]
```

## List Section

1. First item
2. Second item with `inline code`
3. Third item

## Link Section

Visit [OpenAI](https://openai.com) for more info.

## Image Section

![Alt text](image.png)

---

Footer with horizontal rule above."""

        parser = MarkdownParser()
        ast = parser.parse(content)

        # Document should have various element types
        element_types = {e.type for e in ast.elements}

        assert "header" in element_types
        assert "paragraph" in element_types
        assert "code_block" in element_types
        assert "list_item" in element_types

        # Should have frontmatter
        assert ast.frontmatter.get("title") == "Mixed Content Test"

    def test_parse_special_characters(self) -> None:
        """Test parsing content with special characters."""
        content = r"""# Special Characters

This has \*escaped\* asterisks.

Math: $x^2 + y^2 = z^2$

Emoji: 🚀 🎉 😊

Special symbols: © ® ™ § ¶"""

        parser = MarkdownParser()
        ast = parser.parse(content)

        assert len(ast.elements) > 0
        # Should handle special characters without errors

    def test_parse_deeply_nested_lists(self) -> None:
        """Test parsing deeply nested list structures."""
        content = """# Nested Lists

- Level 1
  - Level 2
    - Level 3
      - Level 4
        - Level 5
      - Back to 4
    - Back to 3
  - Another Level 2
- Another Level 1"""

        parser = MarkdownParser()
        ast = parser.parse(content)

        list_items = [e for e in ast.elements if e.type == "list_item"]
        assert len(list_items) >= 5  # At least 5 list items

    def test_parse_html_in_markdown(self) -> None:
        """Test parsing markdown with embedded HTML."""
        content = """# HTML in Markdown

<div class="custom">
This is HTML content.
</div>

Regular markdown paragraph.

<span style="color: red;">Inline HTML</span> mixed with markdown."""

        parser = MarkdownParser()
        ast = parser.parse(content)

        # Should parse without errors
        assert len(ast.elements) > 0

    def test_parse_large_document_structure(self) -> None:
        """Test parsing a large, realistic document structure."""
        content = """---
title: Complete Documentation
version: 1.0.0
---

# Project Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Usage](#usage)
4. [API Reference](#api-reference)

## Introduction

This is a comprehensive guide to our project.

### Key Features

- **Feature 1**: Description
- **Feature 2**: Description
- **Feature 3**: Description

## Installation

### Requirements

- Python 3.8+
- Additional dependencies

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/example/repo.git
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Example

```python
from package import Module

module = Module()
result = module.process(data)
print(result)
```

### Advanced Configuration

| Option | Default | Description |
|--------|---------|-------------|
| debug  | False   | Enable debug |
| verbose| False   | Verbose output |

## API Reference

### `Module.process(data)`

Processes the input data.

**Parameters:**
- `data` (list): Input data

**Returns:**
- `result` (dict): Processed result

---

© 2024 Example Project"""

        parser = MarkdownParser()
        ast = parser.parse(content)

        # Should have parsed all major sections
        headers = [e for e in ast.elements if e.type == "header"]
        assert len(headers) >= 6

        # Should have at least one code block (parser may combine some)
        code_blocks = [e for e in ast.elements if e.type == "code_block"]
        assert len(code_blocks) >= 1

        # Should have frontmatter
        assert ast.frontmatter.get("title") == "Complete Documentation"
        assert ast.frontmatter.get("version") == "1.0.0"
