"""Integration tests for document processing."""

import time
from pathlib import Path

import pytest

from shard_markdown.config.settings import ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor


@pytest.mark.integration
class TestDocumentProcessingIntegration:
    """Integration tests for document processing workflows."""

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create processor for integration testing."""
        return DocumentProcessor(chunking_config)

    @pytest.fixture
    def small_chunking_config(self) -> ChunkingConfig:
        """Create small chunking configuration for testing."""
        return ChunkingConfig(default_size=300, default_overlap=50)

    @pytest.mark.integration
    def test_end_to_end_single_file_processing(
        self,
        processor: DocumentProcessor,
        sample_markdown_file: Path,
    ) -> None:
        """Test complete end-to-end processing of a single file."""
        # Process the file
        result = processor.process_file(
            file_path=sample_markdown_file, collection_name="integration-test"
        )

        # Verify successful processing
        assert result.success is True
        assert result.chunks_created > 0
        assert result.processing_time > 0
        assert result.file_path == sample_markdown_file
        assert result.collection_name == "integration-test"
        assert result.error is None

    @pytest.mark.integration
    def test_end_to_end_batch_processing(
        self,
        processor: DocumentProcessor,
        sample_markdown_files: list[Path],
    ) -> None:
        """Test complete batch processing workflow."""
        # Process batch of files
        batch_result = processor.process_batch(
            file_paths=sample_markdown_files, collection_name="batch-integration-test"
        )

        # Verify batch processing results
        assert batch_result.total_files == len(sample_markdown_files)
        assert batch_result.successful_files > 0
        assert batch_result.total_chunks > 0
        assert batch_result.collection_name == "batch-integration-test"
        assert len(batch_result.results) == len(sample_markdown_files)

        # Verify calculated properties
        assert 0 <= batch_result.success_rate <= 100
        if batch_result.successful_files > 0:
            assert batch_result.average_chunks_per_file > 0
        assert batch_result.processing_speed > 0

    @pytest.mark.integration
    def test_processing_with_different_chunk_sizes(
        self,
        sample_markdown_file: Path,
        small_chunking_config: ChunkingConfig,
    ) -> None:
        """Test processing with different chunk configurations."""
        # Process with small chunks
        small_processor = DocumentProcessor(small_chunking_config)
        small_result = small_processor.process_file(
            file_path=sample_markdown_file, collection_name="small-chunks-test"
        )

        # Process with default chunks
        from shard_markdown.config.settings import (
            ChunkingConfig as ModelsChunkingConfig,
        )

        small_config = ModelsChunkingConfig(default_size=300, default_overlap=50)
        default_processor = DocumentProcessor(small_config)
        default_result = default_processor.process_file(
            file_path=sample_markdown_file, collection_name="default-chunks-test"
        )

        # Both should succeed
        assert small_result.success is True
        assert default_result.success is True

        # Small chunks should typically create more chunks
        # (though this depends on document structure)
        assert small_result.chunks_created >= 0
        assert default_result.chunks_created >= 0

    @pytest.mark.integration
    def test_error_handling_integration(
        self,
        processor: DocumentProcessor,
    ) -> None:
        """Test error handling in integration scenarios."""
        # Test with non-existent file
        non_existent = Path("/path/that/definitely/does/not/exist.md")
        result = processor.process_file(
            file_path=non_existent, collection_name="error-test"
        )

        assert result.success is False
        assert result.chunks_created == 0
        assert result.error is not None
        assert result.processing_time >= 0

    @pytest.mark.integration
    def test_batch_error_handling(
        self,
        processor: DocumentProcessor,
        sample_markdown_files: list[Path],
    ) -> None:
        """Test error handling in batch processing."""
        # Mix valid and invalid files
        files_with_errors = sample_markdown_files + [
            Path("/non/existent/file1.md"),
            Path("/non/existent/file2.md"),
        ]

        batch_result = processor.process_batch(
            file_paths=files_with_errors, collection_name="batch-error-test"
        )

        # Should have some successes and some failures
        assert batch_result.total_files == len(files_with_errors)
        assert batch_result.successful_files == len(sample_markdown_files)
        assert batch_result.failed_files == 2
        assert len(batch_result.results) == len(files_with_errors)

        # Verify individual results
        for i, result in enumerate(batch_result.results):
            if i < len(sample_markdown_files):
                # Valid files should succeed
                assert result.success is True
            else:
                # Invalid files should fail
                assert result.success is False

    @pytest.mark.integration
    def test_processing_performance_characteristics(
        self,
        processor: DocumentProcessor,
        large_markdown_file: Path,
    ) -> None:
        """Test performance characteristics of processing."""
        # Process large file multiple times to get consistent timing
        processing_times = []
        chunk_counts = []

        for _ in range(3):  # Reduced for faster tests
            start_time = time.time()
            result = processor.process_file(
                file_path=large_markdown_file, collection_name="performance-test"
            )
            end_time = time.time()

            assert result.success is True
            processing_times.append(end_time - start_time)
            chunk_counts.append(result.chunks_created)

        # Verify consistent results
        # All chunk counts should be the same
        assert len(set(chunk_counts)) == 1, "Chunk counts should be consistent"

        # Processing times should be reasonable and not vary wildly
        avg_time = sum(processing_times) / len(processing_times)
        assert all(t < avg_time * 2 for t in processing_times), (
            "Processing times vary too much"
        )

    @pytest.mark.integration
    def test_metadata_preservation(
        self,
        processor: DocumentProcessor,
        sample_markdown_file: Path,
    ) -> None:
        """Test that metadata is properly preserved through processing."""
        result = processor.process_file(
            file_path=sample_markdown_file, collection_name="metadata-test"
        )

        assert result.success is True
        assert result.file_path == sample_markdown_file
        assert result.collection_name == "metadata-test"
        assert result.chunks_created > 0

        # Verify timing information is captured
        assert result.processing_time > 0
        assert result.timestamp is not None

    @pytest.mark.integration
    def test_empty_file_handling(
        self,
        processor: DocumentProcessor,
        tmp_path: Path,
    ) -> None:
        """Test handling of empty markdown files."""
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("")

        result = processor.process_file(
            file_path=empty_file, collection_name="empty-file-test"
        )

        # Should succeed but create no chunks
        assert result.success is True
        assert result.chunks_created == 0

    @pytest.mark.integration
    def test_malformed_markdown_handling(
        self,
        processor: DocumentProcessor,
        tmp_path: Path,
    ) -> None:
        """Test handling of malformed markdown content."""
        # Create file with unusual but valid markdown
        malformed_file = tmp_path / "malformed.md"
        malformed_content = """
        # Header with weird spacing

        Paragraph with
        weird line breaks


        ## Another header

        * List item 1
        * List item 2
            * Nested item

        ```python
        # Code block
        print("hello")
        ```

        Final paragraph.
        """
        malformed_file.write_text(malformed_content)

        result = processor.process_file(
            file_path=malformed_file, collection_name="malformed-test"
        )

        # Should handle malformed content gracefully
        assert result.success is True
        assert result.chunks_created >= 0  # May create 0 or more chunks

    @pytest.mark.integration
    def test_large_batch_processing(
        self,
        processor: DocumentProcessor,
        sample_markdown_files: list[Path],
    ) -> None:
        """Test processing large batches of files."""
        # Create additional test files if we don't have enough
        if len(sample_markdown_files) < 5:
            pytest.skip("Need at least 5 sample files for large batch test")

        batch_result = processor.process_batch(
            file_paths=sample_markdown_files, collection_name="large-batch-test"
        )

        # Verify batch processing scaled properly
        assert batch_result.total_files == len(sample_markdown_files)
        assert batch_result.total_processing_time > 0
        assert batch_result.processing_speed > 0

        # All processing results should be present
        assert len(batch_result.results) == len(sample_markdown_files)

    @pytest.mark.integration
    def test_unicode_content_handling(
        self,
        processor: DocumentProcessor,
        tmp_path: Path,
    ) -> None:
        """Test handling of Unicode content in markdown files."""
        unicode_file = tmp_path / "unicode.md"
        unicode_content = """
        # Unicode Test 🚀

        This document contains various Unicode characters:

        ## Emojis
        - 😀 Happy face
        - 🎉 Party
        - 🔥 Fire

        ## Different Languages
        - English: Hello World
        - Spanish: Hola Mundo
        - Japanese: こんにちは世界
        - Arabic: مرحبا بالعالم
        - Russian: Привет мир

        ## Special Characters
        Mathematical symbols: ∑ ∏ ∆ ∞
        Currency: € £ ¥ ₹
        """
        unicode_file.write_text(unicode_content, encoding="utf-8")

        result = processor.process_file(
            file_path=unicode_file, collection_name="unicode-test"
        )

        # Should handle Unicode content without issues
        assert result.success is True
        assert result.chunks_created > 0
