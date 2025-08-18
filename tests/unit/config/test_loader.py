"""Tests for configuration loader backward compatibility layer."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from shard_markdown.config.loader import (
    create_default_config,
    load_config,
    save_config,
)
from shard_markdown.config.settings import AppConfig, ChromaDBConfig


class TestLoaderBackwardCompatibility:
    """Test backward compatibility of loader module functions."""

    def test_load_config_no_args(self) -> None:
        """Test load_config works without arguments."""
        # Mock _find_config_file to return None (no config files found)
        # and clear environment variables
        with patch(
            "shard_markdown.config.settings._find_config_file", return_value=None
        ):
            with patch.dict(os.environ, {}, clear=True):
                config = load_config()

                # Should return valid AppConfig with defaults
                assert isinstance(config, AppConfig)
                assert config.chromadb.host == "localhost"
                assert config.chromadb.port == 8000
                assert config.chunking.default_size == 1000

    def test_load_config_with_path(self) -> None:
        """Test load_config works with explicit path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yaml"

            # Create a test config file
            config_data = {
                "chromadb": {"host": "test-host", "port": 9000, "ssl": True},
                "chunking": {"default_size": 1500, "default_overlap": 300},
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Clear all environment variables to ensure clean state
            with patch.dict(os.environ, {}, clear=True):
                config = load_config(config_path)

                # Should load custom values
                assert config.chromadb.host == "test-host"
                assert config.chromadb.port == 9000
                assert config.chromadb.ssl is True
                assert config.chunking.default_size == 1500
                assert config.chunking.default_overlap == 300

    def test_load_config_nonexistent_path(self) -> None:
        """Test load_config raises error for nonexistent explicit path."""
        nonexistent_path = Path("/nonexistent/path/config.yaml")

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config(nonexistent_path)

    def test_save_config_creates_file(self) -> None:
        """Test save_config creates configuration file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "saved_config.yaml"

            # Create a config to save
            config = AppConfig(chromadb=ChromaDBConfig(host="saved-host", port=7000))

            # Save the config
            save_config(config, config_path)

            # Verify file was created and content is correct
            assert config_path.exists()

            with open(config_path) as f:
                saved_data = yaml.safe_load(f)

            assert saved_data["chromadb"]["host"] == "saved-host"
            assert saved_data["chromadb"]["port"] == 7000

    def test_save_config_creates_directory(self) -> None:
        """Test save_config creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nested" / "dir" / "config.yaml"

            # Parent directories don't exist yet
            assert not config_path.parent.exists()

            config = AppConfig()
            save_config(config, config_path)

            # Should have created directories and file
            assert config_path.exists()
            assert config_path.parent.exists()

    def test_create_default_config_new_file(self) -> None:
        """Test create_default_config creates new configuration file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "default_config.yaml"

            # Create default config
            create_default_config(config_path)

            # Verify file was created
            assert config_path.exists()

            # Verify content is valid YAML and contains expected sections
            with open(config_path) as f:
                content = f.read()
                data = yaml.safe_load(content)

            assert "chromadb" in data
            assert "chunking" in data
            assert "processing" in data
            assert "logging" in data

            # Check some default values
            assert data["chromadb"]["host"] == "localhost"
            assert data["chromadb"]["port"] == 8000
            assert data["chunking"]["default_size"] == 1000

    def test_create_default_config_existing_file_no_force(self) -> None:
        """Test create_default_config raises error when file exists and force=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "existing_config.yaml"

            # Create existing file
            config_path.write_text("existing content")

            # Should raise error when trying to create without force
            with pytest.raises(
                FileExistsError, match="Configuration file already exists"
            ):
                create_default_config(config_path, force=False)

            # File should still contain original content
            assert config_path.read_text() == "existing content"

    def test_create_default_config_existing_file_with_force(self) -> None:
        """Test create_default_config overwrites existing file when force=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "existing_config.yaml"

            # Create existing file
            config_path.write_text("existing content")

            # Should overwrite when force=True
            create_default_config(config_path, force=True)

            # File should now contain default config
            content = config_path.read_text()
            assert "chromadb:" in content
            assert "localhost" in content
            assert "existing content" not in content

    def test_create_default_config_creates_directory(self) -> None:
        """Test create_default_config creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nested" / "path" / "config.yaml"

            # Parent directories don't exist yet
            assert not config_path.parent.exists()

            create_default_config(config_path)

            # Should have created directories and file
            assert config_path.exists()
            assert config_path.parent.exists()

    def test_loader_functions_are_reexports(self) -> None:
        """Test that loader functions are properly re-exported from settings."""
        # Import directly from settings to compare
        from shard_markdown.config.settings import (
            create_default_config as settings_create,
        )
        from shard_markdown.config.settings import (
            load_config as settings_load,
        )
        from shard_markdown.config.settings import (
            save_config as settings_save,
        )

        # Functions should be the same objects (re-exports)
        assert load_config is settings_load
        assert save_config is settings_save
        assert create_default_config is settings_create

    def test_loader_module_all_exports(self) -> None:
        """Test that loader module exports expected functions in __all__."""
        import shard_markdown.config.loader as loader_module

        # Check __all__ contains expected functions
        expected_exports = {"create_default_config", "load_config", "save_config"}
        assert set(loader_module.__all__) == expected_exports

        # Check all exported functions are accessible
        for func_name in expected_exports:
            assert hasattr(loader_module, func_name)
            assert callable(getattr(loader_module, func_name))


class TestLoaderEnvironmentIntegration:
    """Test loader functions work correctly with environment variables."""

    def test_load_config_with_env_overrides(self) -> None:
        """Test load_config applies environment variable overrides."""
        env_vars = {
            "CHROMA_HOST": "env-host",
            "CHROMA_PORT": "9999",
            "CHROMA_SSL": "true",
            "SHARD_MD_CHUNK_SIZE": "2000",
        }

        # Mock _find_config_file to return None (no config files)
        with patch(
            "shard_markdown.config.settings._find_config_file", return_value=None
        ):
            with patch.dict(os.environ, env_vars, clear=True):
                config = load_config()

                # Environment variables should override defaults
                assert config.chromadb.host == "env-host"
                assert config.chromadb.port == 9999
                assert config.chromadb.ssl is True
                assert config.chunking.default_size == 2000

    def test_load_config_file_and_env_precedence(self) -> None:
        """Test that environment variables override config file values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yaml"

            # Create config file with some values
            config_data = {
                "chromadb": {"host": "file-host", "port": 8080, "ssl": False}
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Set environment variables that should override file values
            env_vars = {
                "CHROMA_HOST": "env-override-host",
                "CHROMA_SSL": "true",
                # PORT not set, should use file value
            }

            with patch.dict(os.environ, env_vars, clear=True):
                config = load_config(config_path)

                # Env vars should override file values
                assert config.chromadb.host == "env-override-host"
                assert config.chromadb.ssl is True

                # File value should be used when env var not set
                assert config.chromadb.port == 8080

    def test_load_config_real_file_discovery(self) -> None:
        """Test load_config discovers actual config files in default locations."""
        # This test verifies that config file discovery works as expected
        # without mocking the file discovery mechanism

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a config file in what would be a default location
            config_path = Path(tmpdir) / "shard-md.yaml"
            config_data = {"chromadb": {"host": "discovered-host", "port": 7777}}

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Mock the default locations to include our test directory
            with patch(
                "shard_markdown.config.settings.DEFAULT_CONFIG_LOCATIONS", [config_path]
            ):
                with patch.dict(os.environ, {}, clear=True):
                    config = load_config()

                    # Should have discovered and loaded our config file
                    assert config.chromadb.host == "discovered-host"
                    assert config.chromadb.port == 7777
