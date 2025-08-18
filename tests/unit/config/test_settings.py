"""Minimal tests for configuration settings."""

import pytest
from pydantic import ValidationError

from shard_markdown.config.settings import (
    AppConfig,
    ChromaDBConfig,
    ChunkingConfig,
    ChunkingMethod,
    LoggingConfig,
    load_config,
)


class TestChromaDBConfig:
    """Test ChromaDB configuration validation."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ChromaDBConfig()
        assert config.host == "localhost"
        assert config.port == 8000
        assert config.timeout == 30

    def test_port_validation(self) -> None:
        """Test port range validation."""
        # Valid ports
        ChromaDBConfig(port=8000)

        # Invalid ports should raise validation error
        with pytest.raises(ValidationError):
            ChromaDBConfig(port=0)
        with pytest.raises(ValidationError):
            ChromaDBConfig(port=65536)


class TestChunkingConfig:
    """Test chunking configuration validation."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ChunkingConfig()
        assert config.default_size == 1000
        assert config.default_overlap == 200
        assert config.method == ChunkingMethod.STRUCTURE

    def test_size_validation(self) -> None:
        """Test chunk size validation."""
        # Valid sizes
        ChunkingConfig(default_size=500)

        # Invalid sizes
        with pytest.raises(ValidationError):
            ChunkingConfig(default_size=50)  # Too small
        with pytest.raises(ValidationError):
            ChunkingConfig(default_size=15000)  # Too large


class TestAppConfig:
    """Test main application configuration."""

    def test_default_app_config(self) -> None:
        """Test default application configuration."""
        config = AppConfig()

        assert isinstance(config.chromadb, ChromaDBConfig)
        assert isinstance(config.chunking, ChunkingConfig)
        assert isinstance(config.logging, LoggingConfig)

    def test_load_config_returns_valid_config(self) -> None:
        """Test loading configuration returns valid config object."""
        config = load_config()

        # Just test that we get a valid config object with expected types
        assert isinstance(config, AppConfig)
        assert isinstance(config.chromadb, ChromaDBConfig)
        assert isinstance(config.chunking, ChunkingConfig)
        assert config.chunking.default_size > 0
