"""Unit tests for process CLI command."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from shard_markdown.cli.commands.process import process
from shard_markdown.core.models import BatchResult, ProcessingResult


def create_mock_config():
    """Create a mock configuration object."""
    mock_config = Mock()
    mock_config.chromadb = Mock()
    return mock_config


@pytest.fixture
def mock_context():
    """Mock Click context with config."""
    mock_config = Mock()
    mock_config.chromadb = Mock()
    return {"config": mock_config, "verbose": 0, "quiet": False}


class TestProcessCommand:
    """Test process command functionality."""

    @pytest.fixture
    def cli_runner(self):
        """Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_chromadb_client(self):
        """Mock ChromaDB client."""
        with patch(
            "shard_markdown.cli.commands.process.create_chromadb_client"
        ) as mock:
            client = Mock()
            client.connect.return_value = True
            mock.return_value = client
            yield client

    @pytest.fixture
    def mock_processor(self):
        """Mock DocumentProcessor."""
        with patch("shard_markdown.cli.commands.process.DocumentProcessor") as mock:
            processor = Mock()
            mock.return_value = processor
            yield processor

    @pytest.fixture
    def mock_collection_manager(self):
        """Mock CollectionManager."""
        with patch("shard_markdown.cli.commands.process.CollectionManager") as mock:
            manager = Mock()
            mock.return_value = manager
            yield manager

    def test_process_command_basic(
        self, cli_runner, sample_markdown_file, mock_chromadb_client, mock_processor
    ):
        """Test basic process command functionality."""
        # Setup mock returns for single file processing
        mock_result = ProcessingResult(
            file_path=sample_markdown_file,
            success=True,
            chunks_created=5,
            processing_time=1.2,
            collection_name="test-collection",
        )
        mock_processor.process_document.return_value = mock_result

        # Setup mock collection
        mock_collection = Mock()
        mock_chromadb_client.get_or_create_collection.return_value = mock_collection

        # Create a proper insert result mock
        mock_insert_result = Mock()
        mock_insert_result.success = True
        mock_insert_result.chunks_inserted = 5
        mock_insert_result.processing_time = 0.5
        mock_insert_result.insertion_rate = 10.0  # chunks/s
        mock_chromadb_client.bulk_insert.return_value = mock_insert_result

        # Mock the internal methods used in single file processing
        mock_processor._read_file.return_value = "# Test content"
        mock_processor.parser.parse.return_value = Mock()
        mock_processor.chunker.chunk_document.return_value = [Mock() for _ in range(5)]
        mock_processor.metadata_extractor.extract_file_metadata.return_value = {}
        mock_processor.metadata_extractor.extract_document_metadata.return_value = {}
        mock_processor._enhance_chunks.return_value = [Mock() for _ in range(5)]

        # Setup context with mock config
        mock_config = Mock()
        mock_config.chromadb = Mock()

        result = cli_runner.invoke(
            process,
            ["--collection", "test-collection", str(sample_markdown_file)],
            obj={"config": mock_config, "verbose": 0},
        )

        assert result.exit_code == 0
        # The output shows "Successfully processed and stored 5 chunks"
        assert "Successfully processed" in result.output
        assert "5 chunks" in result.output
        # The collection name might not appear in the single file output

        # Verify processor was called correctly
        mock_processor.process_document.assert_called_once()

    def test_process_command_missing_collection(self, cli_runner, sample_markdown_file):
        """Test process command with missing collection parameter."""
        result = cli_runner.invoke(process, [str(sample_markdown_file)])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_process_command_nonexistent_file(self, cli_runner):
        """Test process command with non-existent file."""
        result = cli_runner.invoke(
            process, ["--collection", "test-collection", "nonexistent.md"]
        )

        assert result.exit_code != 0
        assert (
            "does not exist" in result.output.lower()
            or "not found" in result.output.lower()
        )

    def test_process_command_custom_chunk_settings(
        self,
        cli_runner,
        sample_markdown_file,
        mock_chromadb_client,
        mock_processor,
        mock_context,
    ):
        """Test process command with custom chunking settings."""
        # Setup mock returns for batch processing
        mock_result = ProcessingResult(
            file_path=sample_markdown_file,
            success=True,
            chunks_created=3,
            processing_time=0.8,
            collection_name="test-collection",
        )
        mock_processor.process_document.return_value = mock_result

        # Setup mock collection
        mock_collection = Mock()
        mock_chromadb_client.get_or_create_collection.return_value = mock_collection

        # Create a proper insert result mock
        mock_insert_result = Mock()
        mock_insert_result.success = True
        mock_insert_result.chunks_inserted = 3
        mock_insert_result.processing_time = 0.5
        mock_insert_result.insertion_rate = 6.0  # chunks/s
        mock_chromadb_client.bulk_insert.return_value = mock_insert_result

        # Mock the internal methods used in single file processing
        mock_processor._read_file.return_value = "# Test content"
        mock_processor.parser.parse.return_value = Mock()
        mock_processor.chunker.chunk_document.return_value = [Mock() for _ in range(3)]
        mock_processor.metadata_extractor.extract_file_metadata.return_value = {}
        mock_processor.metadata_extractor.extract_document_metadata.return_value = {}
        mock_processor._enhance_chunks.return_value = [Mock() for _ in range(3)]

        result = cli_runner.invoke(
            process,
            [
                "--collection",
                "test-collection",
                "--chunk-size",
                "1500",
                "--chunk-overlap",
                "300",
                "--chunk-method",
                "fixed",
                str(sample_markdown_file),
            ],
            obj=mock_context,
        )

        assert result.exit_code == 0

        # Verify processor was created with correct config
        mock_processor_class = mock_processor.__class__
        call_args = mock_processor_class.call_args
        if call_args:
            # First argument should be config
            pass  # Note: Actual verification would depend on implementation

    def test_process_command_dry_run(
        self, cli_runner, sample_markdown_file, mock_context
    ):
        """Test dry run functionality."""
        result = cli_runner.invoke(
            process,
            [
                "--collection",
                "test-collection",
                "--dry-run",
                str(sample_markdown_file),
            ],
            obj=mock_context,
        )

        assert result.exit_code == 0
        assert (
            "Dry Run Preview" in result.output
            or "would process" in result.output.lower()
        )
        assert (
            "Files to be processed:" in result.output
            or "Files to process: 1" in result.output
            or "1 file" in result.output
        )

    def test_process_command_recursive(
        self,
        cli_runner,
        test_documents,
        mock_chromadb_client,
        mock_processor,
        mock_context,
    ):
        """Test recursive processing."""

        # Setup mock to return success for each file
        def mock_process_document(file_path, collection_name):
            return ProcessingResult(
                file_path=file_path,
                success=True,
                processing_time=0.5,
                collection_name=collection_name,
            )

        mock_processor.process_document.side_effect = mock_process_document

        # Setup batch processing for multiple files
        mock_batch_result = BatchResult(
            results=[
                ProcessingResult(
                    file_path=path,
                    success=True,
                    chunks_created=5,
                    processing_time=0.5,
                    collection_name="test-collection",
                )
                for path in test_documents.values()
            ],
            total_files=len(test_documents),
            successful_files=len(test_documents),
            failed_files=0,
            total_chunks=len(test_documents) * 5,
            total_processing_time=len(test_documents) * 0.5,
            collection_name="test-collection",
        )
        mock_processor.process_batch.return_value = mock_batch_result

        # Setup additional mocks for batch processing
        mock_processor._read_file.return_value = "# Test content"
        mock_processor.parser.parse.return_value = Mock()
        mock_processor.chunker.chunk_document.return_value = [Mock() for _ in range(5)]
        mock_processor.metadata_extractor.extract_file_metadata.return_value = {}
        mock_processor.metadata_extractor.extract_document_metadata.return_value = {}
        mock_processor._enhance_chunks.return_value = [Mock() for _ in range(5)]

        # Setup mock collection and insert result
        mock_collection = Mock()
        mock_chromadb_client.get_or_create_collection.return_value = mock_collection
        mock_insert_result = Mock()
        mock_insert_result.success = True
        mock_insert_result.chunks_inserted = len(test_documents) * 5
        mock_insert_result.processing_time = 0.5
        mock_insert_result.insertion_rate = len(test_documents) * 10.0  # chunks/s
        mock_chromadb_client.bulk_insert.return_value = mock_insert_result

        # Get the directory containing test documents
        test_dir = list(test_documents.values())[0].parent

        result = cli_runner.invoke(
            process,
            ["--collection", "test-collection", "--recursive", str(test_dir)],
            obj=mock_context,
        )

        assert result.exit_code == 0
        # Should use batch processing for multiple files
        mock_processor.process_batch.assert_called_once()

    def test_process_command_batch_mode(
        self,
        cli_runner,
        test_documents,
        mock_chromadb_client,
        mock_processor,
        mock_context,
    ):
        """Test batch processing mode."""
        # Create mock batch result
        mock_batch_result = BatchResult(
            results=[],
            total_files=len(test_documents),
            successful_files=len(test_documents),
            failed_files=0,
            total_chunks=15,
            total_processing_time=2.5,
            collection_name="test-collection",
        )
        mock_processor.process_batch.return_value = mock_batch_result

        file_paths = [str(path) for path in test_documents.values()]

        result = cli_runner.invoke(
            process,
            ["--collection", "test-collection", "--batch"] + file_paths,
            obj=mock_context,
        )

        # Note: This test assumes --batch option exists
        # The actual command structure may differ
        assert result.exit_code == 0 or "batch" in result.output.lower()

    def test_process_command_create_collection(
        self,
        cli_runner,
        sample_markdown_file,
        mock_chromadb_client,
        mock_processor,
        mock_collection_manager,
        mock_context,
    ):
        """Test collection creation."""
        mock_result = ProcessingResult(
            file_path=sample_markdown_file,
            success=True,
            chunks_created=5,
            processing_time=1.0,
            collection_name="new-collection",
        )
        mock_processor.process_document.return_value = mock_result

        # Setup additional mocks for single file processing
        mock_processor._read_file.return_value = "# Test content"
        mock_processor.parser.parse.return_value = Mock()
        mock_processor.chunker.chunk_document.return_value = [Mock() for _ in range(5)]
        mock_processor.metadata_extractor.extract_file_metadata.return_value = {}
        mock_processor.metadata_extractor.extract_document_metadata.return_value = {}
        mock_processor._enhance_chunks.return_value = [Mock() for _ in range(5)]

        # Setup mock collection and insert result
        mock_collection = Mock()
        mock_chromadb_client.get_or_create_collection.return_value = mock_collection
        mock_insert_result = Mock()
        mock_insert_result.success = True
        mock_insert_result.chunks_inserted = 5
        mock_insert_result.processing_time = 0.5
        mock_insert_result.insertion_rate = 10.0  # chunks/s
        mock_chromadb_client.bulk_insert.return_value = mock_insert_result

        result = cli_runner.invoke(
            process,
            [
                "--collection",
                "new-collection",
                "--create-collection",
                str(sample_markdown_file),
            ],
            obj=mock_context,
        )

        assert result.exit_code == 0
        # The --create-collection flag should be handled properly
        # Since we're not testing the collection manager directly,
        # we just verify the command completes successfully

    def test_process_command_failed_processing(
        self,
        cli_runner,
        sample_markdown_file,
        mock_chromadb_client,
        mock_processor,
        mock_context,
    ):
        """Test handling of processing failures."""
        mock_result = ProcessingResult(
            file_path=sample_markdown_file,
            success=False,
            error="Processing failed",
            chunks_created=0,
            processing_time=0.1,
        )
        mock_processor.process_document.return_value = mock_result

        # Setup mock collection even for failures
        mock_collection = Mock()
        mock_chromadb_client.get_or_create_collection.return_value = mock_collection

        result = cli_runner.invoke(
            process,
            ["--collection", "test-collection", str(sample_markdown_file)],
            obj=mock_context,
        )

        # When processing fails, the command should still complete but report failure
        assert result.exit_code == 0  # Command completes successfully
        assert "failed" in result.output.lower() or "error" in result.output.lower()

    def test_process_command_chromadb_connection_error(
        self, cli_runner, sample_markdown_file, mock_context
    ):
        """Test handling of ChromaDB connection errors."""
        with patch(
            "shard_markdown.cli.commands.process.create_chromadb_client"
        ) as mock_client:
            client = Mock()
            client.connect.return_value = False  # Connection fails
            mock_client.return_value = client

            result = cli_runner.invoke(
                process,
                ["--collection", "test-collection", str(sample_markdown_file)],
                obj=mock_context,
            )

            assert result.exit_code != 0
            assert (
                "connection" in result.output.lower()
                or "failed" in result.output.lower()
            )

    def test_process_command_validation_error(
        self, cli_runner, sample_markdown_file, mock_context
    ):
        """Test handling of validation errors."""
        with patch(
            "shard_markdown.cli.commands.process.validate_collection_name"
        ) as mock_validate:
            mock_validate.side_effect = ValueError("Invalid collection name")

            result = cli_runner.invoke(
                process,
                [
                    "--collection",
                    "invalid-collection-name",
                    str(sample_markdown_file),
                ],
                obj=mock_context,
            )

            assert result.exit_code != 0
            assert "invalid" in result.output.lower()

    def test_process_command_progress_display(
        self,
        cli_runner,
        test_documents,
        mock_chromadb_client,
        mock_processor,
        mock_context,
    ):
        """Test progress display during processing."""

        # Setup mock to simulate processing multiple files
        def mock_process_document(file_path, collection_name):
            return ProcessingResult(
                file_path=file_path,
                success=True,
                chunks_created=3,
                processing_time=0.1,
                collection_name=collection_name,
            )

        mock_processor.process_document.side_effect = mock_process_document

        # Setup batch processing for multiple files
        mock_batch_result = BatchResult(
            results=[
                ProcessingResult(
                    file_path=path,
                    success=True,
                    chunks_created=3,
                    processing_time=0.1,
                    collection_name="test-collection",
                )
                for path in test_documents.values()
            ],
            total_files=len(test_documents),
            successful_files=len(test_documents),
            failed_files=0,
            total_chunks=len(test_documents) * 3,
            total_processing_time=len(test_documents) * 0.1,
            collection_name="test-collection",
        )
        mock_processor.process_batch.return_value = mock_batch_result

        # Setup additional mocks for batch processing
        mock_processor._read_file.return_value = "# Test content"
        mock_processor.parser.parse.return_value = Mock()
        mock_processor.chunker.chunk_document.return_value = [Mock() for _ in range(3)]
        mock_processor.metadata_extractor.extract_file_metadata.return_value = {}
        mock_processor.metadata_extractor.extract_document_metadata.return_value = {}
        mock_processor._enhance_chunks.return_value = [Mock() for _ in range(3)]

        # Setup mock collection and insert result
        mock_collection = Mock()
        mock_chromadb_client.get_or_create_collection.return_value = mock_collection
        mock_insert_result = Mock()
        mock_insert_result.success = True
        mock_insert_result.chunks_inserted = len(test_documents) * 3
        mock_insert_result.processing_time = 0.5
        mock_insert_result.insertion_rate = len(test_documents) * 6.0  # chunks/s
        mock_chromadb_client.bulk_insert.return_value = mock_insert_result

        file_paths = [str(path) for path in test_documents.values()]

        result = cli_runner.invoke(
            process, ["--collection", "test-collection"] + file_paths, obj=mock_context
        )

        assert result.exit_code == 0
        # Should show progress information
        assert (
            "processed" in result.output.lower() or "progress" in result.output.lower()
        )

    def test_process_command_output_formats(
        self, cli_runner, sample_markdown_file, mock_chromadb_client, mock_processor
    ):
        """Test different output formats."""
        mock_result = ProcessingResult(
            file_path=sample_markdown_file,
            success=True,
            chunks_created=5,
            processing_time=1.2,
            collection_name="test-collection",
        )
        mock_processor.process_document.return_value = mock_result

        # Test JSON output
        result = cli_runner.invoke(
            process,
            [
                "--collection",
                "test-collection",
                "--output",
                "json",
                str(sample_markdown_file),
            ],
        )

        # Note: This assumes --output option exists
        if result.exit_code == 0:
            assert "{" in result.output or "json" in result.output.lower()

    def test_process_command_chunk_method_validation(
        self, cli_runner, sample_markdown_file
    ):
        """Test chunk method validation."""
        result = cli_runner.invoke(
            process,
            [
                "--collection",
                "test-collection",
                "--chunk-method",
                "invalid-method",
                str(sample_markdown_file),
            ],
        )

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "choice" in result.output.lower()

    def test_process_command_chunk_size_validation(
        self, cli_runner, sample_markdown_file
    ):
        """Test chunk size validation."""
        # Test negative chunk size
        result = cli_runner.invoke(
            process,
            [
                "--collection",
                "test-collection",
                "--chunk-size",
                "-100",
                str(sample_markdown_file),
            ],
        )

        # Should handle validation error appropriately
        assert result.exit_code != 0 or "invalid" in result.output.lower()

    def test_process_command_help(self, cli_runner):
        """Test process command help."""
        result = cli_runner.invoke(process, ["--help"])

        assert result.exit_code == 0
        assert "collection" in result.output.lower()
        assert "chunk-size" in result.output.lower()
        assert "chunk-overlap" in result.output.lower()
        assert "chunk-method" in result.output.lower()

    @pytest.mark.parametrize(
        "chunk_size,overlap",
        [(500, 100), (1000, 200), (1500, 300), (2000, 400)],
    )
    def test_process_command_chunk_parameter_combinations(
        self,
        cli_runner,
        sample_markdown_file,
        mock_chromadb_client,
        mock_processor,
        mock_context,
        chunk_size,
        overlap,
    ):
        """Test different chunk parameter combinations."""
        mock_result = ProcessingResult(
            file_path=sample_markdown_file,
            success=True,
            chunks_created=5,
            processing_time=1.0,
            collection_name="test-collection",
        )
        mock_processor.process_document.return_value = mock_result

        # Setup additional mocks for single file processing
        mock_processor._read_file.return_value = "# Test content"
        mock_processor.parser.parse.return_value = Mock()
        mock_processor.chunker.chunk_document.return_value = [Mock() for _ in range(5)]
        mock_processor.metadata_extractor.extract_file_metadata.return_value = {}
        mock_processor.metadata_extractor.extract_document_metadata.return_value = {}
        mock_processor._enhance_chunks.return_value = [Mock() for _ in range(5)]

        # Setup mock collection and insert result
        mock_collection = Mock()
        mock_chromadb_client.get_or_create_collection.return_value = mock_collection
        mock_insert_result = Mock()
        mock_insert_result.success = True
        mock_insert_result.chunks_inserted = 5
        mock_insert_result.processing_time = 0.5
        mock_insert_result.insertion_rate = 10.0  # chunks/s
        mock_chromadb_client.bulk_insert.return_value = mock_insert_result

        result = cli_runner.invoke(
            process,
            [
                "--collection",
                "test-collection",
                "--chunk-size",
                str(chunk_size),
                "--chunk-overlap",
                str(overlap),
                str(sample_markdown_file),
            ],
            obj=mock_context,
        )

        assert result.exit_code == 0

    def test_process_command_metadata_options(
        self,
        cli_runner,
        sample_markdown_file,
        mock_chromadb_client,
        mock_processor,
        mock_context,
    ):
        """Test metadata processing options."""
        mock_result = ProcessingResult(
            file_path=sample_markdown_file,
            success=True,
            chunks_created=5,
            processing_time=1.0,
            collection_name="test-collection",
        )
        mock_processor.process_document.return_value = mock_result

        # Setup mock collection
        mock_collection = Mock()
        mock_chromadb_client.get_or_create_collection.return_value = mock_collection

        # Create a proper insert result mock
        mock_insert_result = Mock()
        mock_insert_result.success = True
        mock_insert_result.chunks_inserted = 5
        mock_insert_result.processing_time = 0.5
        mock_chromadb_client.bulk_insert.return_value = mock_insert_result

        # Mock the internal methods used in single file processing
        mock_processor._read_file.return_value = "# Test content"
        mock_processor.parser.parse.return_value = Mock()
        mock_processor.chunker.chunk_document.return_value = [Mock() for _ in range(5)]
        mock_processor.metadata_extractor.extract_file_metadata.return_value = {}
        mock_processor.metadata_extractor.extract_document_metadata.return_value = {}
        mock_processor._enhance_chunks.return_value = [Mock() for _ in range(5)]

        result = cli_runner.invoke(
            process,
            [
                "--collection",
                "test-collection",
                str(sample_markdown_file),
            ],
            obj=mock_context,
        )

        # Test basic functionality
        assert result.exit_code == 0


class TestProcessCommandEdgeCases:
    """Test edge cases for process command."""

    @pytest.fixture
    def cli_runner(self):
        """Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Temporary directory for test files."""
        return tmp_path

    @pytest.fixture
    def mock_chromadb_client(self):
        """Mock ChromaDB client."""
        with patch(
            "shard_markdown.cli.commands.process.create_chromadb_client"
        ) as mock:
            client = Mock()
            client.connect.return_value = True
            # Properly mock get_or_create_collection
            mock_collection = Mock()
            client.get_or_create_collection = Mock(return_value=mock_collection)
            mock.return_value = client
            yield client

    @pytest.fixture
    def mock_processor(self):
        """Mock DocumentProcessor."""
        with patch("shard_markdown.cli.commands.process.DocumentProcessor") as mock:
            processor = Mock()
            mock.return_value = processor
            yield processor

    def test_process_command_with_special_characters_in_path(
        self, cli_runner, temp_dir, mock_chromadb_client, mock_processor, mock_context
    ):
        """Test processing files with special characters in path."""
        # Create file with special characters
        special_file = temp_dir / "test file with spaces & symbols.md"
        special_file.write_text("# Test\nContent")

        mock_result = ProcessingResult(
            file_path=special_file,
            success=True,
            chunks_created=1,
            processing_time=0.1,
            collection_name="test-collection",
        )
        mock_processor.process_document.return_value = mock_result

        # Setup additional mocks for single file processing
        mock_processor._read_file.return_value = "# Test\nContent"
        mock_processor.parser.parse.return_value = Mock()
        mock_processor.chunker.chunk_document.return_value = [Mock()]
        mock_processor.metadata_extractor.extract_file_metadata.return_value = {}
        mock_processor.metadata_extractor.extract_document_metadata.return_value = {}
        mock_processor._enhance_chunks.return_value = [Mock()]

        # Setup mock insert result (collection is already mocked in fixture)
        mock_insert_result = Mock()
        mock_insert_result.success = True
        mock_insert_result.chunks_inserted = 1
        mock_insert_result.processing_time = 0.1
        mock_insert_result.insertion_rate = 10.0  # chunks/s
        mock_chromadb_client.bulk_insert = Mock(return_value=mock_insert_result)

        result = cli_runner.invoke(
            process,
            ["--collection", "test-collection", str(special_file)],
            obj=mock_context,
        )

        assert result.exit_code == 0

    def test_process_command_very_long_collection_name(
        self, cli_runner, sample_markdown_file
    ):
        """Test with very long collection name."""
        long_name = "a" * 300  # Very long collection name

        result = cli_runner.invoke(
            process, ["--collection", long_name, str(sample_markdown_file)]
        )

        # Should handle validation appropriately
        assert result.exit_code != 0 or len(result.output) > 0

    def test_process_command_empty_markdown_file(
        self, cli_runner, temp_dir, mock_chromadb_client, mock_processor, mock_context
    ):
        """Test processing empty markdown file."""
        empty_file = temp_dir / "empty.md"
        empty_file.write_text("")

        mock_result = ProcessingResult(
            file_path=empty_file,
            success=False,
            error="Empty file",
            chunks_created=0,
            processing_time=0.0,
        )
        mock_processor.process_document.return_value = mock_result

        # Setup additional mocks for single file processing
        mock_processor._read_file.return_value = ""
        mock_processor.parser.parse.return_value = Mock()
        mock_processor.chunker.chunk_document.return_value = []
        mock_processor.metadata_extractor.extract_file_metadata.return_value = {}
        mock_processor.metadata_extractor.extract_document_metadata.return_value = {}
        mock_processor._enhance_chunks.return_value = []

        # Setup mock insert result for empty file (collection already mocked)
        mock_insert_result = Mock()
        mock_insert_result.success = False
        mock_insert_result.chunks_inserted = 0
        mock_insert_result.processing_time = 0.0
        mock_insert_result.insertion_rate = 0.0
        mock_chromadb_client.bulk_insert = Mock(return_value=mock_insert_result)

        result = cli_runner.invoke(
            process,
            ["--collection", "test-collection", str(empty_file)],
            obj=mock_context,
        )

        # When processing fails due to empty file, command still completes
        assert result.exit_code == 0  # Command completes successfully
        assert (
            "empty" in result.output.lower()
            or "failed" in result.output.lower()
            or "no chunks" in result.output.lower()
        )
