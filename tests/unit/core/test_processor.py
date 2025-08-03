"""Unit tests for DocumentProcessor."""

import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from shard_markdown.core.models import BatchResult, ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor


class TestDocumentProcessor:
    """Test suite for DocumentProcessor class."""

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig):
        """Create DocumentProcessor instance for testing."""
        return DocumentProcessor(chunking_config)

    @pytest.fixture
    def mock_parser(self):
        """Mock MarkdownParser."""
        with patch("shard_markdown.core.processor.MarkdownParser") as mock:
            yield mock.return_value

    @pytest.fixture
    def mock_chunker(self):
        """Mock ChunkingEngine."""
        with patch("shard_markdown.core.processor.ChunkingEngine") as mock:
            yield mock.return_value

    @pytest.fixture
    def mock_metadata_extractor(self):
        """Mock MetadataExtractor."""
        with patch("shard_markdown.core.processor.MetadataExtractor") as mock:
            yield mock.return_value

    def test_processor_initialization(self, chunking_config):
        """Test processor initializes correctly."""
        processor = DocumentProcessor(chunking_config)

        assert processor.chunking_config == chunking_config
        assert processor.parser is not None
        assert processor.chunker is not None
        assert processor.metadata_extractor is not None

    def test_process_document_success(
        self,
        processor,
        sample_markdown_file,
        sample_chunks,
        mock_parser,
        mock_chunker,
        mock_metadata_extractor,
    ):
        """Test successful document processing."""
        # Setup mocks
        mock_parser.parse.return_value = Mock()
        mock_chunker.chunk_document.return_value = sample_chunks
        mock_metadata_extractor.extract_file_metadata.return_value = {
            "file_type": "markdown"
        }
        mock_metadata_extractor.extract_document_metadata.return_value = {
            "title": "Test"
        }
        mock_metadata_extractor.enhance_chunk_metadata.return_value = {"enhanced": True}

        result = processor.process_document(sample_markdown_file, "test-collection")

        assert result.success is True
        assert result.file_path == sample_markdown_file
        assert result.chunks_created == len(sample_chunks)
        assert result.collection_name == "test-collection"
        assert result.processing_time > 0

        # Verify method calls
        mock_parser.parse.assert_called_once()
        mock_chunker.chunk_document.assert_called_once()
        mock_metadata_extractor.extract_file_metadata.assert_called_once()
        mock_metadata_extractor.extract_document_metadata.assert_called_once()

    def test_process_document_file_not_found(self, processor):
        """Test processing with non-existent file."""
        non_existent_file = Path("nonexistent.md")

        result = processor.process_document(non_existent_file, "test-collection")

        assert result.success is False
        assert result.error is not None
        assert (
            "not found" in result.error.lower()
            or "no such file" in result.error.lower()
        )
        assert result.chunks_created == 0

    def test_process_document_empty_file(self, processor, temp_dir):
        """Test processing empty file."""
        empty_file = temp_dir / "empty.md"
        empty_file.write_text("")

        result = processor.process_document(empty_file, "test-collection")

        assert result.success is False
        assert "empty" in result.error.lower()

    def test_process_document_large_file(self, processor, temp_dir):
        """Test processing file that's too large."""
        large_file = temp_dir / "large.md"

        # Create file larger than 100MB limit
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = 150 * 1024 * 1024  # 150MB

            result = processor.process_document(large_file, "test-collection")

            assert result.success is False
            assert "too large" in result.error.lower()

    def test_process_document_no_chunks_generated(
        self,
        processor,
        sample_markdown_file,
        mock_parser,
        mock_chunker,
        mock_metadata_extractor,
    ):
        """Test processing when no chunks are generated."""
        # Setup mocks
        mock_parser.parse.return_value = Mock()
        mock_chunker.chunk_document.return_value = []  # No chunks
        mock_metadata_extractor.extract_file_metadata.return_value = {}
        mock_metadata_extractor.extract_document_metadata.return_value = {}

        result = processor.process_document(sample_markdown_file, "test-collection")

        assert result.success is False
        assert "no chunks generated" in result.error.lower()
        assert result.chunks_created == 0

    def test_process_document_parsing_error(
        self, processor, sample_markdown_file, mock_parser
    ):
        """Test handling of parsing errors."""
        mock_parser.parse.side_effect = Exception("Parsing failed")

        result = processor.process_document(sample_markdown_file, "test-collection")

        assert result.success is False
        assert "parsing failed" in result.error.lower()

    def test_process_document_encoding_error(self, processor, temp_dir):
        """Test handling of encoding errors."""
        # Create file with invalid encoding
        invalid_file = temp_dir / "invalid_encoding.md"
        invalid_file.write_bytes(b"\xff\xfe# Invalid encoding content")

        result = processor.process_document(invalid_file, "test-collection")

        # Should handle encoding gracefully
        assert result.success is False
        assert "decode" in result.error.lower() or "encoding" in result.error.lower()

    def test_read_file_multiple_encodings(self, processor, temp_dir):
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

    def test_generate_chunk_id(self, processor, sample_markdown_file):
        """Test chunk ID generation."""
        chunk_id_1 = processor._generate_chunk_id(sample_markdown_file, 0)
        chunk_id_2 = processor._generate_chunk_id(sample_markdown_file, 1)

        assert chunk_id_1 != chunk_id_2
        assert chunk_id_1.endswith("_0000")
        assert chunk_id_2.endswith("_0001")
        assert len(chunk_id_1.split("_")[0]) == 16  # Hash part

    def test_enhance_chunks(
        self, processor, sample_chunks, sample_markdown_file, mock_metadata_extractor
    ):
        """Test chunk enhancement with metadata."""
        mock_metadata_extractor.enhance_chunk_metadata.return_value = {
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
        processor,
        test_documents,
        sample_chunks,
        mock_parser,
        mock_chunker,
        mock_metadata_extractor,
    ):
        """Test successful batch processing."""
        # Setup mocks
        mock_parser.parse.return_value = Mock()
        mock_chunker.chunk_document.return_value = sample_chunks
        mock_metadata_extractor.extract_file_metadata.return_value = {
            "file_type": "markdown"
        }
        mock_metadata_extractor.extract_document_metadata.return_value = {
            "title": "Test"
        }
        mock_metadata_extractor.enhance_chunk_metadata.return_value = {"enhanced": True}

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
        processor,
        test_documents,
        mock_parser,
        mock_chunker,
        mock_metadata_extractor,
    ):
        """Test batch processing with some failures."""
        # Setup mocks - make one file fail
        call_count = 0

        def side_effect(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Second call fails
                raise Exception("Processing failed")
            return Mock()

        mock_parser.parse.side_effect = side_effect
        mock_chunker.chunk_document.return_value = []
        mock_metadata_extractor.extract_file_metadata.return_value = {}
        mock_metadata_extractor.extract_document_metadata.return_value = {}

        file_paths = list(test_documents.values())[:2]  # Only test 2 files
        result = processor.process_batch(file_paths, "test-collection", max_workers=1)

        assert result.total_files == 2
        assert (
            result.successful_files == 0
        )  # Both fail - one due to exception, one due to no chunks
        assert result.failed_files == 2
        assert result.success_rate == 0.0

    def test_batch_processing_empty_list(self, processor):
        """Test batch processing with empty file list."""
        result = processor.process_batch([], "test-collection")

        assert result.total_files == 0
        assert result.successful_files == 0
        assert result.failed_files == 0
        assert result.total_chunks == 0

    def test_concurrent_processing(
        self,
        processor,
        test_documents,
        sample_chunks,
        mock_parser,
        mock_chunker,
        mock_metadata_extractor,
    ):
        """Test concurrent processing with multiple workers."""
        # Setup mocks
        mock_parser.parse.return_value = Mock()
        mock_chunker.chunk_document.return_value = sample_chunks
        mock_metadata_extractor.extract_file_metadata.return_value = {
            "file_type": "markdown"
        }
        mock_metadata_extractor.extract_document_metadata.return_value = {
            "title": "Test"
        }
        mock_metadata_extractor.enhance_chunk_metadata.return_value = {"enhanced": True}

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
        processor,
        test_documents,
        sample_chunks,
        mock_parser,
        mock_chunker,
        mock_metadata_extractor,
        max_workers,
    ):
        """Test batch processing with different worker counts."""
        # Setup mocks
        mock_parser.parse.return_value = Mock()
        mock_chunker.chunk_document.return_value = sample_chunks
        mock_metadata_extractor.extract_file_metadata.return_value = {
            "file_type": "markdown"
        }
        mock_metadata_extractor.extract_document_metadata.return_value = {
            "title": "Test"
        }
        mock_metadata_extractor.enhance_chunk_metadata.return_value = {"enhanced": True}

        file_paths = list(test_documents.values())
        result = processor.process_batch(
            file_paths, "test-collection", max_workers=max_workers
        )

        assert result.successful_files == len(file_paths)
        assert result.total_chunks == len(file_paths) * len(sample_chunks)

    def test_processing_time_measurement(
        self,
        processor,
        sample_markdown_file,
        mock_parser,
        mock_chunker,
        mock_metadata_extractor,
    ):
        """Test that processing time is measured correctly."""

        # Add delay to processing
        def delayed_parse(*args):
            time.sleep(0.01)  # 10ms delay
            return Mock()

        mock_parser.parse.side_effect = delayed_parse
        mock_chunker.chunk_document.return_value = []
        mock_metadata_extractor.extract_file_metadata.return_value = {}
        mock_metadata_extractor.extract_document_metadata.return_value = {}

        result = processor.process_document(sample_markdown_file, "test-collection")

        assert result.processing_time >= 0.01  # Should include the delay
        assert result.processing_time < 1.0  # But not too long
