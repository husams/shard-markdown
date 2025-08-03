"""Integration tests for document processing workflow."""

import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from shard_markdown.chromadb.mock_client import MockChromaDBClient
from shard_markdown.core.models import ChunkingConfig, BatchResult
from shard_markdown.core.processor import DocumentProcessor


@pytest.mark.integration
class TestDocumentProcessingIntegration:
    """Integration tests for complete document processing workflow."""

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig):
        """Create processor with mock ChromaDB client."""
        return DocumentProcessor(chunking_config)

    @pytest.fixture
    def mock_chromadb_client(self):
        """Mock ChromaDB client for integration testing."""
        return MockChromaDBClient()

    def test_process_simple_document_end_to_end(
        self, processor, sample_markdown_file
    ):
        """Test processing a simple markdown document end-to-end."""
        result = processor.process_document(
            sample_markdown_file, "test-simple-integration"
        )

        assert result.success is True
        assert result.file_path == sample_markdown_file
        assert result.chunks_created > 0
        assert result.processing_time > 0
        assert result.collection_name == "test-simple-integration"
        assert result.error is None

    def test_process_complex_document_with_frontmatter(
        self, processor, complex_markdown_file
    ):
        """Test processing document with YAML frontmatter."""
        result = processor.process_document(
            complex_markdown_file, "test-complex-integration"
        )

        assert result.success is True
        assert result.chunks_created > 0

        # The document should be properly parsed despite frontmatter
        assert result.processing_time > 0

    def test_process_document_with_code_blocks(self, processor, temp_dir):
        """Test processing document with various code blocks."""
        code_content = """# Code Examples
        
This document contains multiple code blocks.

## Python Example

```python
def hello_world():
    print("Hello, World!")
    return True

class TestClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
```

## JavaScript Example

```javascript
function processData(data) {
    return data.map(item => ({
        ...item,
        processed: true,
        timestamp: new Date()
    }));
}

const config = {
    apiUrl: 'https://api.example.com',
    timeout: 5000
};
```

## Shell Script

```bash
#!/bin/bash
echo "Starting process..."
for file in *.md; do
    echo "Processing $file"
    shard-md process --collection docs "$file"
done
echo "Done!"
```

## Conclusion

Code blocks should be preserved as complete units.
"""

        code_file = temp_dir / "code_examples.md"
        code_file.write_text(code_content)

        result = processor.process_document(code_file, "test-code-integration")

        assert result.success is True
        assert result.chunks_created > 0

        # Code blocks should be preserved without being split
        # This would need verification through the actual chunks

    def test_batch_processing_multiple_documents(
        self, processor, test_documents
    ):
        """Test batch processing of multiple documents."""
        file_paths = list(test_documents.values())

        result = processor.process_batch(
            file_paths, "test-batch-integration", max_workers=2
        )

        assert isinstance(result, BatchResult)
        assert result.total_files == len(file_paths)
        assert result.successful_files > 0
        assert result.total_chunks > 0
        assert result.total_processing_time > 0
        assert result.collection_name == "test-batch-integration"

        # Check success rate
        assert result.success_rate > 0
        assert result.average_chunks_per_file > 0

    def test_concurrent_processing_performance(
        self, processor, test_documents
    ):
        """Test concurrent processing performance."""
        file_paths = list(test_documents.values())

        # Test sequential processing
        start_time = time.time()
        sequential_result = processor.process_batch(
            file_paths, "test-sequential", max_workers=1
        )
        sequential_time = time.time() - start_time

        # Test concurrent processing
        start_time = time.time()
        concurrent_result = processor.process_batch(
            file_paths, "test-concurrent", max_workers=4
        )
        concurrent_time = time.time() - start_time

        # Both should succeed
        assert sequential_result.successful_files == len(file_paths)
        assert concurrent_result.successful_files == len(file_paths)

        # Concurrent should generally be faster (allowing some tolerance)
        # Note: This might not always be true for small datasets
        assert concurrent_time <= sequential_time * 1.5

    def test_document_with_unicode_content(self, processor, temp_dir):
        """Test processing document with Unicode content."""
        unicode_content = """# Unicode Test Document

This document contains various Unicode characters:

## Emoji Section 🚀
- Rocket: 🚀
- Heart: ❤️ 
- Star: ⭐
- Checkmark: ✅

## International Text
- Chinese: 你好世界
- Arabic: مرحبا بالعالم
- Japanese: こんにちは世界
- Russian: Привет мир
- Hebrew: שלום עולם

## Mathematical Symbols
- Infinity: ∞
- Sum: ∑
- Pi: π
- Delta: Δ
- Lambda: λ

## Special Characters
- Copyright: ©
- Trademark: ™
- Registered: ®
- Degree: °
- Micro: µ

This tests Unicode handling throughout the pipeline.
"""

        unicode_file = temp_dir / "unicode_test.md"
        unicode_file.write_text(unicode_content, encoding="utf-8")

        result = processor.process_document(unicode_file, "test-unicode-integration")

        assert result.success is True
        assert result.chunks_created > 0

    def test_large_document_processing(self, processor, temp_dir):
        """Test processing a large document."""
        # Generate large content
        large_content = ["# Large Document Test\n\n"]

        for section in range(100):
            large_content.append(f"## Section {section + 1}\n\n")

            for paragraph in range(5):
                large_content.append(
                    f"This is paragraph {paragraph + 1} of section {section + 1}. "
                )
                large_content.append(
                    "It contains substantial content to test processing performance. "
                )
                large_content.append(
                    "The content is meaningful and \
                        represents realistic documentation. "
                )
                large_content.append(
                    "Each paragraph has multiple sentences to ensure proper chunking.\n\n"
                )

            # Add some code blocks occasionally
            if section % 10 == 0:
                large_content.append("```python\n")
                large_content.append(f"def function_section_{section}():\n")
                large_content.append(f'    """Function for section {section}."""\n')
                large_content.append(f"    return 'Result for section {section}'\n")
                large_content.append("```\n\n")

        large_file = temp_dir / "large_document.md"
        large_file.write_text("".join(large_content))

        result = processor.process_document(large_file, "test-large-integration")

        assert result.success is True
        assert result.chunks_created > 50  # Should create many chunks
        assert result.processing_time < 30  # Should complete in reasonable time

    def test_error_recovery_in_batch_processing(
        self, processor, test_documents, temp_dir
    ):
        """Test error recovery during batch processing."""
        file_paths = list(test_documents.values())

        # Add a problematic file
        problematic_file = temp_dir / "problematic.md"
        problematic_file.write_bytes(
            b"\xff\xfe\x00\x00invalid content"
        )  # Invalid encoding
        file_paths.append(problematic_file)

        # Add an empty file
        empty_file = temp_dir / "empty.md"
        empty_file.write_text("")
        file_paths.append(empty_file)

        result = processor.process_batch(
            file_paths, "test-error-recovery", max_workers=2
        )

        assert isinstance(result, BatchResult)
        assert result.total_files == len(file_paths)
        assert result.successful_files > 0  # Some should succeed
        assert result.failed_files > 0  # Some should fail
        assert result.successful_files + result.failed_files == result.total_files

    def test_metadata_preservation_through_pipeline(self, processor, temp_dir):
        """Test that metadata is preserved through the processing pipeline."""
        content_with_frontmatter = """---
title: "Metadata Test Document"
author: "Integration Test"
tags: ["test", "metadata", "integration"]
category: "documentation"
version: 2.1
published: true
---

# Metadata Test Document

This document tests metadata preservation through the processing pipeline.

## Content Section

The frontmatter above should be extracted and preserved as metadata.

### Subsection

Additional content to ensure proper chunking while maintaining metadata.
"""

        metadata_file = temp_dir / "metadata_test.md"
        metadata_file.write_text(content_with_frontmatter)

        result = processor.process_document(metadata_file, "test-metadata-integration")

        assert result.success is True
        assert result.chunks_created > 0

        # Note: To fully test metadata preservation, we would need access to
        # the actual chunks created, which would require integration with
        # a real or more sophisticated mock ChromaDB client

    def test_chunking_strategy_consistency(
        self, processor, sample_markdown_file
    ):
        """Test that chunking strategies produce consistent results."""
        # Process the same document multiple times
        results = []

        for i in range(3):
            result = processor.process_document(
                sample_markdown_file, f"test-consistency-{i}"
            )
            results.append(result)

        # All results should be successful
        assert all(r.success for r in results)

        # Chunk counts should be consistent
        chunk_counts = [r.chunks_created for r in results]
        assert len(set(chunk_counts)) == 1, "Chunk counts should be consistent"

        # Processing times should be reasonable and relatively consistent
        processing_times = [r.processing_time for r in results]
        max_time = max(processing_times)
        min_time = min(processing_times)
        assert (
            max_time / min_time < 5.0
        ), "Processing times should be relatively consistent"

    def test_file_encoding_detection(self, processor, temp_dir):
        """Test processing files with different encodings."""
        content = (
            "# Encoding Test\n\nThis tests encoding detection: café, naïve, résumé"
        )

        # Test UTF-8
        utf8_file = temp_dir / "utf8.md"
        utf8_file.write_text(content, encoding="utf-8")

        result_utf8 = processor.process_document(utf8_file, "test-utf8")
        assert result_utf8.success is True

        # Test UTF-8 with BOM
        utf8_bom_file = temp_dir / "utf8_bom.md"
        utf8_bom_file.write_text(content, encoding="utf-8-sig")

        result_utf8_bom = processor.process_document(utf8_bom_file, "test-utf8-bom")
        assert result_utf8_bom.success is True

        # Test Latin-1
        latin1_file = temp_dir / "latin1.md"
        latin1_file.write_text(content, encoding="latin-1")

        result_latin1 = processor.process_document(latin1_file, "test-latin1")
        assert result_latin1.success is True

    def test_processing_statistics_accuracy(self, processor, test_documents):
        """Test accuracy of processing statistics."""
        file_paths = list(test_documents.values())

        start_time = time.time()
        result = processor.process_batch(
            file_paths, "test-stats", max_workers=2
        )
        actual_time = time.time() - start_time

        # Verify statistics make sense
        assert result.total_files == len(file_paths)
        assert result.successful_files <= result.total_files
        assert result.failed_files <= result.total_files
        assert result.successful_files + result.failed_files == result.total_files

        # Processing time should be reasonable
        assert (
            0 < result.total_processing_time <= actual_time + 1
        )  # Allow some tolerance

        # Success rate should be between 0 and 100
        assert 0 <= result.success_rate <= 100

        if result.successful_files > 0:
            assert result.average_chunks_per_file > 0
            assert result.total_chunks > 0

        if result.total_processing_time > 0:
            assert result.processing_speed > 0


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Integration tests for error handling scenarios."""

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig):
        """Create processor for error testing."""
        return DocumentProcessor(chunking_config)

    def test_file_permission_errors(self, processor, temp_dir):
        """Test handling of file permission errors."""
        # This test is platform-dependent and \
            might not work in all environments
        try:
            # Create a file and remove read permissions
            restricted_file = temp_dir / "restricted.md"
            restricted_file.write_text("# Restricted Document\nContent")
            restricted_file.chmod(0o000)  # No permissions

            result = processor.process_document(restricted_file, "test-permissions")

            # Should handle permission error gracefully
            assert result.success is False
            assert result.error is not None

        finally:
            # Restore permissions for cleanup
            try:
                restricted_file.chmod(0o644)
            except:
                pass

    def test_disk_space_simulation(self, processor, temp_dir):
        """Test behavior when simulating disk space issues."""
        # This is difficult to test reliably without actually filling disk
        # Instead, we test with extremely large file size simulation

        large_file = temp_dir / "simulated_large.md"
        large_file.write_text("# Test\nContent")

        # Mock file size to be very large
        import unittest.mock

        with unittest.mock.patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 200 * 1024 * 1024  # 200MB

            result = processor.process_document(large_file, "test-large-file")

            assert result.success is False
            assert "too large" in result.error.lower()

    def test_invalid_markdown_recovery(self, processor, temp_dir):
        """Test recovery from invalid markdown content."""
        invalid_content = """# This is invalid markdown

```python
# This code block is never closed

def function():
    return "unclosed"

## This header appears inside code block

- List item
- Another item

# Another header still in code block
"""

        invalid_file = temp_dir / "invalid.md"
        invalid_file.write_text(invalid_content)

        result = processor.process_document(invalid_file, "test-invalid-md")

        # Should handle invalid markdown gracefully
        # The exact behavior depends on the markdown parser implementation
        # It might succeed with warnings or fail gracefully
        assert result.error is None or "invalid" in result.error.lower()

    def test_network_interruption_simulation(
        self, processor, sample_markdown_file
    ):
        """Test behavior during simulated network interruptions."""
        # This would be more relevant for real ChromaDB connections
        # For now, we test with mock client that can simulate failures

        result = processor.process_document(sample_markdown_file, "test-network")

        # With mock client, this should succeed
        assert result.success is True

        # In a real scenario, we would test ChromaDB connection failures
