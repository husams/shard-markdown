"""Unit tests for DocumentProcessor."""

import time
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from shard_markdown.config.settings import ProcessingConfig
from shard_markdown.core.models import BatchResult, ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor


@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock all dependencies at module level before any tests run."""
    with (
        patch("shard_markdown.core.processor.MarkdownParser") as mock_parser_class,
        patch("shard_markdown.core.processor.ChunkingEngine") as mock_chunker_class,
        patch("shard_markdown.core.processor.MetadataExtractor") as mock_metadata_class,
    ):
        # Store mocks for access in tests
        yield {
            "parser_class": mock_parser_class,
            "parser": mock_parser_class.return_value,
            "chunker_class": mock_chunker_class,
            "chunker": mock_chunker_class.return_value,
            "metadata_class": mock_metadata_class,
            "metadata": mock_metadata_class.return_value,
        }


class TestDocumentProcessor:
    """Test suite for DocumentProcessor class."""

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create DocumentProcessor instance for testing."""
        return DocumentProcessor(chunking_config)

    @pytest.fixture
    def strict_processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create DocumentProcessor instance with strict validation for testing."""
        config = ProcessingConfig(strict_validation=True)
        return DocumentProcessor(chunking_config, processing_config=config)

    def test_processor_initialization(self, chunking_config: ChunkingConfig) -> None:
        """Test processor initializes correctly."""
        processor = DocumentProcessor(chunking_config)

        assert processor.chunking_config == chunking_config
        assert processor.parser is not None
        assert processor.chunker is not None
        assert processor.metadata_extractor is not None

    def test_process_document_success(
        self,
        processor: DocumentProcessor,
        sample_markdown_file: Path,
        sample_chunks: Any,
        mock_dependencies: dict,
    ) -> None:
        """Test successful document processing."""
        # Setup mocks using the dependency dict
        mock_parser = mock_dependencies["parser"]
        mock_chunker = mock_dependencies["chunker"]
        mock_metadata = mock_dependencies["metadata"]

        mock_parser.parse.return_value = Mock()
        mock_chunker.chunk_document.return_value = sample_chunks
        mock_metadata.extract_file_metadata.return_value = {"file_type": "markdown"}
        mock_metadata.extract_document_metadata.return_value = {"title": "Test"}
        mock_metadata.enhance_chunk_metadata.return_value = {"enhanced": True}

        result = processor.process_document(sample_markdown_file, "test-collection")

        assert result.success is True
        assert result.file_path == sample_markdown_file
        assert result.chunks_created == len(sample_chunks)
        assert result.collection_name == "test-collection"
        assert result.processing_time > 0

        # Verify method calls
        mock_parser.parse.assert_called_once()
        mock_chunker.chunk_document.assert_called_once()
        mock_metadata.extract_file_metadata.assert_called_once()
        mock_metadata.extract_document_metadata.assert_called_once()

    def test_process_document_file_not_found_strict_mode(
        self, strict_processor: DocumentProcessor
    ) -> None:
        """Test processing with non-existent file in strict mode."""
        non_existent_file = Path("nonexistent.md")

        result = strict_processor.process_document(non_existent_file, "test-collection")

        assert result.success is False
        assert result.error is not None
        assert (
            "not found" in result.error.lower()
            or "no such file" in result.error.lower()
        )
        assert result.chunks_created == 0

    def test_process_document_file_not_found_graceful_mode(
        self, processor: DocumentProcessor
    ) -> None:
        """Test processing with non-existent file in graceful mode."""
        non_existent_file = Path("nonexistent.md")

        result = processor.process_document(non_existent_file, "test-collection")

        # In graceful mode, missing files return failure with empty content error
        assert result.success is False
        assert result.error is not None
        assert "empty" in result.error.lower()
        assert result.chunks_created == 0

    def test_process_document_empty_file_strict_mode(
        self, strict_processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing empty file in strict mode."""
        empty_file = temp_dir / "empty.md"
        empty_file.write_text("")

        result = strict_processor.process_document(empty_file, "test-collection")

        assert result.success is False
        assert result.error and "empty" in result.error.lower()

    def test_process_document_empty_file_graceful_mode(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing empty file in graceful mode."""
        empty_file = temp_dir / "empty.md"
        empty_file.write_text("")

        result = processor.process_document(empty_file, "test-collection")

        # In graceful mode, empty files now consistently return failure
        assert result.success is False
        assert result.error is not None
        assert "empty" in result.error.lower()
        assert result.chunks_created == 0

    def test_process_document_large_file(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test processing file that's too large."""
        # Create processor with a very small file size limit (100 bytes)
        config = ProcessingConfig(max_file_size=100)
        processor = DocumentProcessor(chunking_config, processing_config=config)

        large_file = temp_dir / "large.md"
        # Create a file larger than 100 bytes
        large_content = "# Large Header\n\n" + "This is a very long content " * 10
        large_file.write_text(large_content)

        result = processor.process_document(large_file, "test-collection")

        assert result.success is False
        assert result.error and "too large" in result.error.lower()

    def test_process_document_no_chunks_generated_strict_mode(
        self,
        strict_processor: DocumentProcessor,
        sample_markdown_file: Path,
        mock_dependencies: dict,
    ) -> None:
        """Test processing when no chunks are generated in strict mode."""
        # Setup mocks using the dependency dict
        mock_parser = mock_dependencies["parser"]
        mock_chunker = mock_dependencies["chunker"]
        mock_metadata = mock_dependencies["metadata"]

        mock_parser.parse.return_value = Mock()
        mock_chunker.chunk_document.return_value = []  # No chunks
        mock_metadata.extract_file_metadata.return_value = {}
        mock_metadata.extract_document_metadata.return_value = {}

        result = strict_processor.process_document(
            sample_markdown_file, "test-collection"
        )

        assert result.success is False
        assert result.error and "no chunks generated" in result.error.lower()
        assert result.chunks_created == 0

    def test_process_document_no_chunks_generated_graceful_mode(
        self,
        processor: DocumentProcessor,
        sample_markdown_file: Path,
        mock_dependencies: dict,
    ) -> None:
        """Test processing when no chunks are generated in graceful mode."""
        # Setup mocks using the dependency dict
        mock_parser = mock_dependencies["parser"]
        mock_chunker = mock_dependencies["chunker"]
        mock_metadata = mock_dependencies["metadata"]

        mock_parser.parse.return_value = Mock()
        mock_chunker.chunk_document.return_value = []  # No chunks
        mock_metadata.extract_file_metadata.return_value = {}
        mock_metadata.extract_document_metadata.return_value = {}

        result = processor.process_document(sample_markdown_file, "test-collection")

        # In graceful mode, no chunks is acceptable
        assert result.success is True
        assert result.error is None
        assert result.chunks_created == 0

    def test_process_document_parsing_error(
        self,
        processor: DocumentProcessor,
        sample_markdown_file: Path,
        mock_dependencies: dict,
    ) -> None:
        """Test handling of parsing errors."""
        mock_parser = mock_dependencies["parser"]
        mock_parser.parse.side_effect = Exception("Parsing failed")

        result = processor.process_document(sample_markdown_file, "test-collection")

        assert result.success is False
        assert result.error and "parsing failed" in result.error.lower()

    def test_read_file_multiple_encodings(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test reading file with different encodings."""
        # Create UTF-8 file
        utf8_file = temp_dir / "utf8.md"
        content = "# Test with UTF-8 content: café"
        utf8_file.write_text(content, encoding="utf-8")

        result = processor._read_file(utf8_file)
        assert "café" in result

        # Create Latin-1 file
        latin1_file = temp_dir / "latin1.md"
        latin1_file.write_text(content, encoding="latin-1")

        result = processor._read_file(latin1_file)
        assert result is not None

    def test_generate_chunk_id(
        self, processor: DocumentProcessor, sample_markdown_file: Path
    ) -> None:
        """Test chunk ID generation."""
        chunk_id_1 = processor._generate_chunk_id(sample_markdown_file, 0)
        chunk_id_2 = processor._generate_chunk_id(sample_markdown_file, 1)

        assert chunk_id_1 != chunk_id_2
        assert chunk_id_1.endswith("_0000")
        assert chunk_id_2.endswith("_0001")
        assert len(chunk_id_1.split("_")[0]) == 16  # Hash part

    def test_enhance_chunks(
        self,
        processor: DocumentProcessor,
        sample_chunks: Any,
        sample_markdown_file: Path,
        mock_dependencies: dict,
    ) -> None:
        """Test chunk enhancement with metadata."""
        mock_metadata = mock_dependencies["metadata"]
        mock_metadata.enhance_chunk_metadata.return_value = {
            "enhanced": True,
            "chunk_index": 0,
            "total_chunks": 3,
        }

        file_metadata = {"file_type": "markdown"}
        doc_metadata = {"title": "Test Document"}

        enhanced_chunks = processor._enhance_chunks(
            sample_chunks, file_metadata, doc_metadata, sample_markdown_file
        )

        assert len(enhanced_chunks) == len(sample_chunks)

        for i, chunk in enumerate(enhanced_chunks):
            assert chunk.id is not None
            assert chunk.content == sample_chunks[i].content
            assert "enhanced" in chunk.metadata

    def test_batch_processing_success(
        self,
        processor: DocumentProcessor,
        test_documents: Any,
        sample_chunks: Any,
        mock_dependencies: dict,
    ) -> None:
        """Test successful batch processing."""
        # Setup mocks using the dependency dict
        mock_parser = mock_dependencies["parser"]
        mock_chunker = mock_dependencies["chunker"]
        mock_metadata = mock_dependencies["metadata"]

        mock_parser.parse.return_value = Mock()
        mock_chunker.chunk_document.return_value = sample_chunks
        mock_metadata.extract_file_metadata.return_value = {"file_type": "markdown"}
        mock_metadata.extract_document_metadata.return_value = {"title": "Test"}
        mock_metadata.enhance_chunk_metadata.return_value = {"enhanced": True}

        file_paths = list(test_documents.values())
        result = processor.process_batch(file_paths, "test-collection", max_workers=2)

        assert isinstance(result, BatchResult)
        assert result.total_files == len(file_paths)
        assert result.successful_files == len(file_paths)
        assert result.failed_files == 0
        assert result.total_chunks == len(file_paths) * len(sample_chunks)
        assert result.collection_name == "test-collection"
        assert result.success_rate == 100.0

    def test_batch_processing_partial_failure(
        self,
        processor: DocumentProcessor,
        test_documents: Any,
        mock_dependencies: dict,
    ) -> None:
        """Test batch processing with some failures."""
        # Setup mocks using the dependency dict
        mock_parser = mock_dependencies["parser"]
        mock_chunker = mock_dependencies["chunker"]
        mock_metadata = mock_dependencies["metadata"]

        # Setup mocks - make one file fail
        call_count = 0

        def side_effect(*args: Any) -> Mock:
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Second call fails
                raise Exception("Processing failed")
            return Mock()

        mock_parser.parse.side_effect = side_effect
        mock_chunker.chunk_document.return_value = []
        mock_metadata.extract_file_metadata.return_value = {}
        mock_metadata.extract_document_metadata.return_value = {}

        file_paths = list(test_documents.values())[:2]  # Only test 2 files
        result = processor.process_batch(file_paths, "test-collection", max_workers=1)

        assert result.total_files == 2
        # In graceful mode, files with no chunks succeed
        assert result.successful_files == 1  # One succeeds with 0 chunks, one fails
        assert result.failed_files == 1
        assert result.success_rate == 50.0

    def test_batch_processing_empty_list(self, processor: DocumentProcessor) -> None:
        """Test batch processing with empty file list."""
        result = processor.process_batch([], "test-collection")

        assert result.total_files == 0
        assert result.successful_files == 0
        assert result.failed_files == 0
        assert result.total_chunks == 0

    def test_concurrent_processing(
        self,
        processor: DocumentProcessor,
        test_documents: Any,
        sample_chunks: Any,
        mock_dependencies: dict,
    ) -> None:
        """Test concurrent processing with multiple workers."""
        # Setup mocks using the dependency dict
        mock_parser = mock_dependencies["parser"]
        mock_chunker = mock_dependencies["chunker"]
        mock_metadata = mock_dependencies["metadata"]

        mock_parser.parse.return_value = Mock()
        mock_chunker.chunk_document.return_value = sample_chunks
        mock_metadata.extract_file_metadata.return_value = {"file_type": "markdown"}
        mock_metadata.extract_document_metadata.return_value = {"title": "Test"}
        mock_metadata.enhance_chunk_metadata.return_value = {"enhanced": True}

        file_paths = list(test_documents.values())

        start_time = time.time()
        result = processor.process_batch(file_paths, "test-collection", max_workers=4)
        end_time = time.time()

        # With concurrency, should process faster than sequential
        assert result.successful_files == len(file_paths)
        assert (
            result.total_processing_time < end_time - start_time + 1
        )  # Allow some tolerance

    @pytest.mark.parametrize("max_workers", [1, 2, 4, 8])
    def test_batch_processing_different_worker_counts(
        self,
        processor: DocumentProcessor,
        test_documents: Any,
        sample_chunks: Any,
        mock_dependencies: dict,
        max_workers: int,
    ) -> None:
        """Test batch processing with different worker counts."""
        # Setup mocks using the dependency dict
        mock_parser = mock_dependencies["parser"]
        mock_chunker = mock_dependencies["chunker"]
        mock_metadata = mock_dependencies["metadata"]

        mock_parser.parse.return_value = Mock()
        mock_chunker.chunk_document.return_value = sample_chunks
        mock_metadata.extract_file_metadata.return_value = {"file_type": "markdown"}
        mock_metadata.extract_document_metadata.return_value = {"title": "Test"}
        mock_metadata.enhance_chunk_metadata.return_value = {"enhanced": True}

        file_paths = list(test_documents.values())
        result = processor.process_batch(
            file_paths, "test-collection", max_workers=max_workers
        )

        assert result.successful_files == len(file_paths)
        assert result.total_chunks == len(file_paths) * len(sample_chunks)

    def test_processing_time_measurement(
        self,
        processor: DocumentProcessor,
        sample_markdown_file: Path,
        mock_dependencies: dict,
    ) -> None:
        """Test that processing time is measured correctly."""
        mock_parser = mock_dependencies["parser"]
        mock_chunker = mock_dependencies["chunker"]
        mock_metadata = mock_dependencies["metadata"]

        # Add delay to processing
        def delayed_parse(*args: Any) -> Mock:
            time.sleep(0.01)  # 10ms delay
            return Mock()

        mock_parser.parse.side_effect = delayed_parse
        mock_chunker.chunk_document.return_value = []
        mock_metadata.extract_file_metadata.return_value = {}
        mock_metadata.extract_document_metadata.return_value = {}

        result = processor.process_document(sample_markdown_file, "test-collection")

        assert result.processing_time >= 0.01  # Should include the delay
        assert result.processing_time < 1.0  # But not too long

    def test_whitespace_only_file_handling(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test handling of files with only whitespace."""
        whitespace_file = temp_dir / "whitespace.md"
        whitespace_file.write_text("   \n\n\t\t\n   \n")

        result = processor.process_document(whitespace_file, "test-collection")

        # In graceful mode with skip_empty_files=True (default), should fail consistently
        assert result.success is False
        assert result.error is not None
        assert "empty" in result.error.lower()
        assert result.chunks_created == 0

    def test_whitespace_only_file_strict_mode(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test handling of whitespace-only files in strict mode with skip disabled."""
        # Create processor with strict validation and skip_empty_files=False
        config = ProcessingConfig(strict_validation=True, skip_empty_files=False)
        processor = DocumentProcessor(chunking_config, processing_config=config)

        whitespace_file = temp_dir / "whitespace.md"
        whitespace_file.write_text("   \n\n\t\t\n   \n")

        result = processor.process_document(whitespace_file, "test-collection")

        # In strict mode with skip_empty_files=False, whitespace-only files should fail
        assert result.success is False
        assert result.error is not None
        assert "whitespace" in result.error.lower()

    def test_whitespace_only_file_strict_mode_with_skip(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test handling of whitespace-only files in strict mode with skip enabled."""
        # Create processor with strict validation and skip_empty_files=True (default)
        config = ProcessingConfig(strict_validation=True, skip_empty_files=True)
        processor = DocumentProcessor(chunking_config, processing_config=config)

        whitespace_file = temp_dir / "whitespace.md"
        whitespace_file.write_text("   \n\n\t\t\n   \n")

        result = processor.process_document(whitespace_file, "test-collection")

        # In strict mode with skip_empty_files=True, whitespace files are empty
        assert result.success is False
        assert result.error is not None
        assert "empty" in result.error.lower()


class TestDocumentProcessorWithoutMocks:
    """Test DocumentProcessor without mocks for real file operations."""

    def test_process_document_encoding_error(
        self, temp_dir: Path, chunking_config: ChunkingConfig
    ) -> None:
        """Test handling of encoding errors with real file reading."""
        # Create processor without mocks to test real file reading
        processor = DocumentProcessor(chunking_config)

        # Create file with truly invalid bytes that can't be decoded
        invalid_file = temp_dir / "invalid_encoding.md"
        # Use bytes that are invalid in both UTF-8 and Latin-1
        # Byte sequence that's invalid UTF-8 and problematic
        invalid_file.write_bytes(
            b"\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f"
        )

        result = processor.process_document(invalid_file, "test-collection")

        # Corrupted files should fail in all modes due to security concerns
        # The new behavior rejects corrupted files to prevent data integrity issues
        assert result.success is False
        assert result.error is not None
        assert "corrupted encoding" in result.error.lower()
        assert result.chunks_created == 0


class TestBackwardCompatibility:
    """Test backward compatibility with legacy behavior."""

    def test_process_document_empty_file(
        self, chunking_config: ChunkingConfig, temp_dir: Path
    ) -> None:
        """Test processing empty file with strict mode (legacy behavior)."""
        # Create processor with strict validation for backward compatibility
        config = ProcessingConfig(strict_validation=True)
        processor = DocumentProcessor(chunking_config, processing_config=config)

        empty_file = temp_dir / "empty.md"
        empty_file.write_text("")

        result = processor.process_document(empty_file, "test-collection")

        # Legacy behavior: empty files should fail
        assert result.success is False
        assert result.error and "empty" in result.error.lower()

    def test_process_document_file_not_found(
        self, chunking_config: ChunkingConfig
    ) -> None:
        """Test processing with non-existent file with strict mode (legacy behavior)."""
        # Create processor with strict validation for backward compatibility
        config = ProcessingConfig(strict_validation=True)
        processor = DocumentProcessor(chunking_config, processing_config=config)

        non_existent_file = Path("nonexistent.md")

        result = processor.process_document(non_existent_file, "test-collection")

        # Legacy behavior: missing files should fail
        assert result.success is False
        assert result.error is not None
        assert (
            "not found" in result.error.lower()
            or "no such file" in result.error.lower()
        )
        assert result.chunks_created == 0
