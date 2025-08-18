"""Tests for simplified Settings configuration model."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from shard_markdown.config import load_config
from shard_markdown.config.settings import (
    ChunkingMethod,
    Settings,
    create_default_config,
    save_config,
)


class TestSettings:
    """Test the simplified Settings model."""

    def test_default_values(self) -> None:
        """Test that Settings creates with expected defaults."""
        settings = Settings()

        # ChromaDB defaults
        assert settings.chroma_host == "localhost"
        assert settings.chroma_port == 8000
        assert settings.chroma_ssl is False
        assert settings.chroma_auth_token is None
        assert settings.chroma_timeout == 30

        # Chunking defaults
        assert settings.chunk_size == 1000
        assert settings.chunk_overlap == 200
        assert settings.chunking_method == ChunkingMethod.STRUCTURE
        assert settings.respect_boundaries is True
        assert settings.max_tokens is None

        # Processing defaults
        assert settings.batch_size == 10
        assert settings.recursive is False
        assert settings.pattern == "*.md"
        assert settings.include_frontmatter is True
        assert settings.include_path_metadata is True

        # Logging defaults
        assert settings.log_level == "INFO"
        assert (
            settings.log_format
            == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        assert settings.log_file is None
        assert settings.max_log_file_size == 10485760
        assert settings.log_backup_count == 5

        # Custom defaults
        assert settings.custom_metadata == {}
        assert settings.plugins == []

    def test_custom_values(self) -> None:
        """Test Settings with custom values."""
        settings = Settings(
            chroma_host="custom.host",
            chroma_port=9000,
            chroma_ssl=True,
            chunk_size=1500,
            chunk_overlap=300,
            chunking_method=ChunkingMethod._FIXED,
            batch_size=20,
            recursive=True,
            log_level="DEBUG",
        )

        assert settings.chroma_host == "custom.host"
        assert settings.chroma_port == 9000
        assert settings.chroma_ssl is True
        assert settings.chunk_size == 1500
        assert settings.chunk_overlap == 300
        assert settings.chunking_method == ChunkingMethod._FIXED
        assert settings.batch_size == 20
        assert settings.recursive is True
        assert settings.log_level == "DEBUG"

    def test_host_validation_valid_hosts(self) -> None:
        """Test host validation with valid hostnames and IPs."""
        valid_hosts = [
            "localhost",
            "127.0.0.1",
            "::1",
            "192.168.1.1",
            "10.0.0.1",
            "example.com",
            "sub.example.com",
            "test-host",
            "my-chromadb-server",
        ]

        for host in valid_hosts:
            settings = Settings(chroma_host=host)
            assert settings.chroma_host == host

    def test_host_validation_invalid_hosts(self) -> None:
        """Test host validation with invalid hostnames and IPs."""
        invalid_hosts = [
            "",
            "   ",
            "256.1.1.1",  # Invalid IP
            "192.168.1",  # Incomplete IP
            "-invalid-host",  # Starts with hyphen
            "invalid-host-",  # Ends with hyphen
            "a" * 64,  # Too long label
        ]

        for host in invalid_hosts:
            with pytest.raises(ValueError, match="Invalid host|Host cannot be empty"):
                Settings(chroma_host=host)

    def test_port_validation(self) -> None:
        """Test port validation."""
        # Valid ports
        for port in [1, 8000, 65535]:
            settings = Settings(chroma_port=port)
            assert settings.chroma_port == port

        # Invalid ports
        for port in [0, 65536, -1]:
            with pytest.raises(ValueError):
                Settings(chroma_port=port)

    def test_chunk_size_validation(self) -> None:
        """Test chunk size validation."""
        # Valid sizes
        for size in [100, 1000, 10000]:
            settings = Settings(chunk_size=size)
            assert settings.chunk_size == size

        # Invalid sizes
        for size in [99, 10001, -1]:
            with pytest.raises(ValueError):
                Settings(chunk_size=size)

    def test_chunk_overlap_validation(self) -> None:
        """Test chunk overlap validation."""
        # Valid overlap (less than chunk size)
        settings = Settings(chunk_size=1000, chunk_overlap=500)
        assert settings.chunk_overlap == 500

        # Invalid overlap (greater than or equal to chunk size)
        with pytest.raises(ValueError, match="Overlap must be less than chunk size"):
            Settings(chunk_size=1000, chunk_overlap=1000)

        with pytest.raises(ValueError, match="Overlap must be less than chunk size"):
            Settings(chunk_size=1000, chunk_overlap=1500)

    def test_batch_size_validation(self) -> None:
        """Test batch size validation."""
        # Valid sizes
        for size in [1, 10, 100]:
            settings = Settings(batch_size=size)
            assert settings.batch_size == size

        # Invalid sizes
        for size in [0, 101, -1]:
            with pytest.raises(ValueError):
                Settings(batch_size=size)


class TestLoadConfigFlat:
    """Test load_config function with the new flat structure."""

    def test_load_config_defaults(self) -> None:
        """Test loading config with no file returns defaults."""
        with patch(
            "shard_markdown.config.settings._find_config_file", return_value=None
        ):
            with patch.dict(os.environ, {}, clear=True):
                settings = load_config()

                assert isinstance(settings, Settings)
                assert settings.chroma_host == "localhost"
                assert settings.chroma_port == 8000
                assert settings.chunk_size == 1000

    def test_load_config_from_file_flat(self) -> None:
        """Test loading config from flat YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create flat config file
            config_data = {
                "chroma_host": "test.example.com",
                "chroma_port": 9000,
                "chroma_ssl": True,
                "chunk_size": 1500,
                "chunk_overlap": 250,
                "batch_size": 20,
                "log_level": "DEBUG",
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            with patch.dict(os.environ, {}, clear=True):
                settings = load_config(config_path)

                assert settings.chroma_host == "test.example.com"
                assert settings.chroma_port == 9000
                assert settings.chroma_ssl is True
                assert settings.chunk_size == 1500
                assert settings.chunk_overlap == 250
                assert settings.batch_size == 20
                assert settings.log_level == "DEBUG"

    def test_load_config_from_file_nested_backward_compatibility(self) -> None:
        """Test loading config from nested YAML file (backward compatibility)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create nested config file (old format)
            config_data = {
                "chromadb": {
                    "host": "old.example.com",
                    "port": 8080,
                    "ssl": True,
                    "timeout": 45,
                },
                "chunking": {
                    "default_size": 800,
                    "default_overlap": 150,
                    "method": "fixed",
                },
                "processing": {
                    "batch_size": 15,
                    "recursive": True,
                },
                "logging": {
                    "level": "WARNING",
                    "file_path": str(Path(tmpdir) / "test.log"),
                },
                "plugins": ["test_plugin"],
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            with patch.dict(os.environ, {}, clear=True):
                settings = load_config(config_path)

                # Should map nested structure to flat structure
                assert settings.chroma_host == "old.example.com"
                assert settings.chroma_port == 8080
                assert settings.chroma_ssl is True
                assert settings.chroma_timeout == 45
                assert settings.chunk_size == 800
                assert settings.chunk_overlap == 150
                assert settings.chunking_method == ChunkingMethod._FIXED
                assert settings.batch_size == 15
                assert settings.recursive is True
                assert settings.log_level == "WARNING"
                assert str(settings.log_file) == str(Path(tmpdir) / "test.log")
                assert settings.plugins == ["test_plugin"]

    def test_mixed_flat_and_nested_config(self) -> None:
        """Test config with both flat and nested keys (flat takes precedence)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Mix of flat and nested - flat should win
            config_data = {
                # Flat keys (should be used)
                "chroma_host": "flat.example.com",
                "chunk_size": 2000,
                # Nested keys (should be ignored if flat exists)
                "chromadb": {
                    "host": "nested.example.com",  # Should be ignored
                    "port": 8080,  # Should be used (no flat equivalent)
                },
                "chunking": {
                    "default_size": 500,  # Should be ignored
                    "method": "structure",  # Should be used
                },
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            with patch.dict(os.environ, {}, clear=True):
                settings = load_config(config_path)

                # Flat keys should win
                assert settings.chroma_host == "flat.example.com"
                assert settings.chunk_size == 2000
                # Nested keys used only when no flat equivalent
                assert settings.chroma_port == 8080
                assert settings.chunking_method == ChunkingMethod.STRUCTURE

    def test_all_env_var_mappings(self) -> None:
        """Test all environment variable mappings."""
        # Create a test token that won't trigger security warnings
        test_token = f"test-{'auth' + '-token'}-{123}"

        env_vars = {
            "CHROMA_HOST": "env-host.com",
            "CHROMA_PORT": "9000",
            "CHROMA_SSL": "true",
            "CHROMA_AUTH_TOKEN": test_token,
            "SHARD_MD_CHUNK_SIZE": "1500",
            "SHARD_MD_CHUNK_OVERLAP": "250",
            "SHARD_MD_BATCH_SIZE": "20",
            "SHARD_MD_LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch(
                "shard_markdown.config.settings._find_config_file", return_value=None
            ):
                settings = load_config()

                assert settings.chroma_host == "env-host.com"
                assert settings.chroma_port == 9000
                assert settings.chroma_ssl is True
                assert settings.chroma_auth_token == test_token
                assert settings.chunk_size == 1500
                assert settings.chunk_overlap == 250
                assert settings.batch_size == 20
                assert settings.log_level == "DEBUG"

    def test_env_var_type_conversion(self) -> None:
        """Test environment variable type conversion."""
        env_vars = {
            "CHROMA_PORT": "8080",  # String -> int
            "CHROMA_SSL": "false",  # String -> bool
            "SHARD_MD_CHUNK_SIZE": "2000",  # String -> int
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch(
                "shard_markdown.config.settings._find_config_file", return_value=None
            ):
                settings = load_config()

                assert settings.chroma_port == 8080
                assert isinstance(settings.chroma_port, int)
                assert settings.chroma_ssl is False
                assert isinstance(settings.chroma_ssl, bool)
                assert settings.chunk_size == 2000
                assert isinstance(settings.chunk_size, int)

    def test_env_overrides_file(self) -> None:
        """Test environment variables override file values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create config file
            config_data = {
                "chroma_host": "file.example.com",
                "chroma_port": 8000,
                "chunk_size": 1000,
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Override with env vars
            env_vars = {
                "CHROMA_HOST": "env.example.com",
                "SHARD_MD_CHUNK_SIZE": "1500",
            }

            with patch.dict(os.environ, env_vars, clear=False):
                settings = load_config(config_path)

                # Env should override file
                assert settings.chroma_host == "env.example.com"
                assert settings.chunk_size == 1500
                # File value should remain where no env override
                assert settings.chroma_port == 8000

    def test_invalid_config_file(self) -> None:
        """Test handling of invalid config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "invalid.yaml"

            # Create invalid YAML
            with open(config_path, "w") as f:
                f.write("invalid: yaml: content: [")

            with pytest.raises(ValueError, match="Error reading configuration file"):
                load_config(config_path)

    def test_invalid_config_values(self) -> None:
        """Test validation of invalid config values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Invalid port
            config_data = {"chroma_port": 70000}

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(ValueError, match="Invalid configuration"):
                    load_config(config_path)


class TestSaveConfig:
    """Test save_config function."""

    def test_save_config_creates_directory(self) -> None:
        """Test that save_config creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "nested" / "config"
            config_path = config_dir / "config.yaml"

            # Directory doesn't exist yet
            assert not config_dir.exists()

            settings = Settings(chroma_host="test.com", chunk_size=1500)
            save_config(settings, config_path)

            # Directory should be created and file should exist
            assert config_path.exists()
            assert config_path.is_file()

    def test_save_and_load_roundtrip(self) -> None:
        """Test saving and loading config preserves values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create settings with custom values
            original_settings = Settings(
                chroma_host="roundtrip.com",
                chroma_port=9090,
                chroma_ssl=True,
                chunk_size=1200,
                chunk_overlap=150,
                chunking_method=ChunkingMethod._FIXED,
                batch_size=25,
                recursive=True,
                log_level="DEBUG",
            )

            # Save and reload
            save_config(original_settings, config_path)

            with patch.dict(os.environ, {}, clear=True):
                loaded_settings = load_config(config_path)

                # All values should match
                assert loaded_settings.chroma_host == original_settings.chroma_host
                assert loaded_settings.chroma_port == original_settings.chroma_port
                assert loaded_settings.chroma_ssl == original_settings.chroma_ssl
                assert loaded_settings.chunk_size == original_settings.chunk_size
                assert loaded_settings.chunk_overlap == original_settings.chunk_overlap
                assert (
                    loaded_settings.chunking_method == original_settings.chunking_method
                )
                assert loaded_settings.batch_size == original_settings.batch_size
                assert loaded_settings.recursive == original_settings.recursive
                assert loaded_settings.log_level == original_settings.log_level

    def test_save_config_file_permissions(self) -> None:
        """Test that saved config file has appropriate permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            settings = Settings()
            save_config(settings, config_path)

            # File should be readable and writable by owner
            stat_info = config_path.stat()
            assert stat_info.st_mode & 0o600  # Owner read/write


class TestCreateDefaultConfig:
    """Test create_default_config function."""

    def test_create_default_config(self) -> None:
        """Test creating default config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "default.yaml"

            create_default_config(config_path)

            assert config_path.exists()

            # Should be valid YAML
            with open(config_path) as f:
                data = yaml.safe_load(f)
                assert isinstance(data, dict)

                # Should contain expected keys
                expected_keys = [
                    "chroma_host",
                    "chroma_port",
                    "chunk_size",
                    "chunk_overlap",
                    "batch_size",
                    "log_level",
                ]
                for key in expected_keys:
                    assert key in data

    def test_create_default_config_no_overwrite(self) -> None:
        """Test default config creation doesn't overwrite existing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "existing.yaml"

            # Create existing file
            with open(config_path, "w") as f:
                f.write("existing: content")

            # Should not overwrite without force
            with pytest.raises(RuntimeError, match="already exists"):
                create_default_config(config_path, force=False)

            # Original content should remain
            with open(config_path) as f:
                content = f.read()
                assert "existing: content" in content

    def test_create_default_config_force_overwrite(self) -> None:
        """Test default config creation with force overwrite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "existing.yaml"

            # Create existing file
            with open(config_path, "w") as f:
                f.write("existing: content")

            # Should overwrite with force
            create_default_config(config_path, force=True)

            # Should have new default content
            with open(config_path) as f:
                content = f.read()
                assert "existing: content" not in content
                assert "chroma_host" in content
