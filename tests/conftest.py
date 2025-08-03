"""Pytest configuration and fixtures."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from shard_markdown.chromadb.mock_client import MockChromaDBClient
from shard_markdown.config.settings import AppConfig, ChromaDBConfig
from shard_markdown.core.models import (
    ChunkingConfig,
    DocumentChunk,
    ProcessingResult,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_markdown_file(temp_dir):
    """Create sample markdown file for testing."""
    content = """
# Sample Document

This is a sample markdown document for testing purposes.

## Section 1

Here's some content in section 1.

### Subsection 1.1

More detailed content here.

## Section 2

Different content in section 2.

```python
def example_function():
    return "Hello, World!"
```

## Conclusion

That's the end of our sample document.
"""

    file_path = temp_dir / "sample.md"
    file_path.write_text(content.strip())
    return file_path


@pytest.fixture
def markdown_with_frontmatter(temp_dir):
    """Create markdown file with YAML frontmatter."""
    content = """---
title: "Test Document"
author: "Test Author"
tags:
  - test
  - markdown
date: "2024-01-01"
---

# Test Document with Frontmatter

This document has YAML frontmatter.

## Content Section

Regular markdown content follows the frontmatter.
"""

    file_path = temp_dir / "frontmatter.md"
    file_path.write_text(content.strip())
    return file_path


@pytest.fixture
def complex_markdown_file(temp_dir):
    """Create complex markdown file with various elements."""
    content = """
# Complex Document

This document has multiple types of content.

## Lists

### Unordered List
- Item 1
- Item 2
  - Nested item
  - Another nested item
- Item 3

### Ordered List
1. First item
2. Second item
3. Third item

## Code Blocks

### Python Code
```python
def calculate_sum(a, b):
    \"\"\"Calculate sum of two numbers.\"\"\"
    return a + b

result = calculate_sum(5, 3)
print(f"Result: {result}")
```

### JavaScript Code
```javascript
function greet(name) {
    return `Hello, ${name}!`;
}

console.log(greet("World"));
```

## Tables

| Name | Age | City |
|------|-----|------|
| Alice | 30 | New York |
| Bob | 25 | London |
| Charlie | 35 | Tokyo |

## Blockquotes

> This is a blockquote.
> It can span multiple lines.
>
> And have multiple paragraphs.

## Links and Images

Here's a [link to example.com](https://example.com).

![Sample Image](https://example.com/image.jpg)

## Emphasis

This text has **bold** and *italic* formatting.
You can also use __bold__ and _italic_ alternatives.

## Horizontal Rule

---

## Final Section

This concludes our complex document.
"""

    file_path = temp_dir / "complex.md"
    file_path.write_text(content.strip())
    return file_path


@pytest.fixture
def test_documents(temp_dir):
    """Create multiple test documents."""
    documents = {}

    # Document 1: Simple
    simple_content = """
# Simple Document

Just a simple document with basic content.

## One Section

Some content here.
"""
    simple_path = temp_dir / "simple.md"
    simple_path.write_text(simple_content.strip())
    documents["simple"] = simple_path

    # Document 2: Technical
    technical_content = """
# Technical Documentation

## Installation

```bash
pip install example-package
```

## Usage

```python
import example
result = example.process()
```

## Configuration

- Setting 1: Description
- Setting 2: Description
"""
    technical_path = temp_dir / "technical.md"
    technical_path.write_text(technical_content.strip())
    documents["technical"] = technical_path

    # Document 3: Blog post style
    blog_content = """
# My Blog Post

Published on January 1, 2024

## Introduction

This is a blog post about something interesting.

## Main Content

Here's the main content of the blog post.

### Subsection

More detailed information.

## Conclusion

Thanks for reading!
"""
    blog_path = temp_dir / "blog.md"
    blog_path.write_text(blog_content.strip())
    documents["blog"] = blog_path

    return documents


@pytest.fixture
def chunking_config():
    """Create default chunking configuration."""
    return ChunkingConfig(
        chunk_size=1000,
        overlap=200,
        method="structure",
        respect_boundaries=True,
    )


@pytest.fixture
def app_config():
    """Create test application configuration."""
    return AppConfig(
        chromadb=ChromaDBConfig(
            host="localhost",
            port=8000,
        ),
        chunking=ChunkingConfig(
            chunk_size=1000,
            overlap=200,
            method="structure",
        ),
    )


@pytest.fixture
def mock_chromadb_client():
    """Create mock ChromaDB client."""
    return MockChromaDBClient()


@pytest.fixture
def mock_processing_result():
    """Create mock processing result."""
    return ProcessingResult(
        file_path=Path("test.md"),
        success=True,
        chunks_created=3,
        processing_time=1.5,
        collection_name="test-collection",
    )


@pytest.fixture
def sample_chunks():
    """Create sample document chunks."""
    return [
        DocumentChunk(
            id="chunk_1",
            content="# Header 1\n\nSome content here.",
            metadata={"chunk_index": 0, "section": "Header 1"},
            start_position=0,
            end_position=30,
        ),
        DocumentChunk(
            id="chunk_2",
            content="## Header 2\n\nMore content.",
            metadata={"chunk_index": 1, "section": "Header 2"},
            start_position=31,
            end_position=60,
        ),
        DocumentChunk(
            id="chunk_3",
            content="### Header 3\n\nFinal content.",
            metadata={"chunk_index": 2, "section": "Header 3"},
            start_position=61,
            end_position=90,
        ),
    ]


@pytest.fixture
def cli_runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_collection_manager():
    """Create mock collection manager."""
    manager = Mock()
    manager.collection_exists.return_value = False
    manager.create_collection.return_value = True
    manager.list_collections.return_value = []
    manager.get_collection_info.return_value = {
        "name": "test-collection",
        "count": 0,
        "metadata": {},
    }
    return manager


@pytest.fixture
def large_document_content():
    """Create content for large document testing."""
    sections = []

    sections.append("# Large Document Test\n\n")
    sections.append("This is a large document created for testing purposes.\n\n")

    for i in range(50):
        sections.append(f"## Section {i + 1}\n\n")
        sections.append(
            f"This is the content for section {i + 1}. " * 10 + "\n\n"
        )

        if i % 5 == 0:
            sections.append("```python\n")
            sections.append(f"# Code example for section {i + 1}\n")
            sections.append(f"def function_{i + 1}():\n")
            sections.append(f'    return "Section {i + 1} result"\n')
            sections.append("```\n\n")

    return "".join(sections)


@pytest.fixture
def performance_documents(temp_dir, large_document_content):
    """Create multiple large documents for performance testing."""
    documents = []

    for i in range(20):
        doc_path = temp_dir / f"perf_doc_{i:02d}.md"
        doc_path.write_text(large_document_content)
        documents.append(doc_path)

    return documents
