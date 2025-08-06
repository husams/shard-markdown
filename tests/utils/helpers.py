"""Reusable test utilities and helper functions.

This module provides common test utilities to reduce code duplication across test files.
Includes helpers for file creation, mock setup, assertions, and test data generation.
"""

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from shard_markdown.config.settings import ChromaDBConfig, ProcessingConfig
from shard_markdown.core.models import (
    ChunkingConfig,
    DocumentChunk,
    MarkdownAST,
    MarkdownElement,
    ProcessingResult,
)


class FileHelper:
    """Helper class for creating test files and directories."""

    @staticmethod
    def create_markdown_file(
        directory: Path,
        filename: str,
        content: str,
        encoding: str = "utf-8",
    ) -> Path:
        """Create a markdown file with specified content.

        Args:
            directory: Directory to create the file in
            filename: Name of the file to create
            content: Content to write to the file
            encoding: Text encoding to use

        Returns:
            Path to the created file
        """
        file_path = directory / filename
        file_path.write_text(content, encoding=encoding)
        return file_path

    @staticmethod
    def create_large_markdown_file(
        directory: Path,
        filename: str,
        num_sections: int = 50,
        content_multiplier: int = 10,
    ) -> Path:
        """Create a large markdown file for performance testing.

        Args:
            directory: Directory to create the file in
            filename: Name of the file to create
            num_sections: Number of sections to create
            content_multiplier: Multiplier for content length

        Returns:
            Path to the created file
        """
        sections = [f"# Large Document Test - {filename}\n\n"]
        sections.append("This is a large document created for testing purposes.\n\n")

        for i in range(num_sections):
            sections.append(f"## Section {i + 1}\n\n")
            content_line = f"This is the content for section {i + 1}. "
            sections.append(content_line * content_multiplier + "\n\n")

            if i % 5 == 0:
                sections.append("```python\n")
                sections.append(f"# Code example for section {i + 1}\n")
                sections.append(f"def function_{i + 1}():\n")
                sections.append(f'    return "Section {i + 1} result"\n')
                sections.append("```\n\n")

        content = "".join(sections)
        return FileHelper.create_markdown_file(directory, filename, content)

    @staticmethod
    def create_unicode_markdown_file(directory: Path, filename: str) -> Path:
        """Create a markdown file with Unicode content.

        Args:
            directory: Directory to create the file in
            filename: Name of the file to create

        Returns:
            Path to the created file
        """
        unicode_content = """# 文档标题 (Document Title)

这是一个包含中文内容的文档。This document contains Chinese content.

## Émojis and Special Characters

Here are some emojis: 🚀 📚 💡 🔥

Mathematical symbols: α β γ δ ε ∑ ∫ ∆ ∇

## Código en Español

```python
def función_ejemplo():
    return "¡Hola, mundo!"
```

## العربية (Arabic)

هذا نص باللغة العربية مع بعض الكلمات الإنجليزية mixed in.

## Русский (Russian)

Это текст на русском языке с some English words.
"""
        return FileHelper.create_markdown_file(directory, filename, unicode_content)

    @staticmethod
    def create_frontmatter_file(directory: Path, filename: str) -> Path:
        """Create a markdown file with YAML frontmatter.

        Args:
            directory: Directory to create the file in
            filename: Name of the file to create

        Returns:
            Path to the created file
        """
        frontmatter_content = """---
title: "Test Document"
author: "Test Author"
tags:
  - test
  - markdown
date: "2024-01-01"
description: "Document with frontmatter for testing"
---

# Test Document with Frontmatter

This document has YAML frontmatter for testing purposes.

## Content Section

Regular markdown content follows the frontmatter.

### Code Example

```python
def test_function():
    return "Testing frontmatter parsing"
```
"""
        return FileHelper.create_markdown_file(directory, filename, frontmatter_content)

    @staticmethod
    def create_empty_file(directory: Path, filename: str) -> Path:
        """Create an empty file for testing.

        Args:
            directory: Directory to create the file in
            filename: Name of the file to create

        Returns:
            Path to the created file
        """
        file_path = directory / filename
        file_path.touch()
        return file_path

    @staticmethod
    def create_whitespace_file(directory: Path, filename: str) -> Path:
        """Create a file containing only whitespace.

        Args:
            directory: Directory to create the file in
            filename: Name of the file to create

        Returns:
            Path to the created file
        """
        whitespace_content = "   \n\n\t\t\n   \n"
        return FileHelper.create_markdown_file(directory, filename, whitespace_content)

    @staticmethod
    def create_binary_file(directory: Path, filename: str) -> Path:
        """Create a binary file for testing error handling.

        Args:
            directory: Directory to create the file in
            filename: Name of the file to create

        Returns:
            Path to the created file
        """
        file_path = directory / filename
        with open(file_path, "wb") as f:
            f.write(b"\xff\xfe\xfd\x00\x01\x02\x03")
        return file_path

    @staticmethod
    def create_file_at_size(
        directory: Path, filename: str, target_size: int, encoding: str = "utf-8"
    ) -> Path:
        """Create a file with specific size in bytes.

        Args:
            directory: Directory to create the file in
            filename: Name of the file to create
            target_size: Target file size in bytes
            encoding: Text encoding to use

        Returns:
            Path to the created file
        """
        base_content = f"# {filename}\n\nContent sized to {target_size} bytes."
        current_size = len(base_content.encode(encoding))

        if current_size < target_size:
            padding_needed = target_size - current_size
            padding = " " * (padding_needed - 1) + "\n"
            content = base_content + padding
        else:
            content = base_content[:target_size]

        return FileHelper.create_markdown_file(directory, filename, content, encoding)


class MockHelper:
    """Helper class for creating mock objects and configurations."""

    @staticmethod
    def create_mock_chromadb_config(
        host: str = "localhost",
        port: int = 8000,
        ssl: bool = False,
        timeout: float = 5.0,
        auth_token: str | None = None,
    ) -> ChromaDBConfig:
        """Create a mock ChromaDB configuration.

        Args:
            host: Database host
            port: Database port
            ssl: Whether to use SSL
            timeout: Connection timeout
            auth_token: Authentication token

        Returns:
            ChromaDB configuration object
        """
        return ChromaDBConfig(
            host=host,
            port=port,
            ssl=ssl,
            timeout=timeout,
            auth_token=auth_token,
        )

    @staticmethod
    def create_mock_chunking_config(
        chunk_size: int = 300,
        overlap: int = 50,
        method: str = "structure",
        respect_boundaries: bool = True,
        max_tokens: int | None = None,
    ) -> ChunkingConfig:
        """Create a mock chunking configuration.

        Args:
            chunk_size: Size of each chunk
            overlap: Overlap between chunks
            method: Chunking method
            respect_boundaries: Whether to respect boundaries
            max_tokens: Maximum tokens per chunk

        Returns:
            Chunking configuration object
        """
        return ChunkingConfig(
            chunk_size=chunk_size,
            overlap=overlap,
            method=method,
            respect_boundaries=respect_boundaries,
            max_tokens=max_tokens,
        )

    @staticmethod
    def create_mock_processing_config(
        batch_size: int = 1,
        max_workers: int = 1,
        max_file_size: int = 1_000_000,
        recursive: bool = False,
        pattern: str = "*.md",
        include_frontmatter: bool = True,
        include_path_metadata: bool = True,
        skip_empty_files: bool = True,
        strict_validation: bool = False,
        encoding: str = "utf-8",
        encoding_fallback: str = "latin-1",
        enable_encoding_detection: bool = True,
    ) -> ProcessingConfig:
        """Create a mock processing configuration optimized for testing.

        Args:
            batch_size: Batch size for processing
            max_workers: Maximum number of workers
            max_file_size: Maximum file size in bytes
            recursive: Whether to process directories recursively
            pattern: File pattern to match
            include_frontmatter: Whether to include frontmatter
            include_path_metadata: Whether to include path metadata
            skip_empty_files: Whether to skip empty files
            strict_validation: Whether to use strict validation
            encoding: Primary encoding
            encoding_fallback: Fallback encoding
            enable_encoding_detection: Whether to detect encoding

        Returns:
            Processing configuration object
        """
        return ProcessingConfig(
            batch_size=batch_size,
            max_workers=max_workers,
            max_file_size=max_file_size,
            recursive=recursive,
            pattern=pattern,
            include_frontmatter=include_frontmatter,
            include_path_metadata=include_path_metadata,
            skip_empty_files=skip_empty_files,
            strict_validation=strict_validation,
            encoding=encoding,
            encoding_fallback=encoding_fallback,
            enable_encoding_detection=enable_encoding_detection,
        )

    @staticmethod
    def create_mock_processing_result(
        file_path: str | Path = "test.md",
        success: bool = True,
        chunks_created: int = 5,
        processing_time: float = 1.5,
        collection_name: str = "test-collection",
        error: str | None = None,
    ) -> ProcessingResult:
        """Create a mock processing result.

        Args:
            file_path: Path of the processed file
            success: Whether processing was successful
            chunks_created: Number of chunks created
            processing_time: Time taken for processing
            collection_name: Name of the collection
            error: Error message if any

        Returns:
            Processing result object
        """
        return ProcessingResult(
            file_path=Path(file_path),
            success=success,
            chunks_created=chunks_created,
            processing_time=processing_time,
            collection_name=collection_name,
            error=error,
        )

    @staticmethod
    def create_mock_document_chunk(
        chunk_id: str = "chunk_1",
        content: str = "Sample chunk content",
        metadata: dict[str, Any] | None = None,
        start_position: int = 0,
        end_position: int = 20,
    ) -> DocumentChunk:
        """Create a mock document chunk.

        Args:
            chunk_id: Unique identifier for the chunk
            content: Content of the chunk
            metadata: Additional metadata
            start_position: Start position in document
            end_position: End position in document

        Returns:
            Document chunk object
        """
        if metadata is None:
            metadata = {"chunk_index": 0, "section": "test"}

        return DocumentChunk(
            id=chunk_id,
            content=content,
            metadata=metadata,
            start_position=start_position,
            end_position=end_position,
        )

    @staticmethod
    def create_mock_markdown_ast(
        elements: list[MarkdownElement] | None = None,
        frontmatter: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MarkdownAST:
        """Create a mock markdown AST.

        Args:
            elements: List of markdown elements
            frontmatter: YAML frontmatter data
            metadata: Additional metadata

        Returns:
            Markdown AST object
        """
        if elements is None:
            elements = [
                MarkdownElement(type="header", text="Test Document", level=1),
                MarkdownElement(type="paragraph", text="This is a test paragraph."),
            ]

        if frontmatter is None:
            frontmatter = {"title": "Test Document", "author": "Test Author"}

        if metadata is None:
            metadata = {"word_count": 50, "reading_time": 1}

        return MarkdownAST(
            elements=elements,
            frontmatter=frontmatter,
            metadata=metadata,
        )

    @staticmethod
    def create_mock_collection_manager() -> Mock:
        """Create a mock collection manager with common methods.

        Returns:
            Mock collection manager object
        """
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

    @staticmethod
    def create_mock_chromadb_client() -> Mock:
        """Create a mock ChromaDB client with common methods.

        Returns:
            Mock ChromaDB client object
        """
        client = Mock()
        client.get_collection.return_value = Mock()
        client.create_collection.return_value = Mock()
        client.list_collections.return_value = []
        client.delete_collection.return_value = True
        return client


class AssertionHelper:
    """Helper class for common test assertions."""

    @staticmethod
    def assert_processing_result_success(
        result: ProcessingResult,
        expected_chunks: int | None = None,
        min_processing_time: float = 0.0,
    ) -> None:
        """Assert that a processing result indicates success.

        Args:
            result: Processing result to check
            expected_chunks: Expected number of chunks (optional)
            min_processing_time: Minimum expected processing time
        """
        assert result.success is True, f"Processing failed: {result.error}"
        assert result.error is None, f"Unexpected error: {result.error}"
        assert result.processing_time >= min_processing_time

        if expected_chunks is not None:
            assert result.chunks_created == expected_chunks
        else:
            assert result.chunks_created >= 0

    @staticmethod
    def assert_processing_result_failure(
        result: ProcessingResult,
        expected_error_keywords: list[str] | None = None,
    ) -> None:
        """Assert that a processing result indicates failure.

        Args:
            result: Processing result to check
            expected_error_keywords: Keywords expected in error message
        """
        assert result.success is False, "Processing should have failed"
        assert result.error is not None, "Error message should be present"
        assert result.chunks_created == 0, "No chunks should be created on failure"

        if expected_error_keywords:
            error_lower = result.error.lower()
            for keyword in expected_error_keywords:
                assert keyword.lower() in error_lower, (
                    f"Error message should contain '{keyword}': {result.error}"
                )

    @staticmethod
    def assert_file_size_within_range(
        file_path: Path,
        min_size: int,
        max_size: int,
    ) -> None:
        """Assert that a file size is within the specified range.

        Args:
            file_path: Path to the file to check
            min_size: Minimum expected size in bytes
            max_size: Maximum expected size in bytes
        """
        file_size = file_path.stat().st_size
        assert min_size <= file_size <= max_size, (
            f"File size {file_size} not in range [{min_size}, {max_size}]"
        )

    @staticmethod
    def assert_chunks_valid(chunks: list[DocumentChunk]) -> None:
        """Assert that a list of chunks is valid.

        Args:
            chunks: List of chunks to validate
        """
        assert len(chunks) > 0, "Should have at least one chunk"

        chunk_ids = [chunk.id for chunk in chunks]
        assert len(set(chunk_ids)) == len(chunk_ids), "All chunk IDs should be unique"

        for i, chunk in enumerate(chunks):
            assert chunk.content.strip(), f"Chunk {i} should not be empty"
            assert chunk.id, f"Chunk {i} should have an ID"
            assert isinstance(chunk.metadata, dict), (
                f"Chunk {i} should have metadata dict"
            )


class DataGenerator:
    """Helper class for generating test data."""

    @staticmethod
    def generate_markdown_content_templates() -> dict[str, str]:
        """Generate various markdown content templates for testing.

        Returns:
            Dictionary of content templates by type
        """
        return {
            "simple": """# Simple Document

This is a simple markdown document for testing.

## Section 1

Some basic content here.
""",
            "complex": """# Complex Document

This document demonstrates various markdown features.

## Lists

### Unordered
- Item 1
- Item 2
  - Nested item

### Ordered
1. First item
2. Second item

## Code Blocks

```python
def hello_world():
    return "Hello, World!"
```

## Tables

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |

## Links and Images

[Example link](https://example.com)

![Test image](https://example.com/image.jpg)
""",
            "technical": """# Technical Documentation

## Installation

```bash
pip install shard-markdown
```

## Configuration

```yaml
processing:
  batch_size: 10
  max_workers: 4
```

## API Reference

### Functions

- `process_document()` - Process a single document
- `process_batch()` - Process multiple documents
""",
            "blog": """# Blog Post Title

*Published on January 1, 2024*

## Introduction

Welcome to this blog post about testing markdown processing.

## Main Content

Here's the main content with **bold** and *italic* formatting.

### Subsection

More detailed information here.

## Conclusion

Thanks for reading this test blog post!
""",
        }

    @staticmethod
    def generate_test_chunks(count: int = 5) -> list[DocumentChunk]:
        """Generate a list of test document chunks.

        Args:
            count: Number of chunks to generate

        Returns:
            List of document chunks
        """
        chunks = []
        for i in range(count):
            chunks.append(
                MockHelper.create_mock_document_chunk(
                    chunk_id=f"test_chunk_{i}",
                    content=f"This is test chunk {i} content.",
                    metadata={"chunk_index": i, "section": f"Section {i // 2 + 1}"},
                    start_position=i * 50,
                    end_position=(i + 1) * 50 - 1,
                )
            )
        return chunks

    @staticmethod
    def generate_performance_test_files(
        directory: Path, count: int = 10, size_per_file: int = 5000
    ) -> list[Path]:
        """Generate multiple files for performance testing.

        Args:
            directory: Directory to create files in
            count: Number of files to create
            size_per_file: Approximate size of each file

        Returns:
            List of created file paths
        """
        files = []
        for i in range(count):
            filename = f"perf_test_{i:03d}.md"
            # Create content that approximates the target size
            sections_needed = max(1, size_per_file // 200)  # ~200 chars per section
            file_path = FileHelper.create_large_markdown_file(
                directory, filename, sections_needed, 5
            )
            files.append(file_path)
        return files


class TimingHelper:
    """Helper class for timing and performance testing."""

    @staticmethod
    def time_function(
        func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> tuple[Any, float]:
        """Time the execution of a function.

        Args:
            func: Function to time
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function

        Returns:
            Tuple of (result, execution_time_seconds)
        """
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        return result, execution_time

    @staticmethod
    def assert_execution_time(
        func: Callable[..., Any],
        max_time: float,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Assert that a function executes within a specified time.

        Args:
            func: Function to time
            max_time: Maximum allowed execution time in seconds
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function

        Returns:
            Function result

        Raises:
            AssertionError: If execution time exceeds max_time
        """
        result, execution_time = TimingHelper.time_function(func, *args, **kwargs)
        assert execution_time <= max_time, (
            f"Function took {execution_time:.3f}s, expected <= {max_time:.3f}s"
        )
        return result


class CleanupHelper:
    """Helper class for test cleanup operations."""

    @staticmethod
    def cleanup_temp_files(paths: list[Path]) -> None:
        """Clean up temporary files and directories.

        Args:
            paths: List of paths to clean up
        """
        for path in paths:
            try:
                if path.exists():
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        path.rmdir()
            except OSError:
                # Ignore cleanup errors in tests
                pass

    @staticmethod
    def restore_file_permissions(file_path: Path, mode: int = 0o644) -> None:
        """Restore file permissions after testing.

        Args:
            file_path: Path to file
            mode: File mode to set
        """
        try:
            file_path.chmod(mode)
        except OSError:
            # Ignore permission errors (e.g., on Windows)
            pass
