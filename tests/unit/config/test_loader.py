"""Tests for configuration loader backward compatibility.

Tests that the functions previously in loader.py still work correctly
and provide backward compatibility for the old nested configuration format.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from shard_markdown.config import (
    AppConfig,
    Settings,
    create_default_config,
    load_config,
    save_config,
)


class TestLoaderBackwardCompatibility:
    """Test backward compatibility of configuration loading functions."""

    def test_load_config_no_args(self) -> None:
        """Test load_config works without arguments."""
        # Mock _find_config_file to return None (no config files found)
        # and clear environment variables
        with patch(
            "shard_markdown.config.settings._find_config_file", return_value=None
        ):
            with patch.dict(os.environ, {}, clear=True):
                config = load_config()

                # Should return valid Settings with defaults
                assert isinstance(config, Settings)
                assert config.chroma_host == "localhost"
                assert config.chroma_port == 8000
                assert config.chunk_size == 1000

    def test_load_config_with_path(self) -> None:
        """Test load_config works with explicit path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yaml"

            # Create a test config file using flat structure
            config_data = {
                "chroma_host": "test-host",
                "chroma_port": 9000,
                "chroma_ssl": True,
                "chunk_size": 1500,
                "chunk_overlap": 300,
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Clear all environment variables to ensure clean state
            with patch.dict(os.environ, {}, clear=True):
                config = load_config(config_path)

                # Should load custom values
                assert config.chroma_host == "test-host"
                assert config.chroma_port == 9000
                assert config.chroma_ssl is True
                assert config.chunk_size == 1500
                assert config.chunk_overlap == 300

    def test_load_config_nested_backward_compatibility(self) -> None:
        """Test load_config handles old nested configuration format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nested_config.yaml"

            # Create a test config file using OLD nested structure
            config_data = {
                "chromadb": {"host": "nested-host", "port": 9000, "ssl": True},
                "chunking": {"default_size": 1500, "default_overlap": 300},
                "logging": {"level": "DEBUG"},
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Clear all environment variables to ensure clean state
            with patch.dict(os.environ, {}, clear=True):
                config = load_config(config_path)

                # Should load and migrate nested values to flat structure
                assert config.chroma_host == "nested-host"
                assert config.chroma_port == 9000
                assert config.chroma_ssl is True
                assert config.chunk_size == 1500
                assert config.chunk_overlap == 300
                assert config.log_level == "DEBUG"

    def test_load_config_nonexistent_path(self) -> None:
        """Test load_config raises error for nonexistent explicit path."""
        nonexistent_path = Path("/nonexistent/path/config.yaml")

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config(nonexistent_path)

    def test_save_config_creates_file(self) -> None:
        """Test save_config creates configuration file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "saved_config.yaml"

            # Create a config to save using new flat structure
            config = Settings(chroma_host="saved-host", chroma_port=7000)

            # Save the config
            save_config(config, config_path)

            # Verify file was created and content is correct
            assert config_path.exists()

            with open(config_path) as f:
                saved_data = yaml.safe_load(f)

            assert saved_data["chroma_host"] == "saved-host"
            assert saved_data["chroma_port"] == 7000

    def test_save_config_creates_directory(self) -> None:
        """Test save_config creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nested" / "dir" / "config.yaml"

            # Parent directories don't exist yet
            assert not config_path.parent.exists()

            config = Settings()
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

            # Check for flat structure keys
            assert "chroma_host" in data
            assert "chunk_size" in data
            assert "log_level" in data

            # Check some default values
            assert data["chroma_host"] == "localhost"
            assert data["chroma_port"] == 8000
            assert data["chunk_size"] == 1000

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
            assert "chroma_host: localhost" in content
            assert "chroma_port: 8000" in content
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

    def test_backward_compatibility_classes(self) -> None:
        """Test that backward compatibility classes work correctly."""
        # AppConfig provides the old nested structure
        app_config = AppConfig()

        # Should have nested structure for backward compatibility
        assert hasattr(app_config, "chromadb")
        assert hasattr(app_config, "chunking")
        assert hasattr(app_config, "logging")

        # ChromaDB config should have old attribute names
        assert app_config.chromadb.host == "localhost"
        assert app_config.chromadb.port == 8000

        # Chunking config should have old attribute names
        assert app_config.chunking.default_size == 1000
        assert app_config.chunking.default_overlap == 200

        # New Settings class should have flat structure
        settings = Settings()
        assert settings.chroma_host == "localhost"
        assert settings.chroma_port == 8000
        assert settings.chunk_size == 1000
        assert settings.chunk_overlap == 200


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
                assert config.chroma_host == "env-host"
                assert config.chroma_port == 9999
                assert config.chroma_ssl is True
                assert config.chunk_size == 2000

    def test_load_config_file_and_env_precedence(self) -> None:
        """Test that environment variables override config file values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yaml"

            # Create config file with some values (flat structure)
            config_data = {
                "chroma_host": "file-host",
                "chroma_port": 8080,
                "chroma_ssl": False,
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
                assert config.chroma_host == "env-override-host"
                assert config.chroma_ssl is True

                # File value should be used when env var not set
                assert config.chroma_port == 8080

    def test_load_config_nested_file_and_env_precedence(self) -> None:
        """Test that environment variables override nested config file values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yaml"

            # Create config file with nested structure (backward compatibility)
            config_data = {
                "chromadb": {"host": "nested-file-host", "port": 8080, "ssl": False}
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Set environment variables that should override file values
            env_vars = {
                "CHROMA_HOST": "env-override-host",
                "CHROMA_SSL": "true",
            }

            with patch.dict(os.environ, env_vars, clear=True):
                config = load_config(config_path)

                # Env vars should override migrated nested file values
                assert config.chroma_host == "env-override-host"
                assert config.chroma_ssl is True

                # Migrated file value should be used when env var not set
                assert config.chroma_port == 8080

    def test_load_config_real_file_discovery(self) -> None:
        """Test load_config discovers actual config files in default locations."""
        # This test verifies that config file discovery works as expected
        # without mocking the file discovery mechanism

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a config file in what would be a default location
            config_path = Path(tmpdir) / "shard-md.yaml"
            config_data = {"chroma_host": "discovered-host", "chroma_port": 7777}

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Mock the default locations to include our test directory
            with patch(
                "shard_markdown.config.settings.DEFAULT_CONFIG_LOCATIONS", [config_path]
            ):
                with patch.dict(os.environ, {}, clear=True):
                    config = load_config()

                    # Should have discovered and loaded our config file
                    assert config.chroma_host == "discovered-host"
                    assert config.chroma_port == 7777
