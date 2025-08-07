"""Unit tests for markdown parser."""

from shard_markdown.core.models import MarkdownAST
from shard_markdown.core.parser import MarkdownParser


class TestMarkdownParser:
    """Test cases for MarkdownParser."""

    def test_parse_simple_markdown(self):
        """Test parsing simple markdown content."""
        content = """
# Main Title

This is a paragraph with some text.

## Section Header

Another paragraph here.
"""
        parser = MarkdownParser()
        ast = parser.parse(content)

        assert isinstance(ast, MarkdownAST)
        assert len(ast.elements) > 0

        # Check headers
        headers = [e for e in ast.elements if e.type == "header"]
        assert len(headers) >= 2
        assert headers[0].level == 1
        assert "Main Title" in headers[0].text

    def test_parse_with_frontmatter(self):
        """Test parsing markdown with YAML frontmatter."""
        content = """---
title: "Test Document"
author: "Test Author"
---

# Document Title

Content goes here.
"""
        parser = MarkdownParser()
        ast = parser.parse(content)

        assert isinstance(ast, MarkdownAST)
        assert ast.frontmatter["title"] == "Test Document"
        assert ast.frontmatter["author"] == "Test Author"

        # Should still parse the content
        headers = [e for e in ast.elements if e.type == "header"]
        assert len(headers) >= 1

    def test_parse_code_blocks(self):
        """Test parsing code blocks."""
        content = """
# Code Example

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
"""
        parser = MarkdownParser()
        ast = parser.parse(content)

        code_blocks = [e for e in ast.elements if e.type == "code_block"]
        assert len(code_blocks) >= 2

        # Check language detection
        python_blocks = [cb for cb in code_blocks if cb.language == "python"]
        js_blocks = [cb for cb in code_blocks if cb.language == "javascript"]

        assert len(python_blocks) >= 1
        assert len(js_blocks) >= 1

    def test_parse_lists(self):
        """Test parsing various list types."""
        content = """
# Lists

## Unordered List
- Item 1
- Item 2
- Item 3

## Ordered List
1. First
2. Second
3. Third
"""
        parser = MarkdownParser()
        ast = parser.parse(content)

        # Parser creates list_item elements, not list elements
        list_items = [e for e in ast.elements if e.type == "list_item"]
        assert len(list_items) >= 6  # 3 unordered + 3 ordered items

    def test_parse_empty_content(self):
        """Test parsing empty or whitespace-only content."""
        parser = MarkdownParser()

        # Empty string
        ast = parser.parse("")
        assert isinstance(ast, MarkdownAST)
        assert len(ast.elements) == 0

        # Whitespace only
        ast = parser.parse("   \n\n  \t  \n")
        assert isinstance(ast, MarkdownAST)
        # May or may not have elements depending on implementation

    def test_parse_complex_structure(self):
        """Test parsing complex nested structures."""
        content = """
# Main Document

## Section 1

### Subsection 1.1

Content here.

#### Sub-subsection 1.1.1

More content.

## Section 2

Back to level 2.

### Subsection 2.1

Final content.
"""
        parser = MarkdownParser()
        ast = parser.parse(content)

        headers = [e for e in ast.elements if e.type == "header"]

        # Should have headers at different levels
        levels = [h.level for h in headers]
        assert 1 in levels
        assert 2 in levels
        assert 3 in levels
        assert 4 in levels

    def test_parse_malformed_frontmatter(self):
        """Test handling of malformed YAML frontmatter."""
        content = """---
title: "Test
author: Invalid YAML
---

# Document Title

Content goes here.
"""
        parser = MarkdownParser()
        # Should not raise exception, just ignore invalid frontmatter
        ast = parser.parse(content)

        assert isinstance(ast, MarkdownAST)
        # Should still parse the content
        headers = [e for e in ast.elements if e.type == "header"]
        assert len(headers) >= 1
