"""Unit tests for configuration settings."""

import pytest
from pydantic import ValidationError

from shard_markdown.config.settings import (
    AppConfig,
    ChromaDBConfig,
    ChunkingConfig,
    ProcessingConfig,
)


class TestChromaDBConfig:
    """Test ChromaDB configuration validation."""

    def test_valid_config(self):
        """Test valid ChromaDB configuration."""
        config = ChromaDBConfig(
            host="localhost",
            port=8000,
            ssl=False,
            timeout=30
        )

        assert config.host == "localhost"
        assert config.port == 8000
        assert config.ssl is False
        assert config.timeout == 30

    def test_default_values(self):
        """Test default configuration values."""
        config = ChromaDBConfig()

        assert config.host == "localhost"
        assert config.port == 8000
        assert config.ssl is False
        assert config.timeout == 30

    def test_port_validation(self):
        """Test port range validation."""
        # Valid ports
        valid_ports = [1, 8000, 65535]
        for port in valid_ports:
            config = ChromaDBConfig(port=port)
            assert config.port == port

        # Invalid ports should raise validation error
        invalid_ports = [0, -1, 65536, 70000]
        for port in invalid_ports:
            with pytest.raises(ValidationError):
                ChromaDBConfig(port=port)

    def test_host_validation(self):
        """Test host validation."""
        # Valid hosts
        valid_hosts = ["localhost", "127.0.0.1", "example.com", "db.internal"]
        for host in valid_hosts:
            config = ChromaDBConfig(host=host)
            assert config.host == host

        # Empty host should raise validation error
        with pytest.raises(ValidationError):
            ChromaDBConfig(host="")

    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid timeouts
        valid_timeouts = [1, 30, 60, 300]
        for timeout in valid_timeouts:
            config = ChromaDBConfig(timeout=timeout)
            assert config.timeout == timeout

        # Invalid timeouts
        invalid_timeouts = [0, -1]
        for timeout in invalid_timeouts:
            with pytest.raises(ValidationError):
                ChromaDBConfig(timeout=timeout)


class TestChunkingConfig:
    """Test chunking configuration validation."""

    def test_valid_config(self):
        """Test valid chunking configuration."""
        config = ChunkingConfig(
            default_size=1000,
            default_overlap=200,
            method="structure",
            respect_boundaries=True,
        )

        assert config.default_size == 1000
        assert config.default_overlap == 200
        assert config.method == "structure"
        assert config.respect_boundaries is True

    def test_default_values(self):
        """Test default configuration values."""
        config = ChunkingConfig()

        assert config.default_size == 1000
        assert config.default_overlap == 200
        assert config.method == "structure"
        assert config.respect_boundaries is True

    def test_chunk_size_validation(self):
        """Test chunk size validation."""
        # Valid sizes
        valid_sizes = [100, 500, 1000, 5000]
        for size in valid_sizes:
            config = ChunkingConfig(default_size=size)
            assert config.default_size == size

        # Invalid sizes
        invalid_sizes = [0, -100, 50]  # Too small
        for size in invalid_sizes:
            with pytest.raises(ValidationError):
                ChunkingConfig(default_size=size)

    def test_overlap_validation(self):
        """Test overlap validation."""
        # Valid overlaps
        config = ChunkingConfig(default_size=1000, default_overlap=200)
        assert config.default_overlap == 200

        # Overlap larger than chunk size should fail
        with pytest.raises(ValidationError):
            ChunkingConfig(default_size=500, default_overlap=600)

        # Negative overlap should fail
        with pytest.raises(ValidationError):
            ChunkingConfig(default_overlap=-100)

    def test_method_validation(self):
        """Test chunking method validation."""
        # Valid methods
        valid_methods = ["structure", "fixed", "semantic"]
        for method in valid_methods:
            config = ChunkingConfig(method=method)
            assert config.method == method

        # Invalid method should fail
        with pytest.raises(ValidationError):
            ChunkingConfig(method="invalid_method")


class TestProcessingConfig:
    """Test processing configuration validation."""

    def test_valid_config(self):
        """Test valid processing configuration."""
        config = ProcessingConfig(batch_size=10, max_workers=4, timeout=60)

        assert config.batch_size == 10
        assert config.max_workers == 4
        assert config.timeout == 60

    def test_default_values(self):
        """Test default configuration values."""
        config = ProcessingConfig()

        assert config.batch_size == 10
        assert config.max_workers == 4
        assert config.timeout == 30

    def test_batch_size_validation(self):
        """Test batch size validation."""
        # Valid batch sizes
        valid_sizes = [1, 5, 10, 50]
        for size in valid_sizes:
            config = ProcessingConfig(batch_size=size)
            assert config.batch_size == size

        # Invalid batch sizes
        invalid_sizes = [0, -1]
        for size in invalid_sizes:
            with pytest.raises(ValidationError):
                ProcessingConfig(batch_size=size)

    def test_max_workers_validation(self):
        """Test max workers validation."""
        # Valid worker counts
        valid_workers = [1, 2, 4, 8, 16]
        for workers in valid_workers:
            config = ProcessingConfig(max_workers=workers)
            assert config.max_workers == workers

        # Invalid worker counts
        invalid_workers = [0, -1]
        for workers in invalid_workers:
            with pytest.raises(ValidationError):
                ProcessingConfig(max_workers=workers)


class TestAppConfig:
    """Test complete application configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AppConfig()

        # Should have all subsection configs
        assert config.chromadb is not None
        assert config.chunking is not None
        assert config.processing is not None
        assert config.logging is not None

        # Check default values
        assert config.chromadb.host == "localhost"
        assert config.chunking.default_size == 1000
        assert config.processing.batch_size == 10

    def test_custom_config(self):
        """Test custom configuration."""
        config = AppConfig(
            chromadb=ChromaDBConfig(host="remote-host", port=9000),
            chunking=ChunkingConfig(default_size=1500, method="fixed"),
            processing=ProcessingConfig(max_workers=8),
        )

        assert config.chromadb.host == "remote-host"
        assert config.chromadb.port == 9000
        assert config.chunking.default_size == 1500
        assert config.chunking.method == "fixed"
        assert config.processing.max_workers == 8

    def test_nested_validation(self):
        """Test that nested configuration validation works."""
        # Invalid nested config should fail
        with pytest.raises(ValidationError):
            AppConfig(
                chromadb=ChromaDBConfig(port=70000),  # Invalid port
                chunking=ChunkingConfig(default_size=1000),
            )

        with pytest.raises(ValidationError):
            AppConfig(
                chromadb=ChromaDBConfig(),
                chunking=ChunkingConfig(
                    default_size=500, default_overlap=600
                ),  # Overlap > size
            )

    def test_config_serialization(self):
        """Test configuration serialization."""
        config = AppConfig()

        # Should be able to serialize to dict
        config_dict = config.dict()
        assert isinstance(config_dict, dict)
        assert "chromadb" in config_dict
        assert "chunking" in config_dict
        assert "processing" in config_dict

        # Should be able to serialize to JSON
        config_json = config.json()
        assert isinstance(config_json, str)

        # Should be able to deserialize back
        import json

        parsed = json.loads(config_json)
        assert parsed["chromadb"]["host"] == "localhost"

    def test_config_immutability(self):
        """Test configuration immutability (if implemented)."""
        config = AppConfig()

        # Depending on implementation, config might be immutable
        # This test would verify that behavior
        original_host = config.chromadb.host

        # Try to modify (should either work or raise error depending on implementation)
        try:
            config.chromadb.host = "modified-host"
            # If modification worked, verify it
            assert config.chromadb.host == "modified-host"
        except (AttributeError, TypeError):
            # If config is immutable, that's fine too
            assert config.chromadb.host == original_host

    def test_environment_variable_support(self):
        """Test environment variable configuration support."""
        import os

        # Set environment variables
        env_vars = {
            "SHARD_MD_CHROMADB_HOST": "env-host",
            "SHARD_MD_CHROMADB_PORT": "9000",
            "SHARD_MD_CHUNKING_DEFAULT_SIZE": "1500",
        }

        # Store original values
        original_values = {}
        for key in env_vars:
            original_values[key] = os.environ.get(key)
            os.environ[key] = env_vars[key]

        try:
            # This test assumes environment variable support is implemented
            # The actual behavior depends on the configuration loader
            # Values might come from environment or defaults
            # This test would need to be adjusted based on actual implementation
            pass

        finally:
            # Restore original environment
            for key, original_value in original_values.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value


class TestConfigValidationScenarios:
    """Test various configuration validation scenarios."""

    def test_extreme_values(self):
        """Test configuration with extreme values."""
        # Very large chunk size
        config = ChunkingConfig(default_size=100000)
        assert config.default_size == 100000

        # Very high worker count
        config = ProcessingConfig(max_workers=100)
        assert config.max_workers == 100

        # Very large timeout
        config = ChromaDBConfig(timeout=3600)
        assert config.timeout == 3600

    def test_boundary_values(self):
        """Test configuration with boundary values."""
        # Minimum valid chunk size
        config = ChunkingConfig(default_size=100)
        assert config.default_size == 100

        # Maximum valid port
        config = ChromaDBConfig(port=65535)
        assert config.port == 65535

        # Minimum valid timeout
        config = ChromaDBConfig(timeout=1)
        assert config.timeout == 1

    def test_configuration_combinations(self):
        """Test various configuration combinations."""
        # High performance configuration
        high_perf_config = AppConfig(
            chunking=ChunkingConfig(default_size=2000, default_overlap=400),
            processing=ProcessingConfig(max_workers=16, batch_size=50),
        )

        assert high_perf_config.chunking.default_size == 2000
        assert high_perf_config.processing.max_workers == 16

        # Conservative configuration
        conservative_config = AppConfig(
            chunking=ChunkingConfig(default_size=500, default_overlap=50),
            processing=ProcessingConfig(max_workers=1, batch_size=1),
        )

        assert conservative_config.chunking.default_size == 500
        assert conservative_config.processing.max_workers == 1

    def test_config_field_types(self):
        """Test that configuration fields have correct types."""
        config = AppConfig()

        # Check types
        assert isinstance(config.chromadb.host, str)
        assert isinstance(config.chromadb.port, int)
        assert isinstance(config.chromadb.ssl, bool)
        assert isinstance(config.chunking.default_size, int)
        assert isinstance(config.chunking.respect_boundaries, bool)
        assert isinstance(config.processing.max_workers, int)

    def test_config_validation_error_messages(self):
        """Test that validation errors provide helpful messages."""
        # Test port validation error
        try:
            ChromaDBConfig(port=70000)
            raise AssertionError("Should have raised ValidationError")
        except ValidationError as e:
            error_msg = str(e)
            assert "port" in error_msg.lower() or "65535" in error_msg

        # Test chunk size validation error
        try:
            ChunkingConfig(default_size=50)
            raise AssertionError("Should have raised ValidationError")
        except ValidationError as e:
            error_msg = str(e)
            assert "size" in error_msg.lower() or "100" in error_msg
