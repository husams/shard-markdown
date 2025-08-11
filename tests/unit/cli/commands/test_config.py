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
                "shard_markdown.config.defaults.DEFAULT_CONFIG_LOCATIONS",
                [fs_dir / "global.yaml", fs_dir / "local.yaml"],
            ):
                result = runner.invoke(cli, ["config", "path"])
                assert result.exit_code == 0
                assert "Configuration file locations" in result.output

    def test_init_command(self, runner: CliRunner) -> None:
        """Test the 'config init' command."""
        with runner.isolated_filesystem() as fs_dir_str:
            fs_dir = Path(fs_dir_str)
            local_config_path = fs_dir / ".shard-md" / "config.yaml"
            global_config_path = fs_dir / "global.yaml"
            with patch(
                "shard_markdown.cli.commands.config.DEFAULT_CONFIG_LOCATIONS",
                [global_config_path, local_config_path],
            ):
                result = runner.invoke(cli, ["config", "init"])
                assert result.exit_code == 0
                assert "Initialized configuration file" in result.output
                assert local_config_path.exists()

    def test_init_command_global(self, runner: CliRunner) -> None:
        """Test the 'config init --global' command."""
        with runner.isolated_filesystem() as fs_dir_str:
            fs_dir = Path(fs_dir_str)
            global_config_path = fs_dir / ".shard-md" / "config.yaml"
            with patch(
                "shard_markdown.cli.commands.config.DEFAULT_CONFIG_LOCATIONS",
                [global_config_path],
            ):
                result = runner.invoke(cli, ["config", "init", "--global"])
                assert result.exit_code == 0
                assert global_config_path.exists()

    def test_init_command_force(self, runner: CliRunner) -> None:
        """Test the 'config init --force' command."""
        with runner.isolated_filesystem() as fs_dir_str:
            fs_dir = Path(fs_dir_str)
            config_path = fs_dir / ".shard-md" / "config.yaml"
            config_path.parent.mkdir()
            config_path.write_text("old content")
            with patch(
                "shard_markdown.cli.commands.config.DEFAULT_CONFIG_LOCATIONS",
                [fs_dir / "dummy.yaml", config_path],
            ):
                result = runner.invoke(cli, ["config", "init", "--force"])
                assert result.exit_code == 0
                content = config_path.read_text()
                assert "old content" not in content

    def test_init_command_already_exists(self, runner: CliRunner) -> None:
        """Test 'config init' when file already exists without --force."""
        with runner.isolated_filesystem() as fs_dir_str:
            fs_dir = Path(fs_dir_str)
            config_path = fs_dir / ".shard-md" / "config.yaml"
            config_path.parent.mkdir()
            config_path.write_text("old content")
            with patch(
                "shard_markdown.cli.commands.config.DEFAULT_CONFIG_LOCATIONS",
                [fs_dir / "dummy.yaml", config_path],
            ):
                result = runner.invoke(cli, ["config", "init"])
                assert result.exit_code == 0
                assert "Configuration file already exists" in result.output

    def test_show_command_yaml(self, runner: CliRunner) -> None:
        """Test the 'config show' command with YAML format."""
        with runner.isolated_filesystem() as fs_dir_str:
            fs_dir = Path(fs_dir_str)
            config_path = fs_dir / ".shard-md/config.yaml"
            with patch(
                "shard_markdown.config.loader._find_config_file",
                return_value=config_path,
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
            config_path = fs_dir / ".shard-md/config.yaml"
            with patch(
                "shard_markdown.cli.commands.config.DEFAULT_CONFIG_LOCATIONS",
                [fs_dir / "dummy.yaml", config_path],
            ):
                runner.invoke(cli, ["config", "init"])
                result = runner.invoke(
                    cli, ["config", "set", "chunking.default_size", "1234"]
                )
                assert result.exit_code == 0
                assert "Set chunking.default_size = 1234" in result.output
                with config_path.open() as f:
                    config_data = yaml.safe_load(f)
                assert config_data["chunking"]["default_size"] == 1234

    def test_set_command_custom_metadata(self, runner: CliRunner) -> None:
        """Test 'config set' with a custom metadata key."""
        with runner.isolated_filesystem() as fs_dir_str:
            fs_dir = Path(fs_dir_str)
            config_path = fs_dir / ".shard-md" / "config.yaml"
            with patch(
                "shard_markdown.cli.commands.config.DEFAULT_CONFIG_LOCATIONS",
                [fs_dir / "dummy.yaml", config_path],
            ):
                runner.invoke(cli, ["config", "init"])
                result = runner.invoke(
                    cli, ["config", "set", "custom_metadata.foo", "bar"]
                )
                assert result.exit_code == 0
                with config_path.open() as f:
                    config_data = yaml.safe_load(f)
                assert config_data["custom_metadata"]["foo"] == "bar"
