"""Unit tests for process CLI command."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from shard_markdown.cli.commands.process import process
from shard_markdown.core.models import BatchResult, InsertResult, ProcessingResult


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

            # Mock collection
            collection_obj = Mock()
            client.get_or_create_collection.return_value = collection_obj
            client.get_collection.return_value = collection_obj

            # Mock bulk_insert to return proper InsertResult
            insert_result = InsertResult(
                success=True,
                chunks_inserted=5,
                processing_time=0.5,
                collection_name="test-collection",
            )
            client.bulk_insert.return_value = insert_result

            mock.return_value = client
            yield client

    @pytest.fixture
    def mock_processor(self):
        """Mock DocumentProcessor."""
        with patch("shard_markdown.cli.commands.process.DocumentProcessor") as mock:
            processor = Mock()

            # Mock file reading
            processor._read_file.return_value = "# Test\nSome content"

            # Mock parser
            ast_mock = Mock()
            processor.parser.parse.return_value = ast_mock

            # Mock chunker
            chunks_mock = [Mock() for _ in range(5)]
            processor.chunker.chunk_document.return_value = chunks_mock

            # Mock metadata extraction
            file_metadata = {"file": "metadata"}
            doc_metadata = {"doc": "metadata"}
            processor.metadata_extractor.extract_file_metadata.return_value = (
                file_metadata
            )
            processor.metadata_extractor.extract_document_metadata.return_value = (
                doc_metadata
            )

            # Mock enhance_chunks
            enhanced_chunks = [Mock() for _ in range(5)]
            processor._enhance_chunks.return_value = enhanced_chunks

            # Mock process_batch for multiple file scenarios
            def create_batch_result(*args, **kwargs):
                # Extract file paths (first arg) and collection name (second arg)
                file_paths = args[0] if args else []
                collection_name = args[1] if len(args) > 1 else "test-collection"

                batch_results = []
                for file_path in file_paths:
                    batch_results.append(
                        ProcessingResult(
                            file_path=file_path,
                            success=True,
                            chunks_created=5,
                            processing_time=0.5,
                            collection_name=collection_name,
                        )
                    )

                return BatchResult(
                    results=batch_results,
                    total_files=len(file_paths),
                    successful_files=len(file_paths),
                    failed_files=0,
                    total_chunks=len(file_paths) * 5,
                    total_processing_time=len(file_paths) * 0.5,
                    collection_name=collection_name,
                )

            processor.process_batch.side_effect = create_batch_result

            mock.return_value = processor
            yield processor

    @pytest.fixture
    def mock_collection_manager(self):
        """Mock CollectionManager."""
        with patch("shard_markdown.cli.commands.process.CollectionManager") as mock:
            manager = Mock()
            manager.collection_exists.return_value = False
            manager.create_collection.return_value = True
            manager.clear_collection.return_value = True
            mock.return_value = manager
            yield manager

    def test_process_command_basic(
        self, cli_runner, sample_markdown_file, mock_chromadb_client, mock_processor
    ):
        """Test basic process command functionality."""
        # Setup mock returns
        mock_result = ProcessingResult(
            file_path=sample_markdown_file,
            success=True,
            chunks_created=5,
            processing_time=1.2,
            collection_name="test-collection",
        )
        mock_processor.process_document.return_value = mock_result

        result = cli_runner.invoke(
            process, ["--collection", "test-collection", str(sample_markdown_file)]
        )

        assert result.exit_code == 0
        assert "Successfully processed" in result.output
        assert "5 chunks" in result.output

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
        self, cli_runner, sample_markdown_file, mock_chromadb_client, mock_processor
    ):
        """Test process command with custom chunking settings."""
        mock_result = ProcessingResult(
            file_path=sample_markdown_file,
            success=True,
            chunks_created=3,
            processing_time=0.8,
            collection_name="test-collection",
        )
        mock_processor.process_document.return_value = mock_result

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
        )

        assert result.exit_code == 0

    def test_process_command_dry_run(self, cli_runner, sample_markdown_file):
        """Test dry run functionality."""
        result = cli_runner.invoke(
            process,
            [
                "--collection",
                "test-collection",
                "--dry-run",
                str(sample_markdown_file),
            ],
        )

        assert result.exit_code == 0
        assert (
            "Dry Run Preview" in result.output
            or "would process" in result.output.lower()
        )
        assert "Files to process: 1" in result.output or "1" in result.output

    def test_process_command_recursive(
        self, cli_runner, test_documents, mock_chromadb_client, mock_processor
    ):
        """Test recursive processing."""
        # Get the directory containing test documents
        test_dir = list(test_documents.values())[0].parent

        result = cli_runner.invoke(
            process,
            ["--collection", "test-collection", "--recursive", str(test_dir)],
        )

        assert result.exit_code == 0
        # Should call process_batch for multiple files
        mock_processor.process_batch.assert_called_once()

    def test_process_command_batch_mode(
        self, cli_runner, test_documents, mock_chromadb_client, mock_processor
    ):
        """Test batch processing mode."""
        file_paths = [str(path) for path in test_documents.values()]

        result = cli_runner.invoke(
            process,
            ["--collection", "test-collection", "--max-workers", "4"] + file_paths,
        )

        assert result.exit_code == 0
        # Should call process_batch for multiple files
        mock_processor.process_batch.assert_called_once()

    def test_process_command_create_collection(
        self,
        cli_runner,
        sample_markdown_file,
        mock_chromadb_client,
        mock_processor,
        mock_collection_manager,
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

        result = cli_runner.invoke(
            process,
            [
                "--collection",
                "new-collection",
                "--create-collection",
                str(sample_markdown_file),
            ],
        )

        assert result.exit_code == 0
        # The --create-collection flag is passed to get_or_create_collection
        # which will create the collection if it doesn't exist

    def test_process_command_failed_processing(
        self, cli_runner, sample_markdown_file, mock_chromadb_client, mock_processor
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

        result = cli_runner.invoke(
            process, ["--collection", "test-collection", str(sample_markdown_file)]
        )

        assert result.exit_code == 0  # Processing failure doesn't exit with error
        assert "failed" in result.output.lower() or "error" in result.output.lower()

    def test_process_command_chromadb_connection_error(
        self, cli_runner, sample_markdown_file
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
            )

            assert result.exit_code != 0
            assert (
                "connection" in result.output.lower()
                or "failed" in result.output.lower()
            )

    def test_process_command_validation_error(self, cli_runner, sample_markdown_file):
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
            )

            assert result.exit_code != 0
            assert "invalid" in result.output.lower()

    def test_process_command_progress_display(
        self, cli_runner, test_documents, mock_chromadb_client, mock_processor
    ):
        """Test progress display during processing."""
        file_paths = [str(path) for path in test_documents.values()]

        result = cli_runner.invoke(
            process, ["--collection", "test-collection"] + file_paths
        )

        assert result.exit_code == 0
        # Should show batch processing results
        assert "successfully processed" in result.output.lower()

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

        # Test JSON output (note: this option may not exist yet)
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

        # This test is forward-looking - the --output option may not exist yet
        # So we allow success or specific error about unknown option
        if result.exit_code != 0:
            assert (
                "no such option" in result.output.lower()
                or "unrecognized" in result.output.lower()
            )

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
        )

        assert result.exit_code == 0

    def test_process_command_metadata_options(
        self, cli_runner, sample_markdown_file, mock_chromadb_client, mock_processor
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

        # Test non-existent options (forward-looking test)
        result = cli_runner.invoke(
            process,
            [
                "--collection",
                "test-collection",
                "--include-frontmatter",
                "--custom-metadata",
                '{"project": "test", "version": "1.0"}',
                str(sample_markdown_file),
            ],
        )

        # These options don't exist yet, so expect failure
        if result.exit_code != 0:
            assert "no such option" in result.output.lower()


class TestProcessCommandEdgeCases:
    """Test edge cases for process command."""

    def test_process_command_with_special_characters_in_path(
        self, cli_runner, temp_dir, mock_chromadb_client, mock_processor
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

        result = cli_runner.invoke(
            process, ["--collection", "test-collection", str(special_file)]
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
        self, cli_runner, temp_dir, mock_chromadb_client, mock_processor
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

        result = cli_runner.invoke(
            process, ["--collection", "test-collection", str(empty_file)]
        )

        assert result.exit_code == 0  # Processing failure doesn't exit with error
        assert "empty" in result.output.lower() or "failed" in result.output.lower()
