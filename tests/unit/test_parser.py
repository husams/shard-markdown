"""Unit tests for markdown parser."""

import pytest

from shard_markdown.core.models import MarkdownAST, MarkdownElement
from shard_markdown.core.parser import MarkdownParser


class TestMarkdownParser:
    """Test cases for MarkdownParser."""

    def test_parser_initialization(self):
        """Test parser initializes correctly."""
        parser = MarkdownParser()
        assert parser.md is not None

    def test_parse_simple_markdown(self, sample_markdown_content: str):
        """Test parsing simple markdown content."""
        parser = MarkdownParser()
        ast = parser.parse(sample_markdown_content)

        assert isinstance(ast, MarkdownAST)
        assert len(ast.elements) > 0

        # Check for headers
        headers = [e for e in ast.elements if e.type == "header"]
        assert len(headers) >= 3  # Main Title, Section 1, Section 2

        # Check header levels
        main_title = next(e for e in headers if e.text == "Main Title")
        assert main_title.level == 1

        section1 = next(e for e in headers if e.text == "Section 1")
        assert section1.level == 2

    def test_parse_with_frontmatter(self):
        """Test parsing markdown with frontmatter."""
        content = """---
title: Test Document
author: Test Author
tags:
  - test
  - markdown
---

# Main Content

This is the main content.
"""
        parser = MarkdownParser()
        ast = parser.parse(content)

        assert ast.frontmatter["title"] == "Test Document"
        assert ast.frontmatter["author"] == "Test Author"
        assert "test" in ast.frontmatter["tags"]

        # Check content was parsed
        headers = [e for e in ast.elements if e.type == "header"]
        assert len(headers) >= 1
        assert headers[0].text == "Main Content"

    def test_parse_code_blocks(self):
        """Test parsing code blocks."""
        content = """# Code Example

Here's some Python code:

```python
def hello():
    print("Hello, World!")
    return True
```

And some JavaScript:

```javascript
function hello() {
    console.log("Hello, World!");
}
```
"""
        parser = MarkdownParser()
        ast = parser.parse(content)

        code_blocks = [e for e in ast.elements if e.type == "code_block"]
        assert len(code_blocks) == 2

        python_block = next(e for e in code_blocks if e.language == "python")
        assert "def hello():" in python_block.text

        js_block = next(e for e in code_blocks if e.language == "javascript")
        assert "function hello()" in js_block.text

    def test_parse_lists(self):
        """Test parsing lists."""
        content = """# Lists

## Unordered List

- Item 1
- Item 2
- Item 3

## Ordered List

1. First item
2. Second item
3. Third item
"""
        parser = MarkdownParser()
        ast = parser.parse(content)

        lists = [e for e in ast.elements if e.type == "list"]
        assert len(lists) == 2

        # Check list items
        for list_elem in lists:
            assert list_elem.items is not None
            assert len(list_elem.items) == 3

    def test_extract_frontmatter_only(self):
        """Test extracting frontmatter from content."""
        content = """---
title: Test
description: A test document
---

# Content

Some content here.
"""
        parser = MarkdownParser()
        frontmatter, content_without_fm = parser.extract_frontmatter(content)

        assert frontmatter["title"] == "Test"
        assert frontmatter["description"] == "A test document"
        assert content_without_fm.strip().startswith("# Content")

    def test_parse_empty_content(self):
        """Test parsing empty content."""
        parser = MarkdownParser()
        ast = parser.parse("")

        assert isinstance(ast, MarkdownAST)
        assert len(ast.elements) == 0
        assert len(ast.frontmatter) == 0

    def test_parse_invalid_frontmatter(self):
        """Test parsing with invalid frontmatter."""
        content = """---
invalid: yaml: content: here
---

# Content

Some content.
"""
        parser = MarkdownParser()
        # Should not raise exception, just ignore invalid frontmatter
        ast = parser.parse(content)

        assert isinstance(ast, MarkdownAST)
        # Should still parse the content
        headers = [e for e in ast.elements if e.type == "header"]
        assert len(headers) >= 1
