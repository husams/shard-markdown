"""Tests for the config command."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from shard_markdown.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    """Fixture for a Click CLI runner."""
    return CliRunner()


class TestConfigCommand:
    """Test cases for the 'config' command."""

    def test_path_command(self, runner: CliRunner) -> None:
        """Test the 'config path' command."""
        with runner.isolated_filesystem() as fs_dir_str:
            fs_dir = Path(fs_dir_str)
            with patch(
                "shard_markdown.cli.commands.config.DEFAULT_CONFIG_LOCATIONS",
                [fs_dir / "global.yaml", fs_dir / "local.yaml"],
            ):
                result = runner.invoke(cli, ["config", "path"])
                assert result.exit_code == 0
                assert "global.yaml" in result.output
                assert "local.yaml" in result.output

    def test_init_command(self, runner: CliRunner) -> None:
        """Test the 'config init' command."""
        with runner.isolated_filesystem() as fs_dir_str:
            fs_dir = Path(fs_dir_str)
            global_config_path = fs_dir / "global.yaml"
            local_config_path = fs_dir / "local.yaml"

            with patch(
                "shard_markdown.cli.commands.config.DEFAULT_CONFIG_LOCATIONS",
                [global_config_path, local_config_path],
            ):
                # Test local init (default)
                result = runner.invoke(cli, ["config", "init"])
                assert result.exit_code == 0
                assert local_config_path.exists()

                # Check the content
                with open(local_config_path) as f:
                    data = yaml.safe_load(f)
                assert "chromadb" in data
                assert "chunking" in data

                # Test that re-running without --force fails
                result = runner.invoke(cli, ["config", "init"])
                assert result.exit_code == 0
                assert "Configuration file already exists" in result.output

                # Test global init
                result = runner.invoke(cli, ["config", "init", "--global"])
                assert result.exit_code == 0
                assert global_config_path.exists()

    def test_show_command_yaml(self, runner: CliRunner) -> None:
        """Test the 'config show' command with YAML format."""
        with runner.isolated_filesystem() as fs_dir_str:
            fs_dir = Path(fs_dir_str)
            config_path = fs_dir / ".shard-md/config.yaml"
            with patch(
                "shard_markdown.config.settings._find_config_file",
                return_value=config_path,
            ):
                with patch(
                    "shard_markdown.cli.commands.config.DEFAULT_CONFIG_LOCATIONS",
                    [fs_dir / "dummy.yaml", config_path],
                ):
                    runner.invoke(cli, ["config", "init"])
                result = runner.invoke(cli, ["config", "show", "--format", "yaml"])
                assert result.exit_code == 0
                data = yaml.safe_load(result.output)
                assert "chromadb" in data

    def test_set_command(self, runner: CliRunner) -> None:
        """Test the 'config set' command."""
        with runner.isolated_filesystem() as fs_dir_str:
            fs_dir = Path(fs_dir_str)
            global_config_path = fs_dir / "global.yaml"
            local_config_path = fs_dir / "local.yaml"

            with patch(
                "shard_markdown.cli.commands.config.DEFAULT_CONFIG_LOCATIONS",
                [global_config_path, local_config_path],
            ):
                # Initialize config first
                runner.invoke(cli, ["config", "init"])

                # Test setting a value
                result = runner.invoke(
                    cli, ["config", "set", "chromadb.host", "example.com"]
                )
                assert result.exit_code == 0
                assert "Set chromadb.host = example.com" in result.output

                # Verify the value was set in the local config
                with open(local_config_path) as f:
                    data = yaml.safe_load(f)
                assert data["chromadb"]["host"] == "example.com"
