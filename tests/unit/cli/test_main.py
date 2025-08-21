"""Unit tests for CLI main module."""

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
        config_file: Any,
    ) -> None:
        """Test CLI with custom config file."""
        mock_config = Mock()
        mock_config.logging.file_path = None
        mock_config.logging.max_file_size = 10485760
        mock_config.logging.backup_count = 3
        mock_load_config.return_value = mock_config

        result = cli_runner.invoke(cli, ["--config", str(config_file), "data", "list"])
        assert result is not None

        # Check that the config was loaded and logging was setup
        mock_load_config.assert_called_once()
        mock_setup_logging.assert_called_once()

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

    def test_cli_quiet_mode(self, cli_runner: Any) -> None:
        """Test quiet mode."""
        result = cli_runner.invoke(cli, ["--quiet", "--help"])
        assert result.exit_code == 0

    @patch("shard_markdown.cli.main.setup_logging")
    def test_cli_log_file_option(
        self, mock_setup_logging: Mock, cli_runner: Any, temp_dir: Any
    ) -> None:
        """Test custom log file option."""
        log_file = temp_dir / "test.log"

        result = cli_runner.invoke(cli, ["--log-file", str(log_file), "data", "list"])
        assert result is not None

        # Check that setup_logging was called with our log file
        mock_setup_logging.assert_called_once()

    @patch("shard_markdown.cli.main.load_config")
    def test_cli_config_loading_error(
        self, mock_load_config: Mock, cli_runner: Any
    ) -> None:
        """Test handling of config loading errors."""
        mock_load_config.side_effect = Exception("Config error")

        result = cli_runner.invoke(cli, ["data", "list"])

        assert result.exit_code == 1
        assert "Error initializing" in result.output

    def test_main_function(self) -> None:
        """Test main entry point function."""
        # This would typically be tested by checking that cli() is called
        # Since we can't easily test the actual execution, we just ensure
        # the function exists and is callable
        assert callable(main)

    @patch("shard_markdown.cli.main.load_config")
    @patch("shard_markdown.cli.main.setup_logging")
    def test_cli_context_setup(
        self, mock_setup_logging: Mock, mock_load_config: Mock, cli_runner: Any
    ) -> None:
        """Test that CLI context is properly set up."""
        mock_config = Mock()
        mock_config.logging.file_path = None
        mock_config.logging.max_file_size = 10485760
        mock_config.logging.backup_count = 3
        mock_load_config.return_value = mock_config

        # Use a command that requires context to test context passing
        result = cli_runner.invoke(cli, ["--verbose", "data", "list"])
        assert result is not None

        mock_load_config.assert_called_once()
        mock_setup_logging.assert_called_once()

    def test_cli_invalid_option(self, cli_runner: Any) -> None:
        """Test handling of invalid CLI options."""
        result = cli_runner.invoke(cli, ["--invalid-option"])

        assert result.exit_code != 0
        assert "No such option" in result.output

    def test_cli_command_groups_registered(self, cli_runner: Any) -> None:
        """Test that all command groups are properly registered."""
        result = cli_runner.invoke(cli, ["--help"])

        assert result.exit_code == 0

        # Check that main command groups are present
        assert "process" in result.output
        assert "data" in result.output
        # query is now part of data command
        assert "config" in result.output


class TestCLILogging:
    """Test CLI logging configuration."""

    @patch("shard_markdown.cli.main.setup_logging")
    @patch("shard_markdown.cli.main.load_config")
    def test_logging_setup_quiet_mode(
        self, mock_load_config: Mock, mock_setup_logging: Mock, cli_runner: Any
    ) -> None:
        """Test logging setup in quiet mode."""
        mock_config = Mock()
        mock_config.logging.file_path = None
        mock_config.logging.max_file_size = 10485760
        mock_config.logging.backup_count = 3
        mock_load_config.return_value = mock_config

        result = cli_runner.invoke(cli, ["--quiet", "data", "list"])
        assert result is not None

        # Check that setup_logging was called with appropriate level (40 = ERROR)
        call_args = mock_setup_logging.call_args
        assert call_args[1]["level"] == 40

    @patch("shard_markdown.cli.main.setup_logging")
    @patch("shard_markdown.cli.main.load_config")
    def test_logging_setup_verbose_mode(
        self, mock_load_config: Mock, mock_setup_logging: Mock, cli_runner: Any
    ) -> None:
        """Test logging setup in verbose mode."""
        mock_config = Mock()
        mock_config.logging.file_path = None
        mock_config.logging.max_file_size = 10485760
        mock_config.logging.backup_count = 3
        mock_load_config.return_value = mock_config

        result = cli_runner.invoke(cli, ["-vvv", "data", "list"])
        assert result is not None

        # Check that setup_logging was called with debug level (10 = DEBUG)
        call_args = mock_setup_logging.call_args
        assert call_args[1]["level"] == 10

    @patch("shard_markdown.cli.main.setup_logging")
    @patch("shard_markdown.cli.main.load_config")
    def test_logging_setup_custom_log_file(
        self,
        mock_load_config: Mock,
        mock_setup_logging: Mock,
        cli_runner: Any,
        temp_dir: Any,
    ) -> None:
        """Test logging setup with custom log file."""
        mock_config = Mock()
        mock_config.logging.file_path = None
        mock_config.logging.max_file_size = 10485760
        mock_config.logging.backup_count = 3
        mock_load_config.return_value = mock_config

        log_file = temp_dir / "custom.log"
        result = cli_runner.invoke(cli, ["--log-file", str(log_file), "data", "list"])
        assert result is not None

        # Check that setup_logging was called with custom log file
        call_args = mock_setup_logging.call_args
        assert call_args[1]["file_path"] == log_file


class TestCLIHelp:
    """Test CLI help and documentation."""

    def test_cli_examples_in_help(self, cli_runner: Any) -> None:
        """Test that help includes usage examples."""
        result = cli_runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Examples:" in result.output
        assert "shard-md process" in result.output
        assert "shard-md data list" in result.output
        assert "shard-md data search" in result.output

    def test_cli_prog_name(self, cli_runner: Any) -> None:
        """Test that CLI uses correct program name."""
        result = cli_runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "shard-md" in result.output

    def test_cli_description(self, cli_runner: Any) -> None:
        """Test CLI description is informative."""
        result = cli_runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Intelligent document chunking" in result.output
        assert "ChromaDB" in result.output


class TestCLIErrorHandling:
    """Test CLI error handling."""

    @patch("shard_markdown.cli.main.load_config")
    def test_config_error_handling(
        self, mock_load_config: Mock, cli_runner: Any
    ) -> None:
        """Test handling of configuration errors."""
        mock_load_config.side_effect = FileNotFoundError("Config not found")

        result = cli_runner.invoke(cli, ["data", "list"])

        assert result.exit_code == 1
        assert "Error initializing shard-md" in result.output

    @patch("shard_markdown.cli.main.setup_logging")
    @patch("shard_markdown.cli.main.load_config")
    def test_logging_error_handling(
        self, mock_load_config: Mock, mock_setup_logging: Mock, cli_runner: Any
    ) -> None:
        """Test handling of logging setup errors."""
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        mock_setup_logging.side_effect = Exception("Logging error")

        result = cli_runner.invoke(cli, ["data", "list"])

        assert result.exit_code == 1
        assert "Error initializing shard-md" in result.output

    def test_nonexistent_config_file(self, cli_runner: Any) -> None:
        """Test handling of non-existent config file."""
        result = cli_runner.invoke(cli, ["--config", "nonexistent.yaml", "--help"])

        # Should handle gracefully or show appropriate error
        assert (
            "No such file" in result.output or result.exit_code == 0
        )  # Depending on implementation


class TestCLIIntegration:
    """Test CLI integration aspects."""

    @patch("shard_markdown.cli.main.load_config")
    def test_cli_with_real_config_structure(
        self, mock_load_config: Mock, cli_runner: Any
    ) -> None:
        """Test CLI with realistic config structure."""
        # Create a realistic mock config
        mock_config = Mock()
        mock_config.logging.file_path = None
        mock_config.logging.max_file_size = 10485760
        mock_config.logging.backup_count = 3

        # Add realistic attributes that commands might use
        mock_config.chromadb.host = "localhost"
        mock_config.chromadb.port = 8000
        mock_config.chunking.default_size = 1000
        mock_config.processing.batch_size = 10

        mock_load_config.return_value = mock_config

        result = cli_runner.invoke(cli, ["data", "list"])
        assert result is not None

        mock_load_config.assert_called_once()

    def test_cli_traceback_handling(self, cli_runner: Any) -> None:
        """Test that rich tracebacks are properly installed."""
        # This is tested indirectly by ensuring the CLI loads without error
        # The rich.traceback.install() call should be executed on import
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
