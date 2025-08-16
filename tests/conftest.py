"""Pytest configuration and fixtures."""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from shard_markdown.config.settings import AppConfig, ChromaDBConfig
from shard_markdown.config.settings import ChunkingConfig as SettingsChunkingConfig
from shard_markdown.core.models import ChunkingConfig as ModelsChunkingConfig
from shard_markdown.core.models import (
    DocumentChunk,
    MarkdownAST,
    MarkdownElement,
    ProcessingResult,
)

# Import ChromaDB test fixtures
from tests.fixtures.chromadb_fixtures import (
    chromadb_test_client,  # noqa: F401
    chromadb_test_fixture,  # noqa: F401
    test_collection,  # noqa: F401
    wait_for_chromadb,
)
from tests.fixtures.mock import MockChromaDBClient


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_markdown_file(temp_dir: Path) -> Path:
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
def markdown_with_frontmatter(temp_dir: Path) -> Path:
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
def complex_markdown_file(temp_dir: Path) -> Path:
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
def test_documents(temp_dir: Path) -> dict[str, Path]:
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
def chunking_config() -> ModelsChunkingConfig:
    """Create default chunking configuration for core models."""
    return ModelsChunkingConfig(
        chunk_size=1000,
        overlap=200,
        method="structure",
        respect_boundaries=True,
    )


@pytest.fixture
def app_config() -> AppConfig:
    """Create test application configuration."""
    import os

    # Use environment variables from CI or default to 8000 for consistency
    host = os.getenv("CHROMA_HOST", "localhost")
    port = int(os.getenv("CHROMA_PORT", "8000"))
    return AppConfig(
        chromadb=ChromaDBConfig(
            host=host,
            port=port,
        ),
        chunking=SettingsChunkingConfig(
            default_size=1000,
            default_overlap=200,
            method="structure",
        ),
    )


@pytest.fixture
def mock_chromadb_client() -> MockChromaDBClient:
    """Create mock ChromaDB client."""
    return MockChromaDBClient()


@pytest.fixture
def mock_processing_result() -> ProcessingResult:
    """Create mock processing result."""
    return ProcessingResult(
        file_path=Path("test.md"),
        success=True,
        chunks_created=3,
        processing_time=1.5,
        collection_name="test-collection",
    )


@pytest.fixture
def sample_chunks() -> list[DocumentChunk]:
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
def sample_ast() -> MarkdownAST:
    """Create sample markdown AST for testing."""
    elements = [
        MarkdownElement(type="header", text="Main Title", level=1),
        MarkdownElement(type="paragraph", text="This is the introduction paragraph."),
        MarkdownElement(type="header", text="Section 1", level=2),
        MarkdownElement(type="paragraph", text="Content for section 1."),
        MarkdownElement(type="header", text="Section 2", level=2),
        MarkdownElement(type="paragraph", text="Content for section 2."),
        MarkdownElement(
            type="code_block",
            text="def hello():\n    return 'Hello, World!'",
            language="python",
        ),
    ]

    return MarkdownAST(
        elements=elements,
        frontmatter={"title": "Sample Document", "author": "Test Author"},
        metadata={"word_count": 50, "reading_time": 1},
    )


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_collection_manager() -> Mock:
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
def large_document_content() -> str:
    """Create content for large document testing."""
    sections = []

    sections.append("# Large Document Test\n\n")
    sections.append("This is a large document created for testing purposes.\n\n")

    for i in range(50):
        sections.append(f"## Section {i + 1}\n\n")
        sections.append(f"This is the content for section {i + 1}. " * 10 + "\n\n")

        if i % 5 == 0:
            sections.append("```python\n")
            sections.append(f"# Code example for section {i + 1}\n")
            sections.append(f"def function_{i + 1}():\n")
            sections.append(f'    return "Section {i + 1} result"\n')
            sections.append("```\n\n")

    return "".join(sections)


@pytest.fixture
def performance_documents(temp_dir: Path, large_document_content: str) -> list[Path]:
    """Create multiple large documents for performance testing."""
    documents = []

    for i in range(20):
        doc_path = temp_dir / f"perf_doc_{i:02d}.md"
        doc_path.write_text(large_document_content)
        documents.append(doc_path)

    return documents


@pytest.fixture
def benchmark_settings() -> dict:
    """Create pytest-benchmark configuration settings for performance tests."""
    import os

    # Use more realistic max_time, especially in CI environments
    max_time = float(os.getenv("BENCHMARK_MAX_TIME", "5.0"))  # 5 seconds default
    return {
        "min_rounds": 5,
        "max_time": max_time,
        "disable_gc": False,
        "warmup": False,
        "sort": "min",
        "group": "group",
        "timer": "time.perf_counter",
    }


@pytest.fixture
def config_file(temp_dir: Path) -> Path:
    """Create a temporary configuration file for testing."""
    import os

    # Use environment variables from CI or default to 8000 for consistency
    host = os.getenv("CHROMA_HOST", "localhost")
    port = int(os.getenv("CHROMA_PORT", "8000"))
    config_content = f"""
chromadb:
  host: {host}
  port: {port}

chunking:
  default_size: 1000
  default_overlap: 200
  method: structure

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"""

    config_path = temp_dir / "config.yaml"
    config_path.write_text(config_content.strip())
    return config_path


@pytest.fixture
def sample_markdown_content() -> str:
    """Provide sample markdown content for testing."""
    return """# Sample Document

This is a sample markdown document for testing purposes.

## Section 1

Here's some content in section 1 with enough text to make it meaningful for
chunking tests.

### Subsection 1.1

More detailed content here that provides additional context and information.

## Section 2

Different content in section 2 with various formatting elements.

```python
def example_function():
    return "Hello, World!"
```

### Code Examples

Here are some code examples:

```javascript
function greet(name) {
    return `Hello, ${name}!`;
}
```

## Conclusion

That's the end of our sample document with enough content for testing.
"""


@pytest.fixture
def mock_processor() -> Mock:
    """Create mock document processor."""
    processor = Mock()
    processor.process_file.return_value = ProcessingResult(
        file_path=Path("test.md"),
        success=True,
        chunks_created=5,
        processing_time=2.5,
        collection_name="test-collection",
    )
    processor.process_directory.return_value = [
        ProcessingResult(
            file_path=Path("doc1.md"),
            success=True,
            chunks_created=3,
            processing_time=1.2,
            collection_name="test-collection",
        ),
        ProcessingResult(
            file_path=Path("doc2.md"),
            success=True,
            chunks_created=4,
            processing_time=1.8,
            collection_name="test-collection",
        ),
    ]
    return processor


# pytest hooks for test setup
def pytest_configure(config: Any) -> None:
    """Configure pytest with custom markers and settings.

    Args:
        config: pytest configuration object
    """
    # Register custom markers
    config.addinivalue_line("markers", "chromadb: mark test as requiring ChromaDB")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "slow: mark test as slow")

    # In CI environment, wait for ChromaDB if tests need it
    is_ci = os.environ.get("CI") == "true"
    is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"

    if is_ci or is_github_actions:
        # Check if we're actually running tests that need ChromaDB (not excluding them)
        markexpr = getattr(config.option, "markexpr", "") or ""

        # Check if ChromaDB tests are being run (not excluded)
        needs_chromadb = False
        if markexpr:
            # Check if we're NOT excluding ChromaDB tests
            # We need ChromaDB if:
            # 1. Running chromadb/e2e/integration tests (positive selection)
            # 2. NOT explicitly excluding them with "not chromadb", etc.
            for marker in ["chromadb", "e2e", "integration"]:
                # Check if marker is positively selected or not negated
                if f"not {marker}" not in markexpr and marker in markexpr:
                    needs_chromadb = True
                    break
        else:
            # No mark expression means all tests are being run, including ChromaDB tests
            needs_chromadb = True

        if needs_chromadb:
            host = os.environ.get("CHROMA_HOST", "localhost")
            port = int(
                os.environ.get("CHROMA_PORT", "8000")
            )  # Use 8000 as default for CI consistency
            print(f"CI Environment detected. Waiting for ChromaDB at {host}:{port}...")
            if wait_for_chromadb(host, port, timeout=60):
                print("ChromaDB is ready for testing")
            else:
                print("Warning: ChromaDB not available, some tests may fail")


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """Modify test collection to add markers and skip conditions.

    Args:
        config: pytest configuration object
        items: List of test items
    """
    # Skip ChromaDB tests if ChromaDB is not available
    skip_chromadb = os.environ.get("SKIP_CHROMADB_TESTS") == "true"

    if skip_chromadb:
        skip_marker = pytest.mark.skip(reason="SKIP_CHROMADB_TESTS is set")
        for item in items:
            if "chromadb" in item.keywords:
                item.add_marker(skip_marker)
