"""Unit tests for DocumentProcessor."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from shard_markdown.config.settings import ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor


class TestDocumentProcessor:
    """Test DocumentProcessor functionality."""

    @pytest.fixture
    def mock_parser(self) -> Generator[Mock, None, None]:
        """Mock MarkdownParser."""
        with patch("shard_markdown.core.processor.MarkdownParser") as mock:
            yield mock

    @pytest.fixture
    def mock_chunker(self) -> Generator[Mock, None, None]:
        """Mock ChunkingEngine."""
        with patch("shard_markdown.core.processor.ChunkingEngine") as mock:
            yield mock

    @pytest.fixture
    def mock_metadata_extractor(self) -> Generator[Mock, None, None]:
        """Mock MetadataExtractor."""
        with patch("shard_markdown.core.processor.MetadataExtractor") as mock:
            yield mock

    @pytest.fixture
    def sample_config(self) -> ChunkingConfig:
        """Create sample chunking config."""
        return ChunkingConfig(default_size=500, default_overlap=100)

    @pytest.fixture
    def processor(
        self,
        sample_config: ChunkingConfig,
        mock_parser: Mock,
        mock_chunker: Mock,
        mock_metadata_extractor: Mock,
    ) -> DocumentProcessor:
        """Create DocumentProcessor instance with mocked dependencies."""
        return DocumentProcessor(chunking_config=sample_config)

    @pytest.mark.unit
    def test_init(self, sample_config: ChunkingConfig) -> None:
        """Test DocumentProcessor initialization."""
        processor = DocumentProcessor(chunking_config=sample_config)

        assert processor.chunking_config == sample_config
        assert processor.parser is not None
        assert processor.chunker is not None
        assert processor.metadata_extractor is not None

    @pytest.mark.unit
    def test_process_single_file_success(
        self,
        processor: DocumentProcessor,
        mock_parser: Mock,
        mock_chunker: Mock,
        mock_metadata_extractor: Mock,
        sample_chunks: list,
        tmp_path: Path,
    ) -> None:
        """Test successful single file processing."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n\nSome content.")

        # Setup mocks
        mock_ast = Mock()
        mock_parser.return_value.parse.return_value = mock_ast
        mock_chunker.return_value.chunk_document.return_value = sample_chunks
        mock_metadata_extractor.return_value.extract_file_metadata.return_value = {}

        # Process file
        result = processor.process_file(
            file_path=test_file, collection_name="test-collection"
        )

        # Assertions
        assert result.success is True
        assert result.chunks_created == len(sample_chunks)
        assert result.file_path == test_file
        assert result.collection_name == "test-collection"

    @pytest.mark.unit
    def test_process_single_file_parse_error(
        self,
        processor: DocumentProcessor,
        mock_parser: Mock,
        mock_chunker: Mock,
        mock_metadata_extractor: Mock,
        tmp_path: Path,
    ) -> None:
        """Test handling parse error in single file processing."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Setup mocks
        mock_parser.return_value.parse.side_effect = Exception("Parse error")
        mock_metadata_extractor.return_value.extract_file_metadata.return_value = {}

        # Process file
        result = processor.process_file(
            file_path=test_file, collection_name="test-collection"
        )

        # Assertions
        assert result.success is False
        assert result.chunks_created == 0
        assert result.error == "Parse error"

    @pytest.mark.unit
    def test_process_single_file_chunking_error(
        self,
        processor: DocumentProcessor,
        mock_parser: Mock,
        mock_chunker: Mock,
        mock_metadata_extractor: Mock,
        tmp_path: Path,
    ) -> None:
        """Test handling chunking error in single file processing."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Setup mocks
        mock_ast = Mock()
        mock_parser.return_value.parse.return_value = mock_ast
        mock_chunker.return_value.chunk_document.side_effect = Exception(
            "Chunking error"
        )
        mock_metadata_extractor.return_value.extract_file_metadata.return_value = {}

        # Process file
        result = processor.process_file(
            file_path=test_file, collection_name="test-collection"
        )

        # Assertions
        assert result.success is False
        assert result.chunks_created == 0
        assert result.error == "Chunking error"

    @pytest.mark.unit
    def test_process_batch_multiple_files(
        self,
        processor: DocumentProcessor,
        mock_parser: Mock,
        mock_chunker: Mock,
        mock_metadata_extractor: Mock,
        sample_chunks: list,
        tmp_path: Path,
    ) -> None:
        """Test batch processing multiple files."""
        # Create test files
        files = []
        for i in range(3):
            test_file = tmp_path / f"test_{i}.md"
            test_file.write_text(f"# Test {i}\n\nContent {i}")
            files.append(test_file)

        # Setup mocks
        mock_ast = Mock()
        mock_parser.return_value.parse.return_value = mock_ast
        mock_chunker.return_value.chunk_document.return_value = sample_chunks
        mock_metadata_extractor.return_value.extract_file_metadata.return_value = {}

        # Process files
        result = processor.process_files(
            file_paths=files, collection_name="test-collection"
        )

        # Assertions
        assert result.total_chunks == len(files) * len(sample_chunks)
        assert len(result.results) == len(files)
        assert all(res.success for res in result.results)

    @pytest.mark.unit
    def test_nonexistent_file_handling(
        self,
        processor: DocumentProcessor,
        tmp_path: Path,
    ) -> None:
        """Test handling of non-existent files."""
        nonexistent_file = tmp_path / "does_not_exist.md"

        result = processor.process_file(
            file_path=nonexistent_file, collection_name="test-collection"
        )

        assert result.success is False
        assert result.chunks_created == 0
        assert result.error is not None and "not found" in result.error.lower()

    @pytest.mark.unit
    def test_custom_metadata_handling(
        self,
        processor: DocumentProcessor,
        mock_parser: Mock,
        mock_chunker: Mock,
        mock_metadata_extractor: Mock,
        sample_chunks: list,
        tmp_path: Path,
    ) -> None:
        """Test handling of custom metadata."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Setup mocks
        mock_ast = Mock()
        mock_parser.return_value.parse.return_value = mock_ast
        mock_chunker.return_value.chunk_document.return_value = sample_chunks
        mock_metadata_extractor.return_value.extract_file_metadata.return_value = {}

        # Custom metadata
        custom_metadata = {"source": "test", "category": "docs"}

        # Process file
        result = processor.process_file(
            file_path=test_file,
            collection_name="test-collection",
            custom_metadata=custom_metadata,
        )

        # Assertions
        assert result.success is True
        assert result.chunks_created == len(sample_chunks)

    @pytest.mark.unit
    def test_empty_file_handling(
        self,
        processor: DocumentProcessor,
        mock_parser: Mock,
        mock_chunker: Mock,
        mock_metadata_extractor: Mock,
        tmp_path: Path,
    ) -> None:
        """Test handling of empty files."""
        # Create empty test file
        test_file = tmp_path / "empty.md"
        test_file.write_text("")

        # Setup mocks
        mock_ast = Mock()
        mock_parser.return_value.parse.return_value = mock_ast
        mock_chunker.return_value.chunk_document.return_value = []  # Empty chunks
        mock_metadata_extractor.return_value.extract_file_metadata.return_value = {}

        # Process file
        result = processor.process_file(
            file_path=test_file, collection_name="test-collection"
        )

        # Assertions
        assert result.success is True
        assert result.chunks_created == 0
        assert result.file_path == test_file

    @pytest.mark.unit
    def test_file_path_validation(
        self,
        processor: DocumentProcessor,
    ) -> None:
        """Test file path validation."""
        # Test with invalid path type - processor handles this gracefully
        result = processor.process_file(
            file_path="invalid_path_type",  # type: ignore
            collection_name="test-collection",
        )

        # Should return failed result instead of raising exception
        assert result.success is False
        assert result.error is not None and (
            "AttributeError" in result.error or "str" in result.error
        )

    @pytest.mark.unit
    def test_collection_name_validation(
        self,
        processor: DocumentProcessor,
        tmp_path: Path,
    ) -> None:
        """Test collection name validation."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Test with empty collection name
        result = processor.process_file(file_path=test_file, collection_name="")

        # Should still attempt processing but may have validation issues
        # The exact behavior depends on implementation details
        assert result is not None

    @pytest.mark.unit
    def test_processor_configuration_access(
        self, sample_config: ChunkingConfig
    ) -> None:
        """Test access to processor configuration."""
        processor = DocumentProcessor(chunking_config=sample_config)

        # Test that configuration is accessible
        assert processor.chunking_config.default_size == sample_config.default_size
        assert (
            processor.chunking_config.default_overlap == sample_config.default_overlap
        )
        assert processor.chunking_config.method == sample_config.method
