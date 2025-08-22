"""Unit tests for main CLI command."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from shard_markdown.cli.main import shard_md
from shard_markdown.core.models import DocumentChunk


class TestMainCLI:
    """Test main CLI functionality."""

    @pytest.fixture
    def cli_runner(self):
        """Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        with patch("shard_markdown.cli.main.load_config") as mock:
            config = Mock()
            config.chunk_size = 1000
            config.chunk_overlap = 200
            config.chunk_method = "structure"
            mock.return_value = config
            yield config

    @pytest.fixture
    def mock_parser(self):
        """Mock MarkdownParser."""
        with patch("shard_markdown.cli.main.MarkdownParser") as mock:
            parser = Mock()
            ast = Mock()
            ast.content = "# Test\nContent"
            ast.elements = [Mock()]
            parser.parse.return_value = ast
            mock.return_value = parser
            yield parser

    @pytest.fixture
    def mock_chunker(self):
        """Mock ChunkingEngine."""
        with patch("shard_markdown.cli.main.ChunkingEngine") as mock:
            chunker = Mock()
            chunks = [
                DocumentChunk(
                    content="Test chunk",
                    metadata={"source": "test.md"},
                    start_position=0,
                    end_position=10,
                )
            ]
            chunker.chunk_document.return_value = chunks
            mock.return_value = chunker
            yield chunker

    @pytest.fixture
    def mock_metadata_extractor(self):
        """Mock MetadataExtractor."""
        with patch("shard_markdown.cli.main.MetadataExtractor") as mock:
            extractor = Mock()
            extractor.extract_file_metadata.return_value = {"file_size": 100}
            extractor.extract_document_metadata.return_value = {"title": "Test"}
            mock.return_value = extractor
            yield extractor

    def test_basic_processing(
        self,
        cli_runner,
        sample_markdown_file,
        mock_config,
        mock_parser,
        mock_chunker,
        mock_metadata_extractor,
    ):
        """Test basic file processing without storage."""
        result = cli_runner.invoke(shard_md, [str(sample_markdown_file)])

        assert result.exit_code == 0
        assert "Processing Results" in result.output or "Total chunks:" in result.output

    def test_processing_with_custom_size(
        self,
        cli_runner,
        sample_markdown_file,
        mock_config,
        mock_parser,
        mock_chunker,
        mock_metadata_extractor,
    ):
        """Test processing with custom chunk size."""
        result = cli_runner.invoke(
            shard_md, [str(sample_markdown_file), "--size", "500", "--overlap", "50"]
        )

        assert result.exit_code == 0
        # Config should be updated with new values
        assert mock_config.chunk_size == 500
        assert mock_config.chunk_overlap == 50

    def test_processing_with_strategy(
        self,
        cli_runner,
        sample_markdown_file,
        mock_config,
        mock_parser,
        mock_chunker,
        mock_metadata_extractor,
    ):
        """Test processing with different chunking strategies."""
        result = cli_runner.invoke(
            shard_md, [str(sample_markdown_file), "--strategy", "token"]
        )

        assert result.exit_code == 0
        # Config should be updated with new strategy
        assert mock_config.chunk_method == "token"

    def test_help_output(self, cli_runner):
        """Test help output."""
        result = cli_runner.invoke(shard_md, ["--help"])

        assert result.exit_code == 0
        assert "Intelligently chunk markdown documents" in result.output
        assert "--size" in result.output
        assert "--strategy" in result.output
        assert "--store" in result.output
        assert "--collection" in result.output

    def test_version_output(self, cli_runner):
        """Test version output."""
        result = cli_runner.invoke(shard_md, ["--version"])

        assert result.exit_code == 0
        assert "shard-md, version" in result.output

    def test_nonexistent_file(self, cli_runner):
        """Test processing nonexistent file."""
        result = cli_runner.invoke(shard_md, ["nonexistent.md"])

        assert result.exit_code != 0
        assert "does not exist" in result.output
