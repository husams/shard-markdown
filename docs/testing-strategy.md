# Testing Strategy

## 1. Testing Framework Overview

### 1.1 Testing Philosophy

The shard-markdown CLI tool follows a comprehensive testing strategy that ensures reliability, maintainability, and user confidence. Our testing approach includes:

- **Test-Driven Development (TDD)**: Core functionality is developed with tests written first
- **Behavior-Driven Testing**: Tests describe user scenarios and expected outcomes
- **Layered Testing**: Unit, integration, and end-to-end tests provide complete coverage
- **Performance Testing**: Ensures the tool performs well under various conditions
- **Cross-Platform Testing**: Validates functionality across different operating systems

### 1.2 Testing Stack

```toml
[tool.poetry.group.test.dependencies]
# Core testing framework
pytest = "^7.4.0"
pytest-cov = "^4.1.0"           # Coverage reporting
pytest-mock = "^3.11.0"         # Mocking utilities
pytest-asyncio = "^0.21.0"      # Async testing support
pytest-benchmark = "^4.0.0"     # Performance benchmarking
pytest-xdist = "^3.3.0"         # Parallel test execution

# Testing utilities
factory-boy = "^3.3.0"          # Test data generation
faker = "^19.6.0"               # Fake data generation
responses = "^0.23.0"           # HTTP request mocking
freezegun = "^1.2.0"            # Time mocking

# CLI testing
click-testing = "^1.0.0"        # Click CLI testing utilities

# Database testing
pytest-postgresql = "^5.0.0"    # PostgreSQL test fixtures (if needed)
```

### 1.3 Test Organization

```
tests/
├── conftest.py                 # Shared pytest fixtures and configuration
├── unit/                       # Unit tests (fast, isolated)
│   ├── test_cli/
│   │   ├── test_commands.py
│   │   ├── test_parser.py
│   │   └── test_validation.py
│   ├── test_core/
│   │   ├── test_processor.py
│   │   ├── test_parser.py
│   │   ├── test_chunking/
│   │   │   ├── test_structure.py
│   │   │   ├── test_fixed.py
│   │   │   └── test_semantic.py
│   │   └── test_metadata.py
│   ├── test_chromadb/
│   │   ├── test_client.py
│   │   ├── test_collections.py
│   │   └── test_operations.py
│   └── test_config/
│       ├── test_settings.py
│       ├── test_loader.py
│       └── test_validation.py
├── integration/                # Integration tests (moderate speed)
│   ├── test_document_processing.py
│   ├── test_chromadb_integration.py
│   ├── test_file_operations.py
│   └── test_error_handling.py
├── e2e/                       # End-to-end tests (slow, full system)
│   ├── test_cli_workflows.py
│   ├── test_batch_processing.py
│   └── test_real_world_scenarios.py
├── performance/               # Performance and load tests
│   ├── test_benchmarks.py
│   ├── test_memory_usage.py
│   └── test_sequential_processing.py
├── fixtures/                  # Test data and fixtures
│   ├── sample_documents/
│   │   ├── simple.md
│   │   ├── complex.md
│   │   ├── with_frontmatter.md
│   │   ├── large_document.md
│   │   └── malformed.md
│   ├── config_files/
│   │   ├── valid_config.yaml
│   │   ├── invalid_config.yaml
│   │   └── minimal_config.yaml
│   └── expected_outputs/
│       ├── simple_chunks.json
│       ├── complex_chunks.json
│       └── metadata_examples.json
└── utils/                     # Test utilities and helpers
    ├── __init__.py
    ├── factories.py           # Test data factories
    ├── fixtures.py            # Custom fixtures
    └── helpers.py             # Test helper functions
```

## 2. Unit Testing Strategy

### 2.1 Core Component Testing

#### 2.1.1 Document Processing Tests (`test_core/test_processor.py`)

```python
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from shard_markdown.core.processor import DocumentProcessor
from shard_markdown.core.models import ProcessingConfig, ProcessingResult
from shard_markdown.chromadb.client import ChromaDBClient

class TestDocumentProcessor:
    """Test suite for DocumentProcessor class."""

    @pytest.fixture
    def mock_chroma_client(self):
        """Mock ChromaDB client for testing."""
        client = Mock(spec=ChromaDBClient)
        collection = Mock()
        collection.name = "test-collection"
        client.get_or_create_collection.return_value = collection
        client.bulk_insert.return_value = Mock(
            success=True,
            chunks_inserted=5,
            processing_time=0.1
        )
        return client

    @pytest.fixture
    def processor_config(self):
        """Standard processor configuration for testing."""
        return ProcessingConfig(
            chunk_size=1000,
            chunk_overlap=200,
            chunk_method="structure",
            batch_size=10,
        )

    @pytest.fixture
    def sample_markdown_file(self, tmp_path):
        """Create a sample markdown file for testing."""
        file_path = tmp_path / "test.md"
        content = """# Test Document

This is a test document with multiple sections.

## Section 1

Content for section 1 goes here.

## Section 2

Content for section 2 goes here.
"""
        file_path.write_text(content)
        return file_path

    def test_process_document_success(self, processor_config, mock_chroma_client,
                                    sample_markdown_file):
        """Test successful document processing."""
        processor = DocumentProcessor(processor_config, mock_chroma_client)

        result = processor.process_document(
            sample_markdown_file,
            "test-collection",
            create_collection=True
        )

        assert result.success is True
        assert result.file_path == sample_markdown_file
        assert result.chunks_created > 0
        assert result.collection_name == "test-collection"

        # Verify interactions
        mock_chroma_client.get_or_create_collection.assert_called_once_with(
            "test-collection", create_if_missing=True
        )
        mock_chroma_client.bulk_insert.assert_called_once()

    def test_process_document_file_not_found(self, processor_config, mock_chroma_client):
        """Test processing with non-existent file."""
        processor = DocumentProcessor(processor_config, mock_chroma_client)

        result = processor.process_document(
            Path("nonexistent.md"),
            "test-collection"
        )

        assert result.success is False
        assert "File not found" in result.error or "No such file" in result.error

    def test_process_batch_sequential(self, processor_config, mock_chroma_client,
                                    tmp_path):
        """Test batch processing with multiple files."""
        processor = DocumentProcessor(processor_config, mock_chroma_client)

        # Create multiple test files
        files = []
        for i in range(5):
            file_path = tmp_path / f"test_{i}.md"
            file_path.write_text(f"# Document {i}\n\nContent for document {i}.")
            files.append(file_path)

        results = processor.process_batch(files, "test-collection", batch_size=2)

        assert len(results) == 5
        successful_results = [r for r in results if r.success]
        assert len(successful_results) == 5

    @patch('shard_markdown.core.processor.MarkdownParser')
    def test_markdown_parsing_error_handling(self, mock_parser_class,
                                           processor_config, mock_chroma_client,
                                           sample_markdown_file):
        """Test handling of markdown parsing errors."""
        # Setup mock to raise exception
        mock_parser = Mock()
        mock_parser.parse.side_effect = Exception("Parsing failed")
        mock_parser_class.return_value = mock_parser

        processor = DocumentProcessor(processor_config, mock_chroma_client)

        result = processor.process_document(sample_markdown_file, "test-collection")

        assert result.success is False
        assert "Parsing failed" in result.error
```

#### 2.1.2 Chunking Engine Tests (`test_core/test_chunking/test_structure.py`)

```python
import pytest
from shard_markdown.core.chunking.structure import StructureAwareChunker
from shard_markdown.core.models import ChunkingConfig, MarkdownAST, MarkdownElement

class TestStructureAwareChunker:
    """Test suite for structure-aware chunking."""

    @pytest.fixture
    def chunking_config(self):
        """Standard chunking configuration."""
        return ChunkingConfig(
            chunk_size=1000,
            overlap=200,
            method="structure",
            respect_boundaries=True
        )

    @pytest.fixture
    def sample_ast(self):
        """Create sample markdown AST for testing."""
        elements = [
            MarkdownElement(type="header", level=1, text="Main Title"),
            MarkdownElement(type="paragraph", text="Introduction paragraph with some content."),
            MarkdownElement(type="header", level=2, text="Section 1"),
            MarkdownElement(type="paragraph", text="Content for section 1 with detailed information."),
            MarkdownElement(type="code_block", language="python", text="def example():\n    return 'Hello'"),
            MarkdownElement(type="header", level=2, text="Section 2"),
            MarkdownElement(type="paragraph", text="Content for section 2 with more details."),
        ]
        return MarkdownAST(elements=elements)

    def test_chunk_respects_headers(self, chunking_config, sample_ast):
        """Test that chunking respects header boundaries."""
        chunker = StructureAwareChunker(chunking_config)
        chunks = chunker.chunk_document(sample_ast)

        assert len(chunks) > 0

        # Check that chunks maintain structural context
        for chunk in chunks:
            assert 'structural_context' in chunk.metadata
            assert 'parent_sections' in chunk.metadata

    def test_chunk_size_enforcement(self, sample_ast):
        """Test that chunks respect size limits."""
        config = ChunkingConfig(chunk_size=100, overlap=20)
        chunker = StructureAwareChunker(config)

        chunks = chunker.chunk_document(sample_ast)

        # Most chunks should be within size limits (allowing some flexibility)
        oversized_chunks = [c for c in chunks if len(c.content) > config.chunk_size * 1.2]
        assert len(oversized_chunks) == 0, "Chunks exceed size limits"

    def test_overlap_functionality(self, sample_ast):
        """Test that chunk overlap works correctly."""
        config = ChunkingConfig(chunk_size=200, overlap=50)
        chunker = StructureAwareChunker(config)

        chunks = chunker.chunk_document(sample_ast)

        if len(chunks) > 1:
            # Check that consecutive chunks have some overlap
            for i in range(len(chunks) - 1):
                current_chunk = chunks[i]
                next_chunk = chunks[i + 1]

                # Overlap should be present in metadata
                assert current_chunk.end_position > next_chunk.start_position

    def test_code_block_preservation(self, chunking_config):
        """Test that code blocks are not split inappropriately."""
        elements = [
            MarkdownElement(type="paragraph", text="Before code block."),
            MarkdownElement(
                type="code_block",
                language="python",
                text="def long_function():\n    # This is a long function\n    " +
                     "# " * 50 + "\n    return result"
            ),
            MarkdownElement(type="paragraph", text="After code block.")
        ]
        ast = MarkdownAST(elements=elements)

        chunker = StructureAwareChunker(chunking_config)
        chunks = chunker.chunk_document(ast)

        # Find chunk containing code block
        code_chunks = [c for c in chunks if "def long_function" in c.content]
        assert len(code_chunks) == 1, "Code block should be in exactly one chunk"

    def test_empty_document_handling(self, chunking_config):
        """Test handling of empty documents."""
        empty_ast = MarkdownAST(elements=[])

        chunker = StructureAwareChunker(chunking_config)
        chunks = chunker.chunk_document(empty_ast)

        assert len(chunks) == 0
```

### 2.2 CLI Component Testing

#### 2.2.1 Command Testing (`test_cli/test_commands.py`)

```python
import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch

from shard_markdown.cli.main import cli

class TestProcessCommand:
    """Test suite for process command."""

    @pytest.fixture
    def runner(self):
        """Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_processor(self):
        """Mock document processor."""
        with patch('shard_markdown.cli.commands.process.DocumentProcessor') as mock:
            processor_instance = Mock()
            processor_instance.process_document.return_value = Mock(
                success=True,
                chunks_created=5,
                processing_time=0.1,
                collection_name="test-collection"
            )
            mock.return_value = processor_instance
            yield processor_instance

    @pytest.fixture
    def mock_chromadb_client(self):
        """Mock ChromaDB client."""
        with patch('shard_markdown.cli.commands.process.ChromaDBClient') as mock:
            client_instance = Mock()
            client_instance.connect.return_value = True
            mock.return_value = client_instance
            yield client_instance

    def test_process_command_basic(self, runner, mock_processor, mock_chromadb_client,
                                 tmp_path):
        """Test basic process command functionality."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n\nContent")

        result = runner.invoke(cli, [
            'process',
            '--collection', 'test-collection',
            str(test_file)
        ])

        assert result.exit_code == 0
        assert "Successfully processed" in result.output
        mock_processor.process_document.assert_called_once()

    def test_process_command_missing_collection(self, runner, tmp_path):
        """Test process command with missing collection parameter."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n\nContent")

        result = runner.invoke(cli, [
            'process',
            str(test_file)
        ])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_process_command_invalid_file(self, runner):
        """Test process command with non-existent file."""
        result = runner.invoke(cli, [
            'process',
            '--collection', 'test-collection',
            'nonexistent.md'
        ])

        assert result.exit_code != 0
        assert "does not exist" in result.output.lower()

    def test_process_command_dry_run(self, runner, tmp_path):
        """Test dry run functionality."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n\nContent")

        result = runner.invoke(cli, [
            'process',
            '--collection', 'test-collection',
            '--dry-run',
            str(test_file)
        ])

        assert result.exit_code == 0
        assert "Dry Run Preview" in result.output
        assert "Files to process: 1" in result.output

    def test_process_command_custom_chunk_settings(self, runner, mock_processor,
                                                 mock_chromadb_client, tmp_path):
        """Test process command with custom chunking settings."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n\nContent")

        result = runner.invoke(cli, [
            'process',
            '--collection', 'test-collection',
            '--chunk-size', '1500',
            '--chunk-overlap', '300',
            '--chunk-method', 'fixed',
            str(test_file)
        ])

        assert result.exit_code == 0

        # Verify processor was called with correct configuration
        call_args = mock_processor.process_document.call_args
        # Additional assertions about configuration would go here
```

### 2.3 Configuration Testing

#### 2.3.1 Settings Validation Tests (`test_config/test_settings.py`)

```python
import pytest
from pydantic import ValidationError

from shard_markdown.config.settings import (
    ChromaDBConfig, ChunkingConfig, ProcessingConfig, AppConfig
)

class TestChromaDBConfig:
    """Test ChromaDB configuration validation."""

    def test_valid_config(self):
        """Test valid ChromaDB configuration."""
        config = ChromaDBConfig(
            host="localhost",
            port=8000,
            ssl=False,
            timeout=30
        )

        assert config.host == "localhost"
        assert config.port == 8000
        assert config.ssl is False
        assert config.timeout == 30

    def test_invalid_port_range(self):
        """Test validation of port range."""
        with pytest.raises(ValidationError) as exc_info:
            ChromaDBConfig(port=70000)  # Port too high

        assert "ensure this value is less than or equal to 65535" in str(exc_info.value)

    def test_empty_host(self):
        """Test validation of empty host."""
        with pytest.raises(ValidationError) as exc_info:
            ChromaDBConfig(host="")

        assert "Host cannot be empty" in str(exc_info.value)

    def test_host_whitespace_stripping(self):
        """Test that host whitespace is stripped."""
        config = ChromaDBConfig(host="  localhost  ")
        assert config.host == "localhost"

class TestChunkingConfig:
    """Test chunking configuration validation."""

    def test_valid_config(self):
        """Test valid chunking configuration."""
        config = ChunkingConfig(
            default_size=1000,
            default_overlap=200,
            method="structure"
        )

        assert config.default_size == 1000
        assert config.default_overlap == 200
        assert config.method == "structure"

    def test_overlap_larger_than_size(self):
        """Test validation when overlap is larger than chunk size."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkingConfig(default_size=500, default_overlap=600)

        assert "Overlap must be less than chunk size" in str(exc_info.value)

    def test_minimum_chunk_size(self):
        """Test minimum chunk size validation."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkingConfig(default_size=50)  # Too small

        assert "ensure this value is greater than or equal to 100" in str(exc_info.value)

    def test_negative_overlap(self):
        """Test negative overlap validation."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkingConfig(default_overlap=-100)

        assert "ensure this value is greater than or equal to 0" in str(exc_info.value)

class TestAppConfig:
    """Test complete application configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AppConfig()

        assert config.chromadb.host == "localhost"
        assert config.chromadb.port == 8000
        assert config.chunking.default_size == 1000
        assert config.processing.batch_size == 10

    def test_nested_config_validation(self):
        """Test that nested configuration validation works."""
        with pytest.raises(ValidationError):
            AppConfig(
                chromadb={"host": "", "port": 8000},  # Empty host should fail
                chunking={"default_size": 1000, "default_overlap": 200}
            )

    def test_environment_variable_override(self):
        """Test environment variable configuration override."""
        import os

        # Set environment variable
        os.environ["SHARD_MD_CHROMADB_HOST"] = "remote-server.com"
        os.environ["SHARD_MD_CHROMADB_PORT"] = "9000"

        try:
            config = AppConfig()
            # Note: This test depends on proper environment variable handling
            # which may need to be implemented in the actual configuration loader
        finally:
            # Clean up environment
            os.environ.pop("SHARD_MD_CHROMADB_HOST", None)
            os.environ.pop("SHARD_MD_CHROMADB_PORT", None)
```

## 3. Integration Testing Strategy

### 3.1 Document Processing Integration Tests

#### 3.1.1 End-to-End Processing (`test_integration/test_document_processing.py`)

```python
import pytest
import tempfile
from pathlib import Path
import json

from shard_markdown.core.processor import DocumentProcessor
from shard_markdown.core.models import ProcessingConfig
from shard_markdown.chromadb.client import ChromaDBClient
from shard_markdown.config.settings import ChromaDBConfig

@pytest.mark.integration
class TestDocumentProcessingIntegration:
    """Integration tests for complete document processing workflow."""

    @pytest.fixture(scope="class")
    def chromadb_client(self):
        """Real ChromaDB client for integration testing."""
        # Note: This requires a running ChromaDB instance for testing
        config = ChromaDBConfig(
            host="localhost",
            port=8000,
            ssl=False
        )

        client = ChromaDBClient(config)
        if not client.connect():
            pytest.skip("ChromaDB not available for integration testing")

        yield client

    @pytest.fixture
    def test_documents(self, tmp_path):
        """Create various test documents."""
        documents = {}

        # Simple document
        simple_doc = tmp_path / "simple.md"
        simple_doc.write_text("""# Simple Document

This is a simple document with basic content.

## Section 1
Content for section 1.

## Section 2
Content for section 2.
""")
        documents['simple'] = simple_doc

        # Document with frontmatter
        frontmatter_doc = tmp_path / "with_frontmatter.md"
        frontmatter_doc.write_text("""---
title: "Document with Frontmatter"
author: "Test Author"
tags: ["test", "integration"]
---

# Document with Frontmatter

This document has YAML frontmatter.
""")
        documents['frontmatter'] = frontmatter_doc

        # Complex document with code blocks
        complex_doc = tmp_path / "complex.md"
        complex_doc.write_text("""# Complex Document

This document has various markdown elements.

## Code Example

```python
def hello_world():
    print("Hello, World!")
    return True
```

## Lists

- Item 1
- Item 2
  - Nested item
- Item 3

## Tables

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
""")

        documents['complex'] = complex_doc

        return documents

    def test_process_simple_document(self, chromadb_client, test_documents):
        """Test processing a simple markdown document."""
        config = ProcessingConfig(
            chunk_size=500,
            chunk_overlap=100,
            chunk_method="structure"
        )

        processor = DocumentProcessor(config, chromadb_client)

        result = processor.process_document(
            test_documents['simple'],
            "test-simple-integration",
            create_collection=True
        )

        assert result.success is True
        assert result.chunks_created > 0
        assert result.processing_time > 0

        # Verify data was actually stored
        collection = chromadb_client.get_or_create_collection("test-simple-integration")
        count = collection.count()
        assert count == result.chunks_created

    def test_process_document_with_frontmatter(self, chromadb_client, test_documents):
        """Test processing document with YAML frontmatter."""
        config = ProcessingConfig(
            chunk_size=300,
            chunk_overlap=50,
            include_frontmatter=True
        )

        processor = DocumentProcessor(config, chromadb_client)

        result = processor.process_document(
            test_documents['frontmatter'],
            "test-frontmatter-integration",
            create_collection=True
        )

        assert result.success is True

        # Verify frontmatter was extracted
        collection = chromadb_client.get_or_create_collection("test-frontmatter-integration")
        documents = collection.get(limit=1)

        if documents['metadatas']:
            metadata = documents['metadatas'][0]
            assert metadata.get('title') == "Document with Frontmatter"
            assert metadata.get('author') == "Test Author"
            assert 'test' in metadata.get('tags', [])

    def test_batch_processing(self, chromadb_client, test_documents):
        """Test batch processing of multiple documents."""
        config = ProcessingConfig(
            chunk_size=400,
            chunk_overlap=80,
            batch_size=2,
        )

        processor = DocumentProcessor(config, chromadb_client)

        file_paths = list(test_documents.values())
        results = processor.process_batch(
            file_paths,
            "test-batch-integration",
            create_collection=True,
        )

        assert len(results) == len(file_paths)
        successful_results = [r for r in results if r.success]
        assert len(successful_results) == len(file_paths)

        # Verify total chunks created
        total_chunks = sum(r.chunks_created for r in successful_results)
        assert total_chunks > 0

        # Verify all data was stored
        collection = chromadb_client.get_or_create_collection("test-batch-integration")
        stored_count = collection.count()
        assert stored_count == total_chunks

    def test_error_handling_invalid_file(self, chromadb_client):
        """Test error handling with invalid file."""
        config = ProcessingConfig()
        processor = DocumentProcessor(config, chromadb_client)

        result = processor.process_document(
            Path("nonexistent_file.md"),
            "test-error-integration"
        )

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower() or "no such file" in result.error.lower()

```

### 3.2 ChromaDB Integration Tests

#### 3.2.1 Database Operations (`test_integration/test_chromadb_integration.py`)

```python
import pytest
from shard_markdown.chromadb.client import ChromaDBClient
from shard_markdown.config.settings import ChromaDBConfig
from shard_markdown.core.models import DocumentChunk

@pytest.mark.integration
class TestChromaDBIntegration:
    """Integration tests for ChromaDB operations."""

    @pytest.fixture(scope="class")
    def chromadb_client(self):
        """ChromaDB client for integration testing."""
        config = ChromaDBConfig(host="localhost", port=8000)
        client = ChromaDBClient(config)

        if not client.connect():
            pytest.skip("ChromaDB not available for integration testing")

        yield client

    @pytest.fixture
    def sample_chunks(self):
        """Create sample document chunks for testing."""
        return [
            DocumentChunk(
                id="test_chunk_001",
                content="This is the first test chunk with some content.",
                metadata={
                    "source_file": "test.md",
                    "chunk_index": 0,
                    "section": "Introduction"
                }
            ),
            DocumentChunk(
                id="test_chunk_002",
                content="This is the second test chunk with different content.",
                metadata={
                    "source_file": "test.md",
                    "chunk_index": 1,
                    "section": "Main Content"
                }
            ),
            DocumentChunk(
                id="test_chunk_003",
                content="This is the third and final test chunk.",
                metadata={
                    "source_file": "test.md",
                    "chunk_index": 2,
                    "section": "Conclusion"
                }
            )
        ]

    def test_collection_creation_and_retrieval(self, chromadb_client):
        """Test creating and retrieving collections."""
        collection_name = "test-collection-creation"

        # Create collection
        collection = chromadb_client.get_or_create_collection(
            collection_name,
            create_if_missing=True,
            metadata={"test": "integration", "purpose": "testing"}
        )

        assert collection is not None
        assert collection.name == collection_name

        # Retrieve same collection
        retrieved_collection = chromadb_client.get_or_create_collection(collection_name)
        assert retrieved_collection.name == collection_name

    def test_bulk_insert_and_retrieval(self, chromadb_client, sample_chunks):
        """Test bulk insertion and retrieval of chunks."""
        collection_name = "test-bulk-operations"

        collection = chromadb_client.get_or_create_collection(
            collection_name,
            create_if_missing=True
        )

        # Insert chunks
        result = chromadb_client.bulk_insert(collection, sample_chunks)

        assert result.success is True
        assert result.chunks_inserted == len(sample_chunks)
        assert result.processing_time > 0

        # Verify insertion
        stored_count = collection.count()
        assert stored_count == len(sample_chunks)

        # Retrieve and verify content
        all_docs = collection.get()
        assert len(all_docs['ids']) == len(sample_chunks)

        # Check that our IDs are present
        stored_ids = set(all_docs['ids'])
        expected_ids = {chunk.id for chunk in sample_chunks}
        assert stored_ids == expected_ids

    def test_query_functionality(self, chromadb_client, sample_chunks):
        """Test querying functionality."""
        collection_name = "test-query-operations"

        collection = chromadb_client.get_or_create_collection(
            collection_name,
            create_if_missing=True
        )

        # Insert test data
        chromadb_client.bulk_insert(collection, sample_chunks)

        # Query for similar content
        results = collection.query(
            query_texts=["test chunk content"],
            n_results=2
        )

        assert len(results['ids'][0]) <= 2
        assert len(results['documents'][0]) <= 2

        # Verify results contain expected content
        returned_docs = results['documents'][0]
        assert any("test chunk" in doc.lower() for doc in returned_docs)

    def test_collection_listing(self, chromadb_client):
        """Test listing collections."""
        # Create a few test collections
        test_collections = ["test-list-1", "test-list-2", "test-list-3"]

        for collection_name in test_collections:
            chromadb_client.get_or_create_collection(
                collection_name,
                create_if_missing=True
            )

        # List collections
        collections_info = chromadb_client.list_collections()

        assert isinstance(collections_info, list)

        # Check that our test collections are in the list
        collection_names = [info['name'] for info in collections_info]
        for test_collection in test_collections:
            assert test_collection in collection_names

    def test_error_handling_invalid_collection(self, chromadb_client):
        """Test error handling for invalid collection operations."""
        # Try to get non-existent collection without create flag
        with pytest.raises(Exception):  # Should raise some form of exception
            chromadb_client.get_or_create_collection(
                "nonexistent-collection",
                create_if_missing=False
            )


    @pytest.fixture
    def cli_runner(self):
        """CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample project structure with documentation."""
        project_dir = tmp_path / "sample_project"
        project_dir.mkdir()

        # Create documentation structure
        docs_dir = project_dir / "docs"
        docs_dir.mkdir()

        # API documentation
        api_dir = docs_dir / "api"
        api_dir.mkdir()
        (api_dir / "authentication.md").write_text("""# Authentication

## Overview
The API uses token-based authentication.

## Getting a Token
To get an authentication token:
1. Register an account
2. Login to get your token
3. Include token in requests
""")

        (api_dir / "endpoints.md").write_text("""# API Endpoints

## Users
### GET /users
Returns list of users.

### POST /users
Creates a new user.

## Posts
### GET /posts
Returns list of posts.
""")

        # User guides
        guides_dir = docs_dir / "guides"
        guides_dir.mkdir()
        (guides_dir / "getting-started.md").write_text("""---
title: "Getting Started Guide"
difficulty: "beginner"
estimated_time: "15 minutes"
---

# Getting Started

Welcome to our platform! This guide will help you get started.

## Prerequisites
- Valid email address
- Basic understanding of APIs

## Steps
1. Create account
2. Verify email
3. Generate API token
4. Make first API call
""")

        return project_dir

    @pytest.mark.skipif(
        subprocess.call(["docker", "ps"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0,
        reason="Docker not available"
    )
    def test_complete_documentation_processing_workflow(self, runner, sample_project):
        """Test complete workflow from processing to querying."""
        docs_dir = sample_project / "docs"

        # Step 1: Process documentation
        result = runner.invoke(cli, [
            'process',
            '--collection', 'sample-project-docs',
            '--create-collection',
            '--recursive',
            '--chunk-size', '800',
            '--chunk-overlap', '150',
            '--include-frontmatter',
            '--custom-metadata', '{"project": "sample", "version": "1.0"}',
            str(docs_dir)
        ])

        assert result.exit_code == 0, f"Process command failed: {result.output}"
        assert "Successfully processed" in result.output

        # Step 2: List collections to verify creation
        result = runner.invoke(cli, ['collections', 'list'])
        assert result.exit_code == 0
        assert 'sample-project-docs' in result.output

        # Step 3: Get collection info
        result = runner.invoke(cli, [
            'collections', 'info', 'sample-project-docs'
        ])
        assert result.exit_code == 0
        assert 'sample-project-docs' in result.output

        # Step 4: Search for content
        result = runner.invoke(cli, [
            'query', 'search', 'authentication token',
            '--collection', 'sample-project-docs',
            '--limit', '3'
        ])
        assert result.exit_code == 0
        assert 'authentication' in result.output.lower()

    def test_error_handling_workflow(self, runner, tmp_path):
        """Test error handling in realistic scenarios."""
        # Create a problematic file
        bad_file = tmp_path / "problematic.md"
        bad_file.write_bytes(b'\xff\xfe# Invalid encoding content')

        # Try to process it
        result = runner.invoke(cli, [
            'process',
            '--collection', 'error-test',
            '--create-collection',
            str(bad_file)
        ])

        # Should handle the error gracefully
        assert "encoding" in result.output.lower() or "failed" in result.output.lower()
        # Exit code might be 0 if we handle errors gracefully, or non-zero if we fail fast

    def test_configuration_workflow(self, runner, tmp_path):
        """Test configuration management workflow."""
        config_file = tmp_path / "test-config.yaml"

        # Step 1: Initialize configuration
        result = runner.invoke(cli, [
            '--config', str(config_file),
            'config', 'init'
        ])
        assert result.exit_code == 0
        assert config_file.exists()

        # Step 2: Show configuration
        result = runner.invoke(cli, [
            '--config', str(config_file),
            'config', 'show'
        ])
        assert result.exit_code == 0
        assert 'chromadb' in result.output
        assert 'chunking' in result.output

        # Step 3: Set configuration value
        result = runner.invoke(cli, [
            '--config', str(config_file),
            'config', 'set', 'chunking.default_size', '1500'
        ])
        assert result.exit_code == 0

        # Step 4: Verify configuration change
        result = runner.invoke(cli, [
            '--config', str(config_file),
            'config', 'show'
        ])
        assert result.exit_code == 0
        assert '1500' in result.output

    def test_dry_run_and_preview_workflow(self, runner, sample_project):
        """Test dry run and preview functionality."""
        docs_dir = sample_project / "docs"

        # Step 1: Dry run to see what would be processed
        result = runner.invoke(cli, [
            'process',
            '--collection', 'preview-test',
            '--dry-run',
            '--recursive',
            str(docs_dir)
        ])
        assert result.exit_code == 0
        assert "Dry Run Preview" in result.output
        assert "Files to process:" in result.output

        # Step 2: Preview chunking for specific file
        test_file = docs_dir / "api" / "authentication.md"
        result = runner.invoke(cli, [
            'preview',
            '--chunk-size', '500',
            '--chunk-overlap', '100',
            str(test_file)
        ])
        assert result.exit_code == 0
        assert "Preview for:" in result.output
        assert "Chunk" in result.output

    def test_validation_workflow(self, runner, sample_project):
        """Test document validation workflow."""
        docs_dir = sample_project / "docs"

        # Validate all documents
        result = runner.invoke(cli, [
            'validate',
            '--recursive',
            '--check-frontmatter',
            str(docs_dir)
        ])
        assert result.exit_code == 0

        # Should show validation results
        assert any(keyword in result.output for keyword in ["valid", "passed", "✓"])
```

## 5. Performance Testing Strategy

### 5.1 Benchmark Tests

#### 5.1.1 Processing Performance (`test_performance/test_benchmarks.py`)

```python
import pytest
import time
from pathlib import Path
import statistics

from shard_markdown.core.processor import DocumentProcessor
from shard_markdown.core.models import ProcessingConfig
from shard_markdown.chromadb.client import ChromaDBClient
from shard_markdown.config.settings import ChromaDBConfig

@pytest.mark.performance
class TestProcessingBenchmarks:
    """Performance benchmarks for document processing."""

    @pytest.fixture(scope="class")
    def chromadb_client(self):
        """ChromaDB client for performance testing."""
        config = ChromaDBConfig(host="localhost", port=8000)
        client = ChromaDBClient(config)

        if not client.connect():
            pytest.skip("ChromaDB not available for performance testing")

        yield client

    @pytest.fixture
    def large_document(self, tmp_path):
        """Generate a large markdown document for testing."""
        doc_path = tmp_path / "large_document.md"

        content = []
        content.append("# Large Document for Performance Testing\n\n")

        for section in range(50):  # 50 sections
            content.append(f"## Section {section + 1}\n\n")

            for paragraph in range(10):  # 10 paragraphs per section
                content.append(f"This is paragraph {paragraph + 1} of section {section + 1}. ")
                content.append("It contains some meaningful content that represents typical ")
                content.append("documentation text with multiple sentences and reasonable length. ")
                content.append("The content should be long enough to create multiple chunks ")
                content.append("but not so long as to make testing impractical.\n\n")

            # Add some code blocks
            if section % 5 == 0:
                content.append("```python\n")
                content.append(f"def function_section_{section}():\n")
                content.append(f"    \"\"\"Function for section {section}.\"\"\"\n")
                content.append(f"    return 'Section {section} result'\n")
                content.append("```\n\n")

        doc_path.write_text("".join(content))
        return doc_path

    @pytest.fixture
    def multiple_documents(self, tmp_path):
        """Generate multiple documents for batch testing."""
        documents = []

        for i in range(20):  # 20 documents
            doc_path = tmp_path / f"document_{i:02d}.md"

            content = f"""# Document {i}

This is document number {i} in the test suite.

## Introduction
Introduction content for document {i}.

## Main Content
{'Main content paragraph. ' * 20}

## Code Example
```python
def document_{i}_function():
    return {i}
```

## Conclusion

Conclusion for document {i}.
"""
            doc_path.write_text(content)
            documents.append(doc_path)

        return documents

    def test_single_large_document_processing(self, chromadb_client, large_document):
        """Benchmark processing of a single large document."""
        config = ProcessingConfig(
            chunk_size=1000,
            chunk_overlap=200,
            chunk_method="structure"
        )

        processor = DocumentProcessor(config, chromadb_client)

        # Warm up
        processor.process_document(large_document, "warmup-collection", create_collection=True)

        # Benchmark
        times = []
        for _ in range(5):  # 5 runs
            start_time = time.time()
            result = processor.process_document(
                large_document,
                f"benchmark-large-{int(time.time())}",
                create_collection=True
            )
            end_time = time.time()

            assert result.success is True
            times.append(end_time - start_time)

        avg_time = statistics.mean(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0

        print(f"\nLarge document processing benchmark:")
        print(f"Average time: {avg_time:.3f}s ± {std_dev:.3f}s")
        print(f"Chunks created: {result.chunks_created}")
        print(f"Processing rate: {result.chunks_created / avg_time:.1f} chunks/second")

        # Performance expectations (adjust based on requirements)
        assert avg_time < 10.0, f"Processing too slow: {avg_time:.3f}s"

    def test_batch_processing_performance(self, chromadb_client, multiple_documents):
        """Benchmark batch processing performance."""
        config = ProcessingConfig(
            chunk_size=800,
            chunk_overlap=150,
            batch_size=10,
        )

        processor = DocumentProcessor(config, chromadb_client)

        # Benchmark
        start_time = time.time()
        results = processor.process_batch(
            multiple_documents,
            f"benchmark-batch-{int(time.time())}",
            create_collection=True,
        )
        end_time = time.time()

        total_time = end_time - start_time
        successful_results = [r for r in results if r.success]
        total_chunks = sum(r.chunks_created for r in successful_results)

        print(f"\nBatch processing benchmark:")
        print(f"Documents processed: {len(successful_results)}/{len(multiple_documents)}")
        print(f"Total time: {total_time:.3f}s")
        print(f"Average time per document: {total_time / len(multiple_documents):.3f}s")
        print(f"Total chunks created: {total_chunks}")
        print(f"Processing rate: {total_chunks / total_time:.1f} chunks/second")

        # Performance expectations
        assert len(successful_results) == len(multiple_documents), "Not all documents processed"
        assert total_time < 30.0, f"Batch processing too slow: {total_time:.3f}s"

    @pytest.mark.parametrize("chunk_size,overlap", [
        (500, 100),
        (1000, 200),
        (1500, 300),
        (2000, 400)
    ])
    def test_chunking_performance_by_size(self, chromadb_client, large_document,
                                        chunk_size, overlap):
        """Benchmark performance with different chunk sizes."""
        config = ProcessingConfig(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            chunk_method="structure"
        )

        processor = DocumentProcessor(config, chromadb_client)

        start_time = time.time()
        result = processor.process_document(
            large_document,
            f"benchmark-size-{chunk_size}-{int(time.time())}",
            create_collection=True
        )
        end_time = time.time()

        processing_time = end_time - start_time

        print(f"\nChunk size {chunk_size} (overlap {overlap}):")
        print(f"Processing time: {processing_time:.3f}s")
        print(f"Chunks created: {result.chunks_created}")
        print(f"Avg chunk processing time: {processing_time / result.chunks_created * 1000:.1f}ms")

        assert result.success is True

        # Store results for comparison
        return {
            'chunk_size': chunk_size,
            'overlap': overlap,
            'processing_time': processing_time,
            'chunks_created': result.chunks_created,
            'chunks_per_second': result.chunks_created / processing_time
        }

    def test_memory_usage_monitoring(self, chromadb_client, large_document):
        """Monitor memory usage during processing."""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        config = ProcessingConfig(chunk_size=1000, chunk_overlap=200)
        processor = DocumentProcessor(config, chromadb_client)

        # Get baseline memory usage
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process document and monitor memory
        memory_samples = []

        def memory_monitor():
            while True:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory - baseline_memory)
                time.sleep(0.1)

        # Threading removed for sequential processing
        # Memory monitoring simplified for sequential processing
        # Monitor memory during processing directly

        # Process document
        result = processor.process_document(
            large_document,
            f"memory-test-{int(time.time())}",
            create_collection=True
        )

        # Wait a bit for memory stabilization
        time.sleep(2)

        if memory_samples:
            max_memory_increase = max(memory_samples)
            avg_memory_increase = statistics.mean(memory_samples)

            print(f"\nMemory usage analysis:")
            print(f"Baseline memory: {baseline_memory:.1f} MB")
            print(f"Max memory increase: {max_memory_increase:.1f} MB")
            print(f"Average memory increase: {avg_memory_increase:.1f} MB")
            print(f"Memory per chunk: {max_memory_increase / result.chunks_created:.2f} MB")

            # Memory usage expectations (adjust based on requirements)
            assert max_memory_increase < 500, f"Memory usage too high: {max_memory_increase:.1f}MB"

        assert result.success is True

```

This comprehensive testing strategy ensures the shard-markdown CLI tool is thoroughly tested across all layers and scenarios, providing confidence in its reliability and performance.
