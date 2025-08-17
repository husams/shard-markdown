"""Tests for CLI utilities module."""

from unittest.mock import Mock, patch

import pytest
from click import Abort, ClickException
from rich.console import Console

from shard_markdown.cli.utils import (
    console,
    get_connected_chromadb_client,
    handle_chromadb_errors,
)
from shard_markdown.config.settings import ChromaDBConfig
from shard_markdown.utils.errors import ShardMarkdownError


class TestSharedConsole:
    """Test shared console instance."""

    def test_console_instance_exists(self):
        """Test that console instance is available."""
        assert isinstance(console, Console)

    def test_console_is_singleton(self):
        """Test that importing console multiple times returns same instance."""
        from shard_markdown.cli.utils import console as console2

        assert console is console2


class TestHandleChromaDBErrors:
    """Test ChromaDB error handling function."""

    def test_handle_shard_markdown_error_basic(self, capsys):
        """Test handling ShardMarkdownError with basic verbosity."""
        error = ShardMarkdownError("Test error message", 1001, "TEST")

        with pytest.raises(Abort):
            handle_chromadb_errors(error, verbose=0)

        # Capture would be from rich console, so we just test it doesn't crash

    def test_handle_shard_markdown_error_verbose(self, capsys):
        """Test handling ShardMarkdownError with verbose output."""
        error = ShardMarkdownError("Test error message", 1001, "TEST")

        with pytest.raises(Abort):
            handle_chromadb_errors(error, verbose=1)

    def test_handle_connection_error_basic(self, capsys):
        """Test handling ConnectionError with basic verbosity."""
        error = ConnectionError("Connection failed")

        with pytest.raises(Abort):
            handle_chromadb_errors(error, verbose=0)

    def test_handle_connection_error_verbose(self, capsys):
        """Test handling ConnectionError with verbose output."""
        error = RuntimeError("Runtime error")

        with pytest.raises(Abort):
            # Use try/except to capture the exception for print_exception
            try:
                raise error
            except RuntimeError as e:
                handle_chromadb_errors(e, verbose=2)

    def test_handle_value_error(self, capsys):
        """Test handling ValueError."""
        error = ValueError("Invalid value")

        with pytest.raises(Abort):
            handle_chromadb_errors(error, verbose=1)


class TestGetConnectedChromaDBClient:
    """Test ChromaDB client connection function."""

    def test_successful_connection(self):
        """Test successful client connection."""
        # Mock config
        mock_config = Mock()
        mock_config.chromadb = ChromaDBConfig(host="localhost", port=8000)

        # Mock client
        mock_client = Mock()
        mock_client.connect.return_value = True

        with patch(
            "shard_markdown.cli.utils.create_chromadb_client", return_value=mock_client
        ) as mock_create:
            result = get_connected_chromadb_client(mock_config)

            assert result is mock_client
            mock_create.assert_called_once_with(mock_config.chromadb)
            mock_client.connect.assert_called_once()

    def test_failed_connection(self):
        """Test failed client connection."""
        # Mock config
        mock_config = Mock()
        mock_config.chromadb = ChromaDBConfig(host="localhost", port=8000)

        # Mock client that fails to connect
        mock_client = Mock()
        mock_client.connect.return_value = False

        with patch(
            "shard_markdown.cli.utils.create_chromadb_client", return_value=mock_client
        ) as mock_create:
            with pytest.raises(ClickException, match="Failed to connect to ChromaDB"):
                get_connected_chromadb_client(mock_config)

            mock_create.assert_called_once_with(mock_config.chromadb)
            mock_client.connect.assert_called_once()

    def test_connection_exception(self):
        """Test handling exceptions during connection."""
        # Mock config
        mock_config = Mock()
        mock_config.chromadb = ChromaDBConfig(host="localhost", port=8000)

        # Mock client that raises exception
        mock_client = Mock()
        mock_client.connect.side_effect = RuntimeError("Connection error")

        with patch(
            "shard_markdown.cli.utils.create_chromadb_client", return_value=mock_client
        ) as mock_create:
            with pytest.raises(RuntimeError, match="Connection error"):
                get_connected_chromadb_client(mock_config)

            mock_create.assert_called_once_with(mock_config.chromadb)
            mock_client.connect.assert_called_once()
