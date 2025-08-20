"""Unit tests for consolidated configuration system."""

import pytest
from pydantic import ValidationError

from shard_markdown.config.settings import (
    ChromaDBParams,
    ChunkingParams,
    Settings,
)


class TestSettings:
    """Test consolidated Settings configuration."""

    def test_default_settings(self) -> None:
        """Test default settings creation."""
        settings = Settings()

        assert settings.chroma_host == "localhost"
        assert settings.chroma_port == 8000
        assert settings.chunk_size == 1000
        assert settings.overlap == 100
        assert settings.log_level == "INFO"
        assert settings.output_format == "table"

    def test_custom_settings(self) -> None:
        """Test custom settings creation."""
        settings = Settings(
            chroma_host="example.com",
            chroma_port=9000,
            chunk_size=500,
            overlap=50,
            log_level="DEBUG",
            output_format="json",
        )

        assert settings.chroma_host == "example.com"
        assert settings.chroma_port == 9000
        assert settings.chunk_size == 500
        assert settings.overlap == 50
        assert settings.log_level == "DEBUG"
        assert settings.output_format == "json"

    def test_port_validation(self) -> None:
        """Test port validation."""
        # Valid port
        settings = Settings(chroma_port=8080)
        assert settings.chroma_port == 8080

        # Invalid ports
        with pytest.raises(ValidationError):
            Settings(chroma_port=0)

        with pytest.raises(ValidationError):
            Settings(chroma_port=70000)

    def test_chunk_size_validation(self) -> None:
        """Test chunk size validation."""
        # Valid chunk size
        settings = Settings(chunk_size=2000)
        assert settings.chunk_size == 2000

        # Invalid chunk sizes
        with pytest.raises(ValidationError):
            Settings(chunk_size=50)  # Too small

        with pytest.raises(ValidationError):
            Settings(chunk_size=20000)  # Too large

    def test_overlap_validation(self) -> None:
        """Test overlap validation."""
        # Valid overlap
        settings = Settings(chunk_size=1000, overlap=200)
        assert settings.overlap == 200

        # Overlap larger than chunk size
        with pytest.raises(ValidationError):
            Settings(chunk_size=1000, overlap=1200)

    def test_host_validation(self) -> None:
        """Test host validation."""
        # Valid hosts
        Settings(chroma_host="localhost")
        Settings(chroma_host="127.0.0.1")
        Settings(chroma_host="example.com")

        # Invalid hosts
        with pytest.raises(ValidationError):
            Settings(chroma_host="")

        with pytest.raises(ValidationError):
            Settings(chroma_host="   ")

    def test_get_chunking_params(self) -> None:
        """Test chunking params extraction."""
        settings = Settings(chunk_size=500, overlap=50)
        params = settings.get_chunking_params()

        assert isinstance(params, ChunkingParams)
        assert params.chunk_size == 500
        assert params.overlap == 50
        assert params.method == "structure"
        assert params.respect_boundaries is True
        assert params.max_tokens is None

    def test_get_chromadb_params(self) -> None:
        """Test ChromaDB params extraction."""
        settings = Settings(chroma_host="test.com", chroma_port=9000)
        params = settings.get_chromadb_params()

        assert isinstance(params, ChromaDBParams)
        assert params.host == "test.com"
        assert params.port == 9000
        assert params.ssl is False
        assert params.auth_token is None
        assert params.timeout == 30


class TestChunkingParams:
    """Test ChunkingParams data container."""

    def test_creation(self) -> None:
        """Test ChunkingParams creation."""
        params = ChunkingParams(
            chunk_size=800,
            overlap=80,
            method="fixed",
            respect_boundaries=False,
            max_tokens=1000,
        )

        assert params.chunk_size == 800
        assert params.overlap == 80
        assert params.method == "fixed"
        assert params.respect_boundaries is False
        assert params.max_tokens == 1000

    def test_defaults(self) -> None:
        """Test ChunkingParams defaults."""
        params = ChunkingParams(chunk_size=1000, overlap=100)

        assert params.method == "structure"
        assert params.respect_boundaries is True
        assert params.max_tokens is None


class TestChromaDBParams:
    """Test ChromaDBParams data container."""

    def test_creation(self) -> None:
        """Test ChromaDBParams creation."""
        params = ChromaDBParams(
            host="myhost",
            port=8001,
            ssl=True,
            auth_token="token123",  # noqa: S106
            timeout=60,
        )

        assert params.host == "myhost"
        assert params.port == 8001
        assert params.ssl is True
        assert params.auth_token == "token123"  # noqa: S105
        assert params.timeout == 60

    def test_defaults(self) -> None:
        """Test ChromaDBParams defaults."""
        params = ChromaDBParams(host="localhost", port=8000)

        assert params.ssl is False
        assert params.auth_token is None
        assert params.timeout == 30


class TestConfigIntegration:
    """Test configuration integration scenarios."""

    def test_settings_to_params_conversion(self) -> None:
        """Test conversion from Settings to parameter objects."""
        settings = Settings(
            chroma_host="integration.test",
            chroma_port=8888,
            chunk_size=1500,
            overlap=150,
        )

        # Test ChromaDB params
        db_params = settings.get_chromadb_params()
        assert db_params.host == "integration.test"
        assert db_params.port == 8888

        # Test chunking params
        chunk_params = settings.get_chunking_params()
        assert chunk_params.chunk_size == 1500
        assert chunk_params.overlap == 150

    def test_env_var_compatible_structure(self) -> None:
        """Test that settings support environment variable mappings."""
        # This tests that the flat structure supports env vars
        settings = Settings(
            chroma_host="env.test",  # Maps from CHROMA_HOST
            chroma_port=9999,  # Maps from CHROMA_PORT
            chunk_size=2000,  # Maps from SHARD_MD_CHUNK_SIZE
            overlap=200,  # Maps from SHARD_MD_CHUNK_OVERLAP
            log_level="DEBUG",  # Maps from SHARD_MD_LOG_LEVEL
            output_format="json",  # Maps from SHARD_MD_OUTPUT_FORMAT
        )

        assert settings.chroma_host == "env.test"
        assert settings.chroma_port == 9999
        assert settings.chunk_size == 2000
        assert settings.overlap == 200
        assert settings.log_level == "DEBUG"
        assert settings.output_format == "json"
