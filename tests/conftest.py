"""Pytest configuration and fixtures."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from shard_markdown.chromadb.mock_client import MockChromaDBClient
from shard_markdown.config.settings import AppConfig, ChromaDBConfig, ProcessingConfig
from shard_markdown.config.settings import ChunkingConfig as SettingsChunkingConfig
from shard_markdown.core.models import ChunkingConfig as ModelsChunkingConfig
from shard_markdown.core.models import (
    DocumentChunk,
    MarkdownAST,
    ProcessingResult,
)

# Import test utilities for shared fixtures
from tests.utils.helpers import (
    DataGenerator,
    FileHelper,
    MockHelper,
)


# =============================================================================
# Core Test Fixtures
# =============================================================================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


# =============================================================================
# Configuration Fixtures
# =============================================================================


@pytest.fixture
def chunking_config() -> ModelsChunkingConfig:
    """Create default chunking configuration for core models."""
    return MockHelper.create_mock_chunking_config(
        chunk_size=300,
        overlap=50,
        method="structure",
        respect_boundaries=True,
    )


@pytest.fixture
def app_config() -> AppConfig:
    """Create test application configuration."""
    return AppConfig(
        chromadb=ChromaDBConfig(
            host="localhost",
            port=8000,
        ),
        chunking=SettingsChunkingConfig(
            default_size=300,
            default_overlap=50,
            method="structure",
        ),
    )


@pytest.fixture
def test_processing_config() -> ProcessingConfig:
    """Create test processing configuration with sensible defaults for testing.

    This factory provides a ProcessingConfig optimized for testing scenarios
    while maintaining backward compatibility.
    """
    return MockHelper.create_mock_processing_config(
        batch_size=1,  # Process one file at a time for predictable tests
        max_workers=1,  # Single worker to avoid concurrency issues in tests
        max_file_size=1_000_000,  # 1MB limit for test files
        recursive=False,
        pattern="*.md",
        include_frontmatter=True,
        include_path_metadata=True,
        skip_empty_files=True,
        strict_validation=False,
        encoding="utf-8",
        encoding_fallback="latin-1",
        enable_encoding_detection=True,
    )


@pytest.fixture
def minimal_processing_config() -> ProcessingConfig:
    """Create minimal processing configuration for backward compatibility tests."""
    return ProcessingConfig(
        batch_size=5,
        max_workers=2,
        recursive=True,
        # All other fields should use defaults
    )


@pytest.fixture
def production_processing_config() -> ProcessingConfig:
    """Create production-like processing configuration for integration tests."""
    return ProcessingConfig(
        batch_size=10,  # Default production batch size
        max_workers=4,  # Default production worker count
        max_file_size=10_000_000,  # Default 10MB limit
        recursive=True,
        pattern="**/*.md",
        include_frontmatter=True,
        include_path_metadata=True,
        skip_empty_files=True,
        strict_validation=False,
        encoding="utf-8",
        encoding_fallback="latin-1",
        enable_encoding_detection=True,
    )


@pytest.fixture
def config_file(temp_dir: Path) -> Path:
    """Create a temporary configuration file for testing."""
    config_content = """
chromadb:
  host: localhost
  port: 8000

chunking:
  default_size: 300
  default_overlap: 50
  method: structure

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"""

    config_path = temp_dir / "config.yaml"
    config_path.write_text(config_content.strip())
    return config_path


# =============================================================================
# File Creation Fixtures
# =============================================================================


@pytest.fixture
def sample_markdown_file(temp_dir: Path) -> Path:
    """Create sample markdown file for testing."""
    content = """# Sample Document

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
    return FileHelper.create_markdown_file(temp_dir, "sample.md", content.strip())


@pytest.fixture
def markdown_with_frontmatter(temp_dir: Path) -> Path:
    """Create markdown file with YAML frontmatter."""
    return FileHelper.create_frontmatter_file(temp_dir, "frontmatter.md")


@pytest.fixture
def complex_markdown_file(temp_dir: Path) -> Path:
    """Create complex markdown file with various elements."""
    templates = DataGenerator.generate_markdown_content_templates()
    return FileHelper.create_markdown_file(temp_dir, "complex.md", templates["complex"])


@pytest.fixture
def unicode_markdown_file(temp_dir: Path) -> Path:
    """Create markdown file with Unicode content."""
    return FileHelper.create_unicode_markdown_file(temp_dir, "unicode.md")


@pytest.fixture
def empty_markdown_file(temp_dir: Path) -> Path:
    """Create empty markdown file."""
    return FileHelper.create_empty_file(temp_dir, "empty.md")


@pytest.fixture
def whitespace_markdown_file(temp_dir: Path) -> Path:
    """Create markdown file with only whitespace."""
    return FileHelper.create_whitespace_file(temp_dir, "whitespace.md")


@pytest.fixture
def large_markdown_file(temp_dir: Path) -> Path:
    """Create large markdown file for performance testing."""
    return FileHelper.create_large_markdown_file(
        temp_dir, "large.md", num_sections=50, content_multiplier=10
    )


@pytest.fixture
def test_documents(temp_dir: Path) -> dict[str, Path]:
    """Create multiple test documents with different content types."""
    documents = {}
    templates = DataGenerator.generate_markdown_content_templates()

    for doc_type, content in templates.items():
        file_path = FileHelper.create_markdown_file(temp_dir, f"{doc_type}.md", content)
        documents[doc_type] = file_path

    return documents


@pytest.fixture
def performance_documents(temp_dir: Path) -> list[Path]:
    """Create multiple documents for performance testing."""
    return DataGenerator.generate_performance_test_files(
        temp_dir, count=20, size_per_file=5000
    )


# =============================================================================
# Mock Object Fixtures
# =============================================================================


@pytest.fixture
def mock_chromadb_client() -> MockChromaDBClient:
    """Create mock ChromaDB client."""
    return MockChromaDBClient()


@pytest.fixture
def mock_collection_manager() -> Mock:
    """Create mock collection manager."""
    return MockHelper.create_mock_collection_manager()


@pytest.fixture
def mock_processor() -> Mock:
    """Create mock document processor."""
    processor = Mock()
    processor.process_file.return_value = MockHelper.create_mock_processing_result(
        file_path="test.md",
        success=True,
        chunks_created=5,
        processing_time=2.5,
        collection_name="test-collection",
    )
    processor.process_directory.return_value = [
        MockHelper.create_mock_processing_result(
            file_path="doc1.md",
            success=True,
            chunks_created=3,
            processing_time=1.2,
            collection_name="test-collection",
        ),
        MockHelper.create_mock_processing_result(
            file_path="doc2.md",
            success=True,
            chunks_created=4,
            processing_time=1.8,
            collection_name="test-collection",
        ),
    ]
    return processor


# =============================================================================
# Data Model Fixtures
# =============================================================================


@pytest.fixture
def mock_processing_result() -> ProcessingResult:
    """Create mock processing result."""
    return MockHelper.create_mock_processing_result(
        file_path=Path("test.md"),
        success=True,
        chunks_created=3,
        processing_time=1.5,
        collection_name="test-collection",
    )


@pytest.fixture
def sample_chunks() -> list[DocumentChunk]:
    """Create sample document chunks."""
    return DataGenerator.generate_test_chunks(count=3)


@pytest.fixture
def sample_ast() -> MarkdownAST:
    """Create sample markdown AST for testing."""
    return MockHelper.create_mock_markdown_ast()


@pytest.fixture
def sample_markdown_content() -> str:
    """Provide sample markdown content for testing."""
    templates = DataGenerator.generate_markdown_content_templates()
    return templates["technical"]  # Use technical template as default


# =============================================================================
# Performance Testing Fixtures
# =============================================================================


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
def benchmark_config() -> dict:
    """Create benchmark configuration for performance tests."""
    return {
        "min_rounds": 5,
        "max_time": 1.0,
        "disable_gc": False,
        "warmup": False,
        "sort": "min",
        "group": "group",
        "timer": "time.perf_counter",
    }


# =============================================================================
# Size and Edge Case Testing Fixtures
# =============================================================================


@pytest.fixture
def file_at_size_limit(temp_dir: Path) -> Path:
    """Create file exactly at a specific size limit for testing."""
    return FileHelper.create_file_at_size(temp_dir, "size_limit.md", 1000)


@pytest.fixture
def file_over_size_limit(temp_dir: Path) -> Path:
    """Create file over a specific size limit for testing."""
    return FileHelper.create_file_at_size(temp_dir, "over_limit.md", 1001)


@pytest.fixture
def binary_file(temp_dir: Path) -> Path:
    """Create binary file for error testing."""
    return FileHelper.create_binary_file(temp_dir, "binary.md")


# =============================================================================
# Parameterized Testing Fixtures
# =============================================================================


@pytest.fixture(params=[50, 100, 500, 1000, 2000])
def chunk_sizes(request) -> int:
    """Parametrized fixture for different chunk sizes."""
    return request.param


@pytest.fixture(params=["structure", "fixed", "semantic"])
def chunking_methods(request) -> str:
    """Parametrized fixture for different chunking methods."""
    return request.param


@pytest.fixture(params=[1, 2, 4, 8])
def worker_counts(request) -> int:
    """Parametrized fixture for different worker counts."""
    return request.param


@pytest.fixture(params=["utf-8", "latin-1", "ascii"])
def encodings(request) -> str:
    """Parametrized fixture for different encodings."""
    return request.param
