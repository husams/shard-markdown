"""Unit tests for process command."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from shard_markdown.cli.commands.process import process


class TestProcessCommand:
    """Test process command functionality."""

    @pytest.fixture
    def cli_runner(self):
        """Create Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def sample_markdown_file(self):
        """Create a temporary markdown file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Document\n\nThis is a test.\n")
            return Path(f.name)

    @pytest.fixture
    def test_documents(self):
        """Create multiple test documents."""
        files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
                f.write(f"# Document {i}\n\nContent for document {i}\n")
                files.append(Path(f.name))
        return files

    @pytest.fixture
    def mock_context(self):
        """Mock Click context."""
        config = Mock()
        config.chunking = Mock()
        config.chunking.default_size = 1000
        config.chunking.default_overlap = 200
        config.chunking.method = "structure"
        config.chromadb = Mock()
        config.chromadb.host = "localhost"
        config.chromadb.port = 8000
        # Fix logging config with proper types
        config.logging = Mock()
        config.logging.level = "INFO"
        config.logging.file_path = None
        config.logging.max_file_size = 10485760  # Actual integer
        config.logging.backup_count = 5

        return {
            "config": config,
            "quiet": False,
            "verbose": 0,
        }

    @pytest.fixture
    def mock_chromadb_client(self):
        """Mock ChromaDB client."""
        client = Mock()
        client.create_collection.return_value = Mock()
        client.get_collection.return_value = Mock()
        return client

    def test_process_command_basic(
        self, cli_runner, sample_markdown_file, mock_context
    ):
        """Test basic process command functionality."""
        with patch(
            "shard_markdown.cli.commands.process.load_app_config"
        ) as mock_config:
            mock_config.return_value = mock_context["config"]

            result = cli_runner.invoke(
                process,
                ["--collection", "test-collection", str(sample_markdown_file)],
                obj=mock_context,
            )

            # Should complete successfully (even without ChromaDB insertion)
            assert result.exit_code == 0
            assert "Processing 1 files" in result.output

    def test_process_command_custom_chunk_settings(
        self, cli_runner, sample_markdown_file, mock_context
    ):
        """Test process command with custom chunk settings."""
        with patch(
            "shard_markdown.cli.commands.process.load_app_config"
        ) as mock_config:
            mock_config.return_value = mock_context["config"]

            result = cli_runner.invoke(
                process,
                [
                    "--collection",
                    "test-collection",
                    "--chunk-size",
                    "500",
                    "--chunk-overlap",
                    "100",
                    str(sample_markdown_file),
                ],
                obj=mock_context,
            )

            assert result.exit_code == 0
            assert "Chunk size: 500" in result.output
            assert "Chunk overlap: 100" in result.output

    def test_process_command_recursive(self, cli_runner, mock_context):
        """Test process command with recursive option."""
        # Create temp directory with markdown files
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)

            # Create files in subdirectory
            subdir = test_dir / "subdir"
            subdir.mkdir()

            file1 = test_dir / "test1.md"
            file1.write_text("# Test 1\n\nContent 1")

            file2 = subdir / "test2.md"
            file2.write_text("# Test 2\n\nContent 2")

            with patch(
                "shard_markdown.cli.commands.process.load_app_config"
            ) as mock_config:
                mock_config.return_value = mock_context["config"]

                result = cli_runner.invoke(
                    process,
                    ["--collection", "test-collection", "--recursive", str(test_dir)],
                    obj=mock_context,
                )

                assert result.exit_code == 0
                assert "Processing 2 files" in result.output

    def test_process_command_batch_mode(self, cli_runner, test_documents, mock_context):
        """Test processing multiple files."""
        with patch(
            "shard_markdown.cli.commands.process.load_app_config"
        ) as mock_config:
            mock_config.return_value = mock_context["config"]

            result = cli_runner.invoke(
                process,
                ["--collection", "test-collection"] + [str(f) for f in test_documents],
                obj=mock_context,
            )

            assert result.exit_code == 0
            assert "Processing 3 files" in result.output

    def test_process_command_create_collection(
        self, cli_runner, sample_markdown_file, mock_context
    ):
        """Test process command with collection creation flag."""
        with patch(
            "shard_markdown.cli.commands.process.load_app_config"
        ) as mock_config:
            mock_config.return_value = mock_context["config"]

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
        mock_context,
    ):
        """Test that progress is displayed during processing."""
        with patch(
            "shard_markdown.cli.commands.process.load_app_config"
        ) as mock_config:
            mock_config.return_value = mock_context["config"]

            result = cli_runner.invoke(
                process,
                ["--collection", "test-collection"] + [str(f) for f in test_documents],
                obj=mock_context,
            )

            assert result.exit_code == 0
            assert "Processing 3 files" in result.output

    def test_process_command_output_formats(
        self, cli_runner, sample_markdown_file, mock_context
    ):
        """Test different output scenarios."""
        with patch(
            "shard_markdown.cli.commands.process.load_app_config"
        ) as mock_config:
            mock_config.return_value = mock_context["config"]

            # Test verbose output
            result = cli_runner.invoke(
                process,
                [
                    "--collection",
                    "test-collection",
                    "--verbose",
                    str(sample_markdown_file),
                ],
                obj=mock_context,
            )

            assert result.exit_code == 0

    @pytest.mark.parametrize(
        "chunk_size,chunk_overlap",
        [
            (500, 100),
            (1000, 200),
            (1500, 300),
            (2000, 400),
        ],
    )
    def test_process_command_chunk_parameter_combinations(
        self, cli_runner, sample_markdown_file, mock_context, chunk_size, chunk_overlap
    ):
        """Test various chunk size and overlap combinations."""
        with patch(
            "shard_markdown.cli.commands.process.load_app_config"
        ) as mock_config:
            mock_config.return_value = mock_context["config"]

            result = cli_runner.invoke(
                process,
                [
                    "--collection",
                    "test-collection",
                    "--chunk-size",
                    str(chunk_size),
                    "--chunk-overlap",
                    str(chunk_overlap),
                    str(sample_markdown_file),
                ],
                obj=mock_context,
            )

            assert result.exit_code == 0
            assert f"Chunk size: {chunk_size}" in result.output
            assert f"Chunk overlap: {chunk_overlap}" in result.output

    def test_process_command_metadata_options(
        self, cli_runner, sample_markdown_file, mock_context
    ):
        """Test adding custom metadata."""
        with patch(
            "shard_markdown.cli.commands.process.load_app_config"
        ) as mock_config:
            mock_config.return_value = mock_context["config"]

            result = cli_runner.invoke(
                process,
                [
                    "--collection",
                    "test-collection",
                    "--metadata",
                    "source=test",
                    "--metadata",
                    "category=docs",
                    str(sample_markdown_file),
                ],
                obj=mock_context,
            )

            assert result.exit_code == 0
            assert "Custom metadata" in result.output

    def test_process_command_dry_run(
        self, cli_runner, sample_markdown_file, mock_context
    ):
        """Test dry run mode."""
        with patch(
            "shard_markdown.cli.commands.process.load_app_config"
        ) as mock_config:
            mock_config.return_value = mock_context["config"]

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
            # Should show what would be processed without actually processing
            assert (
                "DRY RUN" in result.output or "would process" in result.output.lower()
            )

    def test_process_command_no_files_found_directory_without_recursive(
        self, cli_runner, mock_context
    ):
        """Test behavior when directory is provided without --recursive flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir)

            with patch(
                "shard_markdown.cli.commands.process.load_app_config"
            ) as mock_config:
                mock_config.return_value = mock_context["config"]

                result = cli_runner.invoke(
                    process,
                    ["--collection", "test-collection", str(empty_dir)],
                    obj=mock_context,
                )

                # Expect error code 1004 for directory without recursive flag
                assert result.exit_code == 1004
                assert "recursive flag not set" in result.output

    def test_process_command_empty_directory_with_recursive(
        self, cli_runner, mock_context
    ):
        """Test behavior when empty directory is provided with --recursive flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir)

            with patch(
                "shard_markdown.cli.commands.process.load_app_config"
            ) as mock_config:
                mock_config.return_value = mock_context["config"]

                result = cli_runner.invoke(
                    process,
                    ["--collection", "test-collection", "--recursive", str(empty_dir)],
                    obj=mock_context,
                )

                # Expect error code 1003 for empty directory with recursive flag
                assert result.exit_code == 1003
                assert "No markdown files found in directory" in result.output


class TestProcessCommandEdgeCases:
    """Test edge cases for process command."""

    @pytest.fixture
    def cli_runner(self):
        """Create Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_context(self):
        """Mock Click context."""
        config = Mock()
        config.chunking = Mock()
        config.chunking.default_size = 1000
        config.chunking.default_overlap = 200
        config.chunking.method = "structure"
        config.chromadb = Mock()
        config.chromadb.host = "localhost"
        config.chromadb.port = 8000
        # Fix logging config with proper types
        config.logging = Mock()
        config.logging.level = "INFO"
        config.logging.file_path = None
        config.logging.max_file_size = 10485760  # Actual integer
        config.logging.backup_count = 5

        return {
            "config": config,
            "quiet": False,
            "verbose": 0,
        }

    def test_process_command_with_special_characters_in_path(
        self, cli_runner, mock_context
    ):
        """Test processing files with special characters in path."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", prefix="test with spaces & chars!", delete=False
        ) as f:
            f.write("# Test\n\nContent")
            special_file = Path(f.name)

        with patch(
            "shard_markdown.cli.commands.process.load_app_config"
        ) as mock_config:
            mock_config.return_value = mock_context["config"]

            result = cli_runner.invoke(
                process,
                ["--collection", "test-collection", str(special_file)],
                obj=mock_context,
            )

            assert result.exit_code == 0

    def test_process_command_empty_markdown_file(self, cli_runner, mock_context):
        """Test processing an empty markdown file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("")  # Empty file
            empty_file = Path(f.name)

        with patch(
            "shard_markdown.cli.commands.process.load_app_config"
        ) as mock_config:
            mock_config.return_value = mock_context["config"]

            result = cli_runner.invoke(
                process,
                ["--collection", "test-collection", str(empty_file)],
                obj=mock_context,
            )

            # Should handle empty files gracefully
            assert result.exit_code == 0
