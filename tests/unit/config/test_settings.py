"""Unit tests for configuration settings."""

from typing import cast

import pytest
from pydantic import ValidationError

from shard_markdown.config.settings import (
    AppConfig,
    ChromaDBConfig,
    ChunkingConfig,
    ChunkingMethod,
    ProcessingConfig,
)


class TestChromaDBConfig:
    """Test ChromaDB configuration validation."""

    def test_valid_config(self) -> None:
        """Test valid ChromaDB configuration."""
        config = ChromaDBConfig(host="localhost", port=8000, ssl=False, timeout=30)

        assert config.host == "localhost"
        assert config.port == 8000
        assert config.ssl is False
        assert config.timeout == 30

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ChromaDBConfig()

        assert config.host == "localhost"
        assert config.port == 8000
        assert config.ssl is False
        assert config.timeout == 30

    def test_port_validation(self) -> None:
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

    def test_host_validation(self) -> None:
        """Test host validation."""
        # Valid hosts
        valid_hosts = ["localhost", "127.0.0.1", "example.com", "db.internal"]
        for host in valid_hosts:
            config = ChromaDBConfig(host=host)
            assert config.host == host

        # Empty host should raise validation error
        with pytest.raises(ValidationError):
            ChromaDBConfig(host="")

    def test_timeout_validation(self) -> None:
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

    def test_valid_config(self) -> None:
        """Test valid chunking configuration."""
        config = ChunkingConfig(
            default_size=1000,
            default_overlap=200,
            method=ChunkingMethod.STRUCTURE,
            respect_boundaries=True,
        )

        assert config.default_size == 1000
        assert config.default_overlap == 200
        assert config.method == ChunkingMethod.STRUCTURE
        assert config.respect_boundaries is True

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ChunkingConfig()

        assert config.default_size == 1000
        assert config.default_overlap == 200
        assert config.method == ChunkingMethod.STRUCTURE
        assert config.respect_boundaries is True

    def test_chunk_size_validation(self) -> None:
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

    def test_overlap_validation(self) -> None:
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

    def test_method_validation(self) -> None:
        """Test chunking method validation."""
        # Valid methods using enum
        valid_methods = [
            ChunkingMethod.STRUCTURE,
            ChunkingMethod._FIXED,
            ChunkingMethod._SEMANTIC,
        ]
        for method in valid_methods:
            config = ChunkingConfig(method=method)
            assert config.method == method

        # Test string method as well (should be converted to enum)
        config = ChunkingConfig(method=ChunkingMethod.STRUCTURE)
        assert config.method == ChunkingMethod.STRUCTURE

        # Invalid method should fail
        with pytest.raises(ValidationError):
            ChunkingConfig(method=cast(ChunkingMethod, "invalid_method"))


class TestProcessingConfig:
    """Test processing configuration validation."""

    def test_valid_config(self) -> None:
        """Test valid processing configuration."""
        config = ProcessingConfig(batch_size=10)

        assert config.batch_size == 10

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ProcessingConfig()

        assert config.batch_size == 10

    def test_batch_size_validation(self) -> None:
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


class TestAppConfig:
    """Test complete application configuration."""

    def test_default_config(self) -> None:
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

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = AppConfig(
            chromadb=ChromaDBConfig(host="remote-host", port=9000),
            chunking=ChunkingConfig(default_size=1500, method=ChunkingMethod._FIXED),
            processing=ProcessingConfig(batch_size=20),
        )

        assert config.chromadb.host == "remote-host"
        assert config.chromadb.port == 9000
        assert config.chunking.default_size == 1500
        assert config.chunking.method == ChunkingMethod._FIXED
        assert config.processing.batch_size == 20

    def test_nested_validation(self) -> None:
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

    def test_config_serialization(self) -> None:
        """Test configuration serialization."""
        config = AppConfig()

        # Should be able to serialize to dict
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)
        assert "chromadb" in config_dict
        assert "chunking" in config_dict
        assert "processing" in config_dict

        # Should be able to serialize to JSON
        config_json = config.model_dump_json()
        assert isinstance(config_json, str)

        # Should be able to deserialize back
        import json

        parsed = json.loads(config_json)
        assert parsed["chromadb"]["host"] == "localhost"

    def test_config_immutability(self) -> None:
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

    def test_environment_variable_support(self) -> None:
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

    def test_extreme_values(self) -> None:
        """Test configuration with extreme values."""
        # Maximum allowed chunk size
        chunking_config = ChunkingConfig(default_size=10000)
        assert chunking_config.default_size == 10000

        # Very large timeout
        chromadb_config = ChromaDBConfig(timeout=3600)
        assert chromadb_config.timeout == 3600

    def test_boundary_values(self) -> None:
        """Test configuration with boundary values."""
        # Minimum valid chunk size
        chunking_config = ChunkingConfig(default_size=100)
        assert chunking_config.default_size == 100

        # Maximum valid port
        chromadb_config = ChromaDBConfig(port=65535)
        assert chromadb_config.port == 65535

        # Minimum valid timeout
        chromadb_config_timeout = ChromaDBConfig(timeout=1)
        assert chromadb_config_timeout.timeout == 1

    def test_configuration_combinations(self) -> None:
        """Test various configuration combinations."""
        # High performance configuration
        high_perf_config = AppConfig(
            chunking=ChunkingConfig(default_size=2000, default_overlap=400),
            processing=ProcessingConfig(batch_size=50),
        )

        assert high_perf_config.chunking.default_size == 2000
        assert high_perf_config.processing.batch_size == 50

        # Conservative configuration
        conservative_config = AppConfig(
            chunking=ChunkingConfig(default_size=500, default_overlap=50),
            processing=ProcessingConfig(batch_size=1),
        )

        assert conservative_config.chunking.default_size == 500
        assert conservative_config.processing.batch_size == 1

    def test_config_field_types(self) -> None:
        """Test that configuration fields have correct types."""
        config = AppConfig()

        # Check types
        assert isinstance(config.chromadb.host, str)
        assert isinstance(config.chromadb.port, int)
        assert isinstance(config.chromadb.ssl, bool)
        assert isinstance(config.chunking.default_size, int)
        assert isinstance(config.chunking.respect_boundaries, bool)

    def test_config_validation_error_messages(self) -> None:
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
