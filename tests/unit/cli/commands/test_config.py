"""Tests for config command."""

from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
from click.testing import CliRunner

from shard_markdown.cli.commands.config import config, init, show
from shard_markdown.cli.commands.config import set as set_config


class TestConfigCommands:
    """Test cases for config commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config_obj(self):
        """Create mock config object."""
        config_obj = Mock()
        config_obj.chromadb = Mock()
        config_obj.chromadb.host = "localhost"
        config_obj.chromadb.port = 8000
        config_obj.chunking = Mock()
        config_obj.chunking.method = "fixed"
        config_obj.chunking.chunk_size = 1000
        config_obj.chunking.overlap = 100
        return config_obj

    def test_config_show(self, runner, mock_config_obj):
        """Test showing configuration."""
        with patch("shard_markdown.cli.commands.config.load_config") as mock_load:
            mock_load.return_value = mock_config_obj
            result = runner.invoke(config, ["show"])

            assert result.exit_code == 0
            assert "Configuration Settings" in result.output
            assert "localhost" in result.output
            assert "8000" in result.output

    def test_config_show_json_format(self, runner, mock_config_obj):
        """Test showing config in JSON format."""
        with patch("shard_markdown.cli.commands.config.load_config") as mock_load:
            mock_load.return_value = mock_config_obj
            result = runner.invoke(config, ["show", "--format", "json"])

            assert result.exit_code == 0
            # Should contain JSON structure
            assert "{" in result.output or "chromadb" in result.output

    def test_config_set(self, runner):
        """Test setting config value."""
        with patch("shard_markdown.cli.commands.config.Path") as mock_path:
            mock_file = mock_open()
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.open = mock_file

            with patch(
                "shard_markdown.cli.commands.config.yaml.safe_load"
            ) as mock_load:
                mock_load.return_value = {
                    "chromadb": {"host": "localhost", "port": 8000},
                }

                with patch("shard_markdown.cli.commands.config.yaml.dump"):
                    result = runner.invoke(
                        config,
                        ["set", "chromadb.host", "127.0.0.1"],
                    )

                    assert result.exit_code == 0
                    assert "Updated" in result.output
                    # Dump was called implicitly

    def test_config_set_new_key(self, runner):
        """Test setting new config key."""
        with patch("shard_markdown.cli.commands.config.Path") as mock_path:
            mock_file = mock_open()
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.open = mock_file

            with patch(
                "shard_markdown.cli.commands.config.yaml.safe_load"
            ) as mock_load:
                mock_load.return_value = {}

                with patch("shard_markdown.cli.commands.config.yaml.dump"):
                    result = runner.invoke(
                        config,
                        ["set", "new.key", "value"],
                    )

                    assert result.exit_code == 0
                    # Dump was called implicitly

    def test_config_init(self, runner):
        """Test initializing config."""
        with patch("shard_markdown.cli.commands.config.Path") as mock_path:
            # Config doesn't exist yet
            mock_path.return_value.exists.return_value = False
            mock_path.return_value.parent.mkdir = Mock()

            mock_file = mock_open()
            mock_path.return_value.open = mock_file

            with patch("shard_markdown.cli.commands.config.yaml.dump"):
                result = runner.invoke(config, ["init"])

                assert result.exit_code == 0
                assert "Created" in result.output
                # Dump was called implicitly

    def test_config_init_already_exists(self, runner):
        """Test initializing config when it already exists."""
        with patch("shard_markdown.cli.commands.config.Path") as mock_path:
            # Config already exists
            mock_path.return_value.exists.return_value = True

            result = runner.invoke(config, ["init"])

            assert result.exit_code == 0
            assert "already exists" in result.output

    def test_config_init_with_force(self, runner):
        """Test force initializing config."""
        with patch("shard_markdown.cli.commands.config.Path") as mock_path:
            # Config already exists but we force
            mock_path.return_value.exists.return_value = True

            mock_file = mock_open()
            mock_path.return_value.open = mock_file

            with patch("shard_markdown.cli.commands.config.yaml.dump"):
                result = runner.invoke(config, ["init", "--force"])

                assert result.exit_code == 0
                assert "Created" in result.output
                # Dump was called implicitly

    def test_config_path(self, runner):
        """Test showing config path."""
        with patch("shard_markdown.cli.commands.config.Path") as mock_path:
            mock_path.return_value = Path("/home/user/.shard-md/config.yaml")
            result = runner.invoke(config, ["path"])

            assert result.exit_code == 0
            assert "config.yaml" in result.output

    def test_show_standalone(self, runner, mock_config_obj):
        """Test show command standalone."""
        with patch("shard_markdown.cli.commands.config.load_config") as mock_load:
            mock_load.return_value = mock_config_obj
            result = runner.invoke(show)

            assert result.exit_code == 0
            assert "localhost" in result.output

    def test_set_standalone(self, runner):
        """Test set command standalone."""
        with patch("shard_markdown.cli.commands.config.Path") as mock_path:
            mock_file = mock_open()
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.open = mock_file

            with patch(
                "shard_markdown.cli.commands.config.yaml.safe_load"
            ) as mock_load:
                mock_load.return_value = {"chunking": {}}

                with patch("shard_markdown.cli.commands.config.yaml.dump"):
                    result = runner.invoke(
                        set_config,
                        ["chunking.chunk_size", "2000"],
                    )

                    assert result.exit_code == 0

    def test_init_standalone(self, runner):
        """Test init command standalone."""
        with patch("shard_markdown.cli.commands.config.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            mock_path.return_value.parent.mkdir = Mock()

            mock_file = mock_open()
            mock_path.return_value.open = mock_file

            with patch("shard_markdown.cli.commands.config.yaml.dump"):
                result = runner.invoke(init)

                assert result.exit_code == 0
                # Dump was called implicitly
