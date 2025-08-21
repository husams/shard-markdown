"""Unit tests for configuration settings."""

import pytest
from pydantic import ValidationError

from shard_markdown.config import Settings


class TestSettings:
    """Test Settings configuration validation."""

    def test_valid_config(self) -> None:
        """Test valid configuration."""
        config = Settings(
            chroma_host="localhost",
            chroma_port=8000,
            chroma_ssl=False,
            chroma_timeout=30,
            chunk_size=1000,
            chunk_overlap=200,
            chunk_method="structure",
        )

        assert config.chroma_host == "localhost"
        assert config.chroma_port == 8000
        assert config.chroma_ssl is False
        assert config.chroma_timeout == 30
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.chunk_method == "structure"

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = Settings()

        # ChromaDB defaults
        assert config.chroma_host == "localhost"
        assert config.chroma_port == 8000
        assert config.chroma_ssl is False
        assert config.chroma_timeout == 30
        assert config.chroma_auth_token is None

        # Chunking defaults
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.chunk_method == "structure"
        assert config.chunk_respect_boundaries is True
        assert config.chunk_max_tokens is None

        # Processing defaults
        assert config.process_batch_size == 10
        assert config.process_recursive is False
        assert config.process_pattern == "*.md"
        assert config.process_include_frontmatter is True
        assert config.process_include_path_metadata is True

        # Logging defaults
        assert config.log_level == "INFO"
        assert config.log_file is None
        assert config.log_max_file_size == 10485760
        assert config.log_backup_count == 5

        # Output defaults
        assert config.output_format == "table"

    def test_port_validation(self) -> None:
        """Test port range validation."""
        # Valid ports
        valid_ports = [1, 8000, 65535]
        for port in valid_ports:
            config = Settings(chroma_port=port)
            assert config.chroma_port == port

        # Invalid ports should raise validation error
        invalid_ports = [0, -1, 65536, 70000]
        for port in invalid_ports:
            with pytest.raises(ValidationError):
                Settings(chroma_port=port)

    def test_host_validation(self) -> None:
        """Test host validation."""
        # Valid hosts
        valid_hosts = ["localhost", "127.0.0.1", "example.com", "db.internal"]
        for host in valid_hosts:
            config = Settings(chroma_host=host)
            assert config.chroma_host == host

        # Empty host should raise validation error
        with pytest.raises(ValidationError):
            Settings(chroma_host="")

    def test_timeout_validation(self) -> None:
        """Test timeout validation."""
        # Valid timeouts
        valid_timeouts = [1, 30, 60, 300]
        for timeout in valid_timeouts:
            config = Settings(chroma_timeout=timeout)
            assert config.chroma_timeout == timeout

        # Invalid timeouts
        invalid_timeouts = [0, -1]
        for timeout in invalid_timeouts:
            with pytest.raises(ValidationError):
                Settings(chroma_timeout=timeout)

    def test_chunk_size_validation(self) -> None:
        """Test chunk size validation."""
        # Valid chunk sizes
        valid_sizes = [100, 1000, 10000]
        for size in valid_sizes:
            config = Settings(chunk_size=size)
            assert config.chunk_size == size

        # Invalid chunk sizes
        invalid_sizes = [50, 0, -100, 10001, 20000]
        for size in invalid_sizes:
            with pytest.raises(ValidationError):
                Settings(chunk_size=size)

    def test_chunk_overlap_validation(self) -> None:
        """Test chunk overlap validation."""
        # Valid overlaps
        valid_overlaps = [0, 200, 500, 999]
        for overlap in valid_overlaps:
            config = Settings(chunk_overlap=overlap)
            assert config.chunk_overlap == overlap

        # Invalid overlaps
        invalid_overlaps = [-1, 1001, 2000]
        for overlap in invalid_overlaps:
            with pytest.raises(ValidationError):
                Settings(chunk_overlap=overlap)

    def test_overlap_less_than_chunk_size(self) -> None:
        """Test that overlap must be less than chunk size."""
        # Valid: overlap < chunk_size
        config = Settings(chunk_size=1000, chunk_overlap=200)
        assert config.chunk_overlap == 200

        # Invalid: overlap >= chunk_size
        with pytest.raises(ValidationError):
            Settings(chunk_size=1000, chunk_overlap=1000)

        with pytest.raises(ValidationError):
            Settings(chunk_size=1000, chunk_overlap=1500)

    def test_batch_size_validation(self) -> None:
        """Test batch size validation."""
        # Valid batch sizes
        valid_sizes = [1, 10, 50, 100]
        for size in valid_sizes:
            config = Settings(process_batch_size=size)
            assert config.process_batch_size == size

        # Invalid batch sizes
        invalid_sizes = [0, -1, 101, 200]
        for size in invalid_sizes:
            with pytest.raises(ValidationError):
                Settings(process_batch_size=size)

    def test_custom_metadata(self) -> None:
        """Test custom metadata field."""
        metadata = {"project": "test", "version": "1.0"}
        config = Settings(custom_metadata=metadata)
        assert config.custom_metadata == metadata

    def test_plugins_list(self) -> None:
        """Test plugins list field."""
        plugins = ["plugin1", "plugin2"]
        config = Settings(plugins=plugins)
        assert config.plugins == plugins
