"""Integration tests for document processing."""

import time
from pathlib import Path
from typing import Any

import pytest

from shard_markdown.core.models import ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor


class TestDocumentProcessingIntegration:
    """Integration tests for document processing workflows."""

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create processor for integration testing."""
        return DocumentProcessor(chunking_config)

    def test_end_to_end_processing(
        self,
        processor: DocumentProcessor,
        sample_markdown_file: Path,
    ) -> None:
        """Test complete end-to-end document processing."""
        # This test requires real components working together
        result = processor.process_document(sample_markdown_file, "integration-test")

        # Verify processing completed successfully
        assert result.success is True
        assert result.chunks_created > 0
        assert result.processing_time > 0
        assert result.collection_name == "integration-test"

    def test_batch_processing_integration(
        self,
        processor: DocumentProcessor,
        test_documents: dict[str, Any],
    ) -> None:
        """Test batch processing with real documents."""
        file_paths = list(test_documents.values())

        result = processor.process_batch(
            file_paths, "batch-integration-test", max_workers=2
        )

        # Verify batch processing results
        assert result.total_files == len(file_paths)
        assert result.successful_files > 0
        assert result.total_chunks > 0
        assert result.collection_name == "batch-integration-test"
        assert result.processing_speed > 0

    def test_complex_markdown_structure(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing of complex markdown documents."""
        # Create a complex markdown document
        complex_content = """
# Main Title

This is the introduction paragraph with some **bold** and *italic* text.

## Section 1

### Subsection 1.1

Here's some content with a [link](https://example.com) and inline `code`.

```python
def example_function():
    return "This is a code block"
```

#### Sub-subsection 1.1.1

- List item 1
- List item 2
  - Nested item
  - Another nested item
- List item 3

1. Numbered list
2. Second item
3. Third item

## Section 2

> This is a blockquote
> that spans multiple lines

### Tables

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |

### More Code

```javascript
const example = {
    property: "value",
    method: function() {
        return this.property;
    }
};
```

## Conclusion

Final thoughts and summary.
"""

        complex_file = temp_dir / "complex.md"
        complex_file.write_text(complex_content)

        result = processor.process_document(complex_file, "complex-test")

        assert result.success is True
        assert result.chunks_created >= 3  # Should create multiple chunks
        assert "complex.md" in str(result.file_path)

    def test_unicode_content_processing(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing documents with Unicode content."""
        unicode_content = """
# 文档标题 (Document Title)

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

        unicode_file = temp_dir / "unicode.md"
        unicode_file.write_text(unicode_content, encoding="utf-8")

        result = processor.process_document(unicode_file, "unicode-test")

        assert result.success is True
        assert result.chunks_created > 0

    def test_large_document_processing(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing of large documents."""
        # Create a large document
        large_content = []
        large_content.append("# Large Document\n\n")

        for i in range(100):  # Create 100 sections
            large_content.append(f"## Section {i + 1}\n\n")
            large_content.append(
                f"This is the content for section {i + 1}. "
                f"It contains multiple sentences to make it substantial. "
                f"Each section has enough content to potentially create "
                f"multiple chunks depending on the chunking strategy. "
                f"Section {i + 1} is part of a larger document structure.\n\n"
            )

            if i % 10 == 0:  # Add code blocks every 10 sections
                large_content.append(
                    f"```python\n"
                    f"def section_{i + 1}_function():\n"
                    f'    return "Content for section {i + 1}"\n'
                    f"```\n\n"
                )

        large_file = temp_dir / "large.md"
        large_file.write_text("".join(large_content))

        result = processor.process_document(large_file, "large-test")

        assert result.success is True
        assert result.chunks_created >= 10  # Should create many chunks
        assert result.processing_time > 0

    def test_empty_sections_handling(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of documents with empty sections."""
        content_with_empty = """
# Document with Empty Sections

## Section 1

This section has content.

## Empty Section 2

## Section 3

This section also has content.

## Another Empty Section

## Section 5

Final section with content.
"""

        empty_sections_file = temp_dir / "empty_sections.md"
        empty_sections_file.write_text(content_with_empty)

        result = processor.process_document(empty_sections_file, "empty-sections-test")

        assert result.success is True
        assert result.chunks_created > 0

    def test_frontmatter_processing(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing documents with YAML frontmatter."""
        frontmatter_content = """---
title: "Document with Frontmatter"
author: "Test Author"
date: "2024-01-01"
tags:
  - test
  - markdown
  - frontmatter
description: "This document has YAML frontmatter"
---

# Document Content

This document starts with YAML frontmatter.

## Section 1

Content after the frontmatter.

## Section 2

More content to process.
"""

        frontmatter_file = temp_dir / "frontmatter.md"
        frontmatter_file.write_text(frontmatter_content)

        result = processor.process_document(frontmatter_file, "frontmatter-test")

        assert result.success is True
        assert result.chunks_created > 0

    def test_code_heavy_document(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing documents with lots of code blocks."""
        code_heavy_content = """
# Code-Heavy Document

This document contains multiple code blocks in different languages.

## Python Code

```python
class DocumentProcessor:
    def __init__(self, config):
        self.config = config

    def process(self, document):
        # Process the document
        return self.chunk_document(document)

    def chunk_document(self, document):
        chunks = []
        # Chunking logic here
        return chunks
```

## JavaScript Code

```javascript
const processor = {
    config: {},

    process: function(document) {
        return this.chunkDocument(document);
    },

    chunkDocument: function(document) {
        const chunks = [];
        // Chunking logic here
        return chunks;
    }
};
```

## SQL Code

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO documents (title, content) VALUES
('Test Document', 'This is test content'),
('Another Document', 'More test content');

SELECT * FROM documents WHERE title LIKE '%Test%';
```

## Configuration Files

```yaml
database:
  host: localhost
  port: 5432
  name: documents_db

processing:
  chunk_size: 1000
  overlap: 200

features:
  - text_processing
  - code_highlighting
  - metadata_extraction
```

## JSON Data

```json
{
  "documents": [
    {
      "id": 1,
      "title": "Sample Document",
      "metadata": {
        "author": "Test Author",
        "created": "2024-01-01T00:00:00Z"
      }
    }
  ]
}
```
"""

        code_file = temp_dir / "code_heavy.md"
        code_file.write_text(code_heavy_content)

        result = processor.process_document(code_file, "code-heavy-test")

        assert result.success is True
        assert result.chunks_created > 0

    def test_performance_timing(
        self, processor: DocumentProcessor, test_documents: dict[str, Any]
    ) -> None:
        """Test processing performance and timing."""
        file_paths = list(test_documents.values())

        start_time = time.time()
        result = processor.process_batch(file_paths, "performance-test", max_workers=1)
        end_time = time.time()

        # Basic performance checks
        assert result.success_rate > 0
        assert result.total_processing_time > 0
        assert result.total_processing_time <= (end_time - start_time)
        assert result.processing_speed > 0  # chunks per second

    def test_concurrent_processing_safety(
        self, processor: DocumentProcessor, test_documents: dict[str, Any]
    ) -> None:
        """Test that concurrent processing is safe and consistent."""
        file_paths = list(test_documents.values())

        # Process with different worker counts
        result_1_worker = processor.process_batch(
            file_paths, "concurrent-test-1", max_workers=1
        )

        result_4_workers = processor.process_batch(
            file_paths, "concurrent-test-4", max_workers=4
        )

        # Results should be consistent regardless of worker count
        assert result_1_worker.total_files == result_4_workers.total_files
        assert result_1_worker.successful_files == result_4_workers.successful_files
        # Total chunks might vary slightly due to threading, but should be close
        chunk_diff = abs(result_1_worker.total_chunks - result_4_workers.total_chunks)
        assert chunk_diff <= 1


class TestDocumentProcessingErrors:
    """Test error handling in document processing."""

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create processor for error testing."""
        return DocumentProcessor(chunking_config)

    def test_file_permission_errors(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of file permission errors."""
        # This test is platform-dependent and might not work in all environments
        try:
            # Create a file and remove read permissions
            restricted_file = temp_dir / "restricted.md"
            restricted_file.write_text("# Restricted Document\nContent")
            restricted_file.chmod(0o000)  # No permissions

            result = processor.process_document(restricted_file, "test-permissions")

            # Should handle permission error gracefully
            assert result.success is False
            error_msg = result.error.lower()
            assert "permission" in error_msg or "access" in error_msg

        except OSError:
            # Skip test if we can't modify permissions (e.g., Windows)
            pytest.skip("Cannot modify file permissions on this platform")

        finally:
            # Restore permissions for cleanup
            try:
                restricted_file.chmod(0o644)
            except OSError:
                pass

    def test_corrupted_file_handling(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of corrupted or invalid files."""
        # Create a file with invalid UTF-8 sequences
        corrupted_file = temp_dir / "corrupted.md"
        with open(corrupted_file, "wb") as f:
            f.write(b"# Valid header\n")
            f.write(b"\xff\xfe\xfd")  # Invalid UTF-8
            f.write(b"\n# Another header\n")

        result = processor.process_document(corrupted_file, "corrupted-test")

        # Should handle encoding errors gracefully
        assert result.success is False
        assert result.error is not None

    def test_very_large_file_handling(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of extremely large files."""
        # Create a file that's too large (simulate with size check)
        large_file = temp_dir / "huge.md"
        large_file.write_text("# Small content")

        # Mock the file size to appear very large
        import os
        from unittest.mock import patch

        with patch.object(os.path, "getsize", return_value=200 * 1024 * 1024):
            result = processor.process_document(large_file, "huge-test")

            # Should handle size limit gracefully
            assert result.success is False
            error_msg = result.error.lower()
            assert "too large" in error_msg or "size" in error_msg

    def test_nonexistent_file_handling(self, processor: DocumentProcessor) -> None:
        """Test handling of non-existent files."""
        nonexistent_file = Path("does_not_exist.md")

        result = processor.process_document(nonexistent_file, "nonexistent-test")

        assert result.success is False
        error_msg = result.error.lower()
        assert "not found" in error_msg or "does not exist" in error_msg

    def test_directory_instead_of_file(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling when a directory is passed instead of a file."""
        result = processor.process_document(temp_dir, "directory-test")

        assert result.success is False
        error_msg = result.error.lower()
        assert "directory" in error_msg or "not a file" in error_msg

    def test_empty_file_handling(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of completely empty files."""
        empty_file = temp_dir / "empty.md"
        empty_file.write_text("")

        result = processor.process_document(empty_file, "empty-test")

        assert result.success is False
        assert "empty" in result.error.lower()

    def test_whitespace_only_file(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of files with only whitespace."""
        whitespace_file = temp_dir / "whitespace.md"
        whitespace_file.write_text("   \n\n\t\t\n   \n")

        result = processor.process_document(whitespace_file, "whitespace-test")

        # Should either succeed with no chunks or fail gracefully
        if result.success:
            assert result.chunks_created == 0
        else:
            error_msg = result.error.lower()
            assert "empty" in error_msg or "no content" in error_msg


class TestDocumentProcessingMetadata:
    """Test metadata handling in document processing."""

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create processor for metadata testing."""
        return DocumentProcessor(chunking_config)

    def test_metadata_extraction_and_enhancement(
        self,
        processor: DocumentProcessor,
        sample_markdown_file: Path,
    ) -> None:
        """Test that metadata is properly extracted and enhanced."""
        result = processor.process_document(sample_markdown_file, "metadata-test")

        assert result.success is True
        # Metadata testing would depend on the actual implementation
        # This is a placeholder for comprehensive metadata tests

    def test_custom_metadata_integration(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test integration of custom metadata."""
        # This test would verify that custom metadata is properly
        # integrated into the processing pipeline
        content = """
# Test Document

This is test content for metadata integration.

## Section 1

Content with metadata.
"""

        test_file = temp_dir / "metadata_test.md"
        test_file.write_text(content)

        result = processor.process_document(test_file, "custom-metadata-test")

        assert result.success is True
        assert result.chunks_created > 0
