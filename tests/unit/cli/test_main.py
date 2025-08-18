"""Unit tests for CLI main module."""

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from shard_markdown.cli.main import cli, main


class TestCLIMain:
    """Test CLI main functionality."""

    def test_cli_help(self, cli_runner: Any) -> None:
        """Test CLI help output."""
        result = cli_runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Shard Markdown" in result.output
        assert "Intelligent document chunking" in result.output
        assert "Commands:" in result.output

    def test_cli_version(self, cli_runner: Any) -> None:
        """Test version command."""
        result = cli_runner.invoke(cli, ["version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output
        assert "shard-md" in result.output

    def test_cli_version_option(self, cli_runner: Any) -> None:
        """Test --version option."""
        result = cli_runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output

    @patch("shard_markdown.cli.main.load_config")
    @patch("shard_markdown.cli.main.setup_logging")
    def test_cli_with_config_file(
        self,
        mock_setup_logging: Mock,
        mock_load_config: Mock,
        cli_runner: Any,
    ) -> None:
        """Test CLI with custom config file."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("chromadb:\n  host: localhost\n  port: 8000\n")
            config_file = Path(f.name)

        mock_config = Mock()
        mock_config.logging.file_path = None
        mock_config.logging.max_file_size = 10485760
        mock_config.logging.backup_count = 3
        mock_load_config.return_value = mock_config

        result = cli_runner.invoke(
            cli, ["--config", str(config_file), "collections", "list"]
        )
        assert result is not None

        # Check that the config was loaded and logging was setup
        mock_load_config.assert_called_once()
        mock_setup_logging.assert_called_once()

        # Clean up
        config_file.unlink()

    def test_cli_verbose_levels(self, cli_runner: Any) -> None:
        """Test different verbosity levels."""
        # Single verbose
        result = cli_runner.invoke(cli, ["-v", "--help"])
        assert result.exit_code == 0

        # Double verbose
        result = cli_runner.invoke(cli, ["-vv", "--help"])
        assert result.exit_code == 0

        # Triple verbose
        result = cli_runner.invoke(cli, ["-vvv", "--help"])
        assert result.exit_code == 0

    def test_cli_quiet_flag(self, cli_runner: Any) -> None:
        """Test quiet flag."""
        result = cli_runner.invoke(cli, ["--quiet", "--help"])
        assert result.exit_code == 0

    def test_main_entry_point(self) -> None:
        """Test main entry point function."""
        # Just test that main doesn't error on import
        assert main is not None
        assert callable(main)

    def test_cli_group_structure(self, cli_runner: Any) -> None:
        """Test CLI group structure and commands."""
        # Test basic structure
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

        # Should have main commands
        expected_commands = ["process", "collections", "query", "config", "version"]
        for command in expected_commands:
            assert command in result.output

    def test_cli_invalid_command(self, cli_runner: Any) -> None:
        """Test CLI with invalid command."""
        result = cli_runner.invoke(cli, ["invalid-command"])
        assert result.exit_code != 0
        assert "No such command" in result.output

    def test_cli_config_validation(self, cli_runner: Any) -> None:
        """Test CLI config file validation."""
        # Test with non-existent config file
        result = cli_runner.invoke(
            cli, ["--config", "/nonexistent/config.yaml", "--help"]
        )
        # CLI should still show help even with invalid config path
        assert result.exit_code == 0
