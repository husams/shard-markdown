"""Pytest configuration and fixtures."""

import json
import tempfile
from pathlib import Path
from typing import Dict, Generator, List
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from shard_markdown.chromadb.mock_client import MockChromaDBClient
from shard_markdown.config.settings import AppConfig, ChromaDBConfig
from shard_markdown.core.models import (
    ChunkingConfig,
    DocumentChunk,
    MarkdownAST,
    MarkdownElement,
)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def cli_runner() -> CliRunner:
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_markdown_content() -> str:
    """Sample markdown content for testing."""
    return """# Main Title

This is the introduction paragraph.

## Section 1

This is a paragraph in section 1 with some content.

### Subsection 1.1

More content here with **bold** and *italic* text.

```python
def hello_world():
    print("Hello, World!")
```

## Section 2

Another section with different content.

- List item 1
- List item 2
- List item 3

Final paragraph with some concluding thoughts.
"""


@pytest.fixture
def complex_markdown_content() -> str:
    """Complex markdown content with frontmatter for testing."""
    return """---
title: "Complex Document"
author: "Test Author"
tags: ["test", "complex", "markdown"]
description: "A complex document for testing purposes"
---

# Complex Document

This document contains various markdown elements for comprehensive testing.

## Introduction

This is the introduction section with **bold** and *italic* text.

### Features

The document includes:

1. Ordered lists
2. Code blocks
3. Tables
4. Nested sections

## Code Examples

Here's a Python example:

```python
def complex_function(param1: str, param2: int) -> bool:
    \"\"\"A complex function with type hints.\"\"\"
    if param2 > 0:
        print(f"Processing: {param1}")
        return True
    return False
```

And some JavaScript:

```javascript
function processData(data) {
    return data.map(item => ({
        ...item,
        processed: true
    }));
}
```

## Data Table

| Feature | Support | Notes |
|---------|---------|-------|
| Headers | Yes | All levels |
| Code | Yes | Multiple languages |
| Lists | Yes | Ordered and unordered |

## Conclusion

This concludes our complex document example.
"""


@pytest.fixture
def frontmatter_document() -> str:
    """Document with YAML frontmatter."""
    return """---
title: "Test Document"
author: "Test Author"
tags:
  - test
  - documentation
date: "2024-01-01"
version: 1.0
---

# Test Document

This document has frontmatter that should be parsed correctly.

## Content

Regular markdown content follows the frontmatter.
"""


@pytest.fixture
def sample_markdown_file(temp_dir: Path, sample_markdown_content: str) -> Path:
    """Create a sample markdown file for testing."""
    file_path = temp_dir / "sample.md"
    file_path.write_text(sample_markdown_content)
    return file_path


@pytest.fixture
def complex_markdown_file(temp_dir: Path, complex_markdown_content: str) -> Path:
    """Create a complex markdown file for testing."""
    file_path = temp_dir / "complex.md"
    file_path.write_text(complex_markdown_content)
    return file_path


@pytest.fixture
def test_documents(temp_dir: Path) -> Dict[str, Path]:
    """Create multiple test documents for batch testing."""
    documents = {}

    # Simple document
    simple_content = """# Simple Document
This is a simple document with basic content.
## Section 1
Content for section 1.
"""
    simple_path = temp_dir / "simple.md"
    simple_path.write_text(simple_content)
    documents["simple"] = simple_path

    # Document with code
    code_content = """# Code Document
This document contains code examples.
```python
def example():
    return "Hello World"
```
## More Content
Additional content after code.
"""
    code_path = temp_dir / "code.md"
    code_path.write_text(code_content)
    documents["code"] = code_path

    # Large document
    large_content = "# Large Document\n\n"
    for i in range(50):
        large_content += f"## Section {i}\n"
        large_content += f"{'Content paragraph. ' * 20}\n\n"

    large_path = temp_dir / "large.md"
    large_path.write_text(large_content)
    documents["large"] = large_path

    return documents


@pytest.fixture
def sample_ast() -> MarkdownAST:
    """Sample MarkdownAST for testing."""
    elements = [
        MarkdownElement(type="header", level=1, text="Main Title"),
        MarkdownElement(type="paragraph", text="Introduction paragraph."),
        MarkdownElement(type="header", level=2, text="Section 1"),
        MarkdownElement(type="paragraph", text="Content for section 1."),
        MarkdownElement(
            type="code_block",
            language="python",
            text="def hello():\n    print('Hello')",
        ),
        MarkdownElement(type="header", level=2, text="Section 2"),
        MarkdownElement(type="paragraph", text="Final content."),
    ]
    return MarkdownAST(elements=elements)


@pytest.fixture
def sample_chunks() -> List[DocumentChunk]:
    """Sample document chunks for testing."""
    return [
        DocumentChunk(
            id="chunk_001",
            content="# Main Title\n\nIntroduction paragraph.",
            metadata={
                "chunk_index": 0,
                "total_chunks": 3,
                "source_file": "test.md",
                "chunk_method": "structure",
            },
            start_position=0,
            end_position=35,
        ),
        DocumentChunk(
            id="chunk_002",
            content="## Section 1\n\nContent for section 1.",
            metadata={
                "chunk_index": 1,
                "total_chunks": 3,
                "source_file": "test.md",
                "chunk_method": "structure",
            },
            start_position=35,
            end_position=70,
        ),
        DocumentChunk(
            id="chunk_003",
            content="## Section 2\n\nFinal content.",
            metadata={
                "chunk_index": 2,
                "total_chunks": 3,
                "source_file": "test.md",
                "chunk_method": "structure",
            },
            start_position=70,
            end_position=100,
        ),
    ]


@pytest.fixture
def default_config() -> AppConfig:
    """Default application configuration for testing."""
    return AppConfig()


@pytest.fixture
def test_config() -> AppConfig:
    """Test-specific application configuration."""
    return AppConfig(
        chromadb=ChromaDBConfig(
            host="localhost",
            port=8000,
            ssl=False,
            timeout=30
        )
    )


@pytest.fixture
def chunking_config() -> ChunkingConfig:
    """Default chunking configuration for testing."""
    return ChunkingConfig(chunk_size=500, overlap=100, method="structure")


@pytest.fixture
def mock_chromadb_client():
    """Mock ChromaDB client for testing."""
    return MockChromaDBClient()


@pytest.fixture
def config_file(temp_dir: Path) -> Path:
    """Create a test configuration file."""
    config_data = {
        "chromadb": {"host": "localhost", "port": 8000, "ssl": False},
        "chunking": {
            "default_size": 1000,
            "default_overlap": 200,
            "method": "structure",
        },
        "processing": {"batch_size": 10, "max_workers": 4},
    }

    config_path = temp_dir / "test_config.yaml"
    import yaml

    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    return config_path


@pytest.fixture
def malformed_markdown(temp_dir: Path) -> Path:
    """Create a malformed markdown file for error testing."""
    content = """# Invalid Document

This document has some issues.

```python
# This code block is not closed properly

def broken_function():
    return "missing closing backticks"

## Section without proper ending

This paragraph is
"""
    file_path = temp_dir / "malformed.md"
    file_path.write_text(content)
    return file_path


@pytest.fixture(autouse=True)
def cleanup_test_collections():
    """Clean up any test collections after each test."""
    yield
    # Cleanup code would go here if we had a real ChromaDB instance
    pass


# Performance test fixtures
@pytest.fixture
def large_document_content() -> str:
    """Generate large document content for performance testing."""
    content = ["# Performance Test Document\n\n"]

    for section in range(100):
        content.append(f"## Section {section + 1}\n\n")
        for para in range(10):
            content.append(f"This is paragraph {para + 1} of section {section + 1}. ")
            content.append("It contains meaningful content for testing performance. ")
            content.append("The content is long enough to create realistic chunks.\n\n")

    return "".join(content)


@pytest.fixture
def performance_documents(temp_dir: Path, large_document_content: str) -> List[Path]:
    """Create multiple large documents for performance testing."""
    documents = []

    for i in range(20):
        doc_path = temp_dir / f"perf_doc_{i:02d}.md"
        doc_path.write_text(large_document_content)
        documents.append(doc_path)

    return documents
