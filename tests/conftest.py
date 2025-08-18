"""Pytest configuration and fixtures."""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from shard_markdown.config.settings import AppConfig, ChromaDBConfig, ChunkingConfig
from shard_markdown.core.models import (
    DocumentChunk,
    MarkdownAST,
    MarkdownElement,
    ProcessingResult,
)

# Import ChromaDB fixtures
from tests.fixtures.chromadb_fixtures import chromadb_test_fixture  # noqa: F401


# Test data
SAMPLE_MARKDOWN = """# Test Document

This is a test document for markdown processing.

## Section 1

Some content in section 1.

## Section 2

More content in section 2.

```python
def hello():
    print("Hello World")
```

- List item 1
- List item 2
- List item 3
"""

SAMPLE_FRONTMATTER_MARKDOWN = """---
title: "Test Document"
author: "Test Author"
tags: ["test", "markdown"]
---

# Test Document with Frontmatter

This document has YAML frontmatter.
"""


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_config_dir(temp_dir: Path) -> Path:
    """Create a temporary config directory."""
    config_dir = temp_dir / ".shard-md"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def sample_md_file(temp_dir: Path) -> Path:
    """Create a sample markdown file for testing."""
    md_file = temp_dir / "test.md"
    md_file.write_text(SAMPLE_MARKDOWN)
    return md_file


@pytest.fixture
def sample_md_file_with_frontmatter(temp_dir: Path) -> Path:
    """Create a sample markdown file with frontmatter for testing."""
    md_file = temp_dir / "test_with_frontmatter.md"
    md_file.write_text(SAMPLE_FRONTMATTER_MARKDOWN)
    return md_file


@pytest.fixture
def multiple_md_files(temp_dir: Path) -> list[Path]:
    """Create multiple markdown files for batch testing."""
    files = []
    for i in range(3):
        md_file = temp_dir / f"test_{i}.md"
        content = f"# Document {i}\n\nContent for document {i}.\n"
        md_file.write_text(content)
        files.append(md_file)
    return files


@pytest.fixture
def nested_md_files(temp_dir: Path) -> list[Path]:
    """Create nested directory structure with markdown files."""
    # Create nested directories
    subdir1 = temp_dir / "subdir1"
    subdir2 = temp_dir / "subdir2"
    nested_dir = subdir1 / "nested"

    subdir1.mkdir()
    subdir2.mkdir()
    nested_dir.mkdir(parents=True)

    # Create files
    files = []

    # Root level
    root_file = temp_dir / "root.md"
    root_file.write_text("# Root Document\n\nContent at root level.\n")
    files.append(root_file)

    # Subdir1
    sub1_file = subdir1 / "sub1.md"
    sub1_file.write_text("# Subdir1 Document\n\nContent in subdir1.\n")
    files.append(sub1_file)

    # Subdir2
    sub2_file = subdir2 / "sub2.md"
    sub2_file.write_text("# Subdir2 Document\n\nContent in subdir2.\n")
    files.append(sub2_file)

    # Nested
    nested_file = nested_dir / "nested.md"
    nested_file.write_text("# Nested Document\n\nContent in nested dir.\n")
    files.append(nested_file)

    # Also create some non-markdown files that should be ignored
    (temp_dir / "readme.txt").write_text("Not markdown")
    (subdir1 / "config.json").write_text('{"test": true}')

    return files


@pytest.fixture
def app_config() -> AppConfig:
    """Provide a test application configuration."""
    return AppConfig(
        chromadb=ChromaDBConfig(host="localhost", port=8000),
        chunking=ChunkingConfig(default_size=500, default_overlap=100),
    )


@pytest.fixture
def chunking_config() -> ChunkingConfig:
    """Provide a test chunking configuration."""
    return ChunkingConfig(default_size=500, default_overlap=100)


@pytest.fixture
def sample_ast() -> MarkdownAST:
    """Provide a sample markdown AST for testing that matches SAMPLE_MARKDOWN."""
    elements = [
        # Header: # Test Document
        MarkdownElement(type="header", text="Test Document", level=1),
        # Paragraph: This is a test document for markdown processing.
        MarkdownElement(
            type="paragraph", text="This is a test document for markdown processing."
        ),
        # Header: ## Section 1
        MarkdownElement(type="header", text="Section 1", level=2),
        # Paragraph: Some content in section 1.
        MarkdownElement(type="paragraph", text="Some content in section 1."),
        # Header: ## Section 2
        MarkdownElement(type="header", text="Section 2", level=2),
        # Paragraph: More content in section 2.
        MarkdownElement(type="paragraph", text="More content in section 2."),
        # Code block: python code
        MarkdownElement(
            type="code_block",
            text='def hello():\n    print("Hello World")',
            language="python",
        ),
        # Note: The list is not included as a separate element in this simple fixture
    ]
    return MarkdownAST(elements=elements)


@pytest.fixture
def sample_chunks() -> list[DocumentChunk]:
    """Provide sample document chunks for testing."""
    return [
        DocumentChunk(
            id="chunk_0001",
            content="# Test Document\n\nThis is a test paragraph.",
            metadata={"chunk_index": 0, "source_file": "test.md"},
            start_position=0,
            end_position=47,
        ),
        DocumentChunk(
            id="chunk_0002",
            content="## Section 1\n\nContent in section 1.",
            metadata={"chunk_index": 1, "source_file": "test.md"},
            start_position=47,
            end_position=82,
        ),
    ]


@pytest.fixture
def mock_chromadb_client() -> Mock:
    """Provide a mock ChromaDB client for testing."""
    mock_client = Mock()
    mock_client.heartbeat.return_value = None
    mock_client.get_or_create_collection.return_value = Mock()
    return mock_client


@pytest.fixture
def processing_result() -> ProcessingResult:
    """Provide a sample processing result."""
    return ProcessingResult(
        file_path=Path("test.md"),
        success=True,
        chunks_created=2,
        processing_time=0.5,
    )


# Fixtures for E2E tests using the same names as in the E2E test files
@pytest.fixture
def sample_markdown_file(sample_md_file: Path) -> Path:
    """Alias for compatibility with E2E tests."""
    return sample_md_file


@pytest.fixture
def test_documents(multiple_md_files: list[Path]) -> dict[str, Path]:
    """Create test documents dict for compatibility with E2E tests."""
    return {f"doc_{i}": path for i, path in enumerate(multiple_md_files)}


@pytest.fixture(autouse=True)
def reset_env_vars() -> Generator[None, None, None]:
    """Reset environment variables after each test."""
    # Store original values
    original_env = {
        key: os.environ.get(key)
        for key in [
            "CHROMA_HOST",
            "CHROMA_PORT",
            "SHARD_MD_CHUNK_SIZE",
            "SHARD_MD_CHUNK_OVERLAP",
            "SHARD_MD_LOG_LEVEL",
        ]
    }

    yield

    # Restore original values
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
