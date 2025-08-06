"""Unit tests for configuration settings."""

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
        # Valid sizes (updated to match new constraints)
        valid_sizes = [50, 100, 500, 1000, 5000, 50000]  # Now includes 50 as valid
        for size in valid_sizes:
            config = ChunkingConfig(default_size=size)
            assert config.default_size == size

        # Invalid sizes (updated to match new constraints)
        invalid_sizes = [0, -100, 49, 50001]  # Now 49 is too small, 50001 too large
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

        # Test new maximum overlap constraint
        config_large_overlap = ChunkingConfig(default_size=10000, default_overlap=5000)
        assert config_large_overlap.default_overlap == 5000

        # Too large overlap should fail
        with pytest.raises(ValidationError):
            ChunkingConfig(default_size=10000, default_overlap=5001)

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
            ChunkingConfig(method="invalid_method")

    def test_max_tokens_validation(self) -> None:
        """Test max_tokens validation."""
        # Valid max_tokens values
        config = ChunkingConfig(max_tokens=1000)
        assert config.max_tokens == 1000

        config_none = ChunkingConfig(max_tokens=None)
        assert config_none.max_tokens is None

        # Test new constraints
        config_max = ChunkingConfig(max_tokens=100000)
        assert config_max.max_tokens == 100000

        # Invalid max_tokens
        with pytest.raises(ValidationError):
            ChunkingConfig(max_tokens=0)

        with pytest.raises(ValidationError):
            ChunkingConfig(max_tokens=100001)

    def test_overlap_size_relationship(self) -> None:
        """Test overlap cannot be larger than chunk size."""
        # Equal overlap and chunk size should fail
        with pytest.raises(ValidationError):
            ChunkingConfig(default_size=100, default_overlap=100)

        # Overlap just less than chunk size should work
        config = ChunkingConfig(default_size=100, default_overlap=99)
        assert config.default_overlap == 99


class TestProcessingConfig:
    """Test processing configuration validation."""

    def test_valid_config(self) -> None:
        """Test valid processing configuration."""
        config = ProcessingConfig(
            batch_size=10,
            max_workers=4,
            recursive=True,
            pattern="*.md",
        )

        assert config.batch_size == 10
        assert config.max_workers == 4
        assert config.recursive is True
        assert config.pattern == "*.md"

    def test_default_values(self) -> None:
        """Test all default configuration values."""
        config = ProcessingConfig()

        # Basic processing defaults
        assert config.batch_size == 10
        assert config.max_workers == 4
        assert config.recursive is False
        assert config.pattern == "*.md"
        assert config.include_frontmatter is True
        assert config.include_path_metadata is True

        # File handling defaults (new requirements)
        assert config.max_file_size == 10_000_000  # 10MB
        assert config.skip_empty_files is True
        assert config.strict_validation is False
        assert config.encoding == "utf-8"
        assert config.encoding_fallback == "latin-1"

        # Advanced encoding detection defaults
        assert config.enable_encoding_detection is True
        assert config.encoding_detection is not None
        assert config.validation is not None

    def test_batch_size_validation(self) -> None:
        """Test batch size validation."""
        # Valid batch sizes
        valid_sizes = [1, 10, 50, 100]
        for size in valid_sizes:
            config = ProcessingConfig(batch_size=size)
            assert config.batch_size == size

        # Invalid batch sizes
        invalid_sizes = [0, -1, 101]
        for size in invalid_sizes:
            with pytest.raises(ValidationError):
                ProcessingConfig(batch_size=size)

    def test_max_workers_validation(self) -> None:
        """Test max workers validation."""
        # Valid worker counts
        valid_counts = [1, 4, 8, 16]
        for count in valid_counts:
            config = ProcessingConfig(max_workers=count)
            assert config.max_workers == count

        # Invalid worker counts
        invalid_counts = [0, -1, 17]
        for count in invalid_counts:
            with pytest.raises(ValidationError):
                ProcessingConfig(max_workers=count)

    def test_max_file_size_validation(self) -> None:
        """Test max file size validation."""
        # Valid file sizes
        valid_sizes = [1, 1024, 10_000_000, 100_000_000]
        for size in valid_sizes:
            config = ProcessingConfig(max_file_size=size)
            assert config.max_file_size == size

        # Invalid file sizes (must be positive)
        invalid_sizes = [0, -1, -100]
        for size in invalid_sizes:
            with pytest.raises(ValidationError):
                ProcessingConfig(max_file_size=size)

    def test_encoding_settings(self) -> None:
        """Test encoding configuration."""
        # Test custom encoding settings
        config = ProcessingConfig(encoding="iso-8859-1", encoding_fallback="utf-8")
        assert config.encoding == "iso-8859-1"
        assert config.encoding_fallback == "utf-8"

        # Test common encodings
        common_encodings = ["utf-8", "latin-1", "ascii", "iso-8859-1", "cp1252"]
        for encoding in common_encodings:
            config = ProcessingConfig(encoding=encoding)
            assert config.encoding == encoding

    def test_boolean_flags(self) -> None:
        """Test boolean configuration flags."""
        # Test all boolean flags
        config = ProcessingConfig(
            recursive=True,
            include_frontmatter=False,
            include_path_metadata=False,
            skip_empty_files=False,
            strict_validation=True,
            enable_encoding_detection=False,
        )

        assert config.recursive is True
        assert config.include_frontmatter is False
        assert config.include_path_metadata is False
        assert config.skip_empty_files is False
        assert config.strict_validation is True
        assert config.enable_encoding_detection is False

    def test_pattern_validation(self) -> None:
        """Test file pattern validation."""
        # Valid patterns
        valid_patterns = ["*.md", "*.txt", "**/*.md", "doc_*.markdown"]
        for pattern in valid_patterns:
            config = ProcessingConfig(pattern=pattern)
            assert config.pattern == pattern

    def test_backward_compatibility(self) -> None:
        """Test that old configuration still works without new fields."""
        # This should work with just basic fields
        config = ProcessingConfig(
            batch_size=5,
            max_workers=2,
            recursive=True,
        )

        # Should use defaults for new fields
        assert config.max_file_size == 10_000_000
        assert config.skip_empty_files is True
        assert config.strict_validation is False
        assert config.encoding == "utf-8"
        assert config.encoding_fallback == "latin-1"


class TestAppConfig:
    """Test main application configuration."""

    def test_valid_config(self) -> None:
        """Test valid application configuration."""
        config = AppConfig()

        # Check that all sub-configurations exist
        assert isinstance(config.chromadb, ChromaDBConfig)
        assert isinstance(config.chunking, ChunkingConfig)
        assert isinstance(config.processing, ProcessingConfig)

    def test_custom_subconfigs(self) -> None:
        """Test app config with custom sub-configurations."""
        chromadb_config = ChromaDBConfig(host="remote.db", port=9000)
        chunking_config = ChunkingConfig(default_size=2000, default_overlap=400)
        processing_config = ProcessingConfig(batch_size=20, max_workers=8)

        config = AppConfig(
            chromadb=chromadb_config,
            chunking=chunking_config,
            processing=processing_config,
        )

        assert config.chromadb.host == "remote.db"
        assert config.chromadb.port == 9000
        assert config.chunking.default_size == 2000
        assert config.chunking.default_overlap == 400
        assert config.processing.batch_size == 20
        assert config.processing.max_workers == 8

    def test_default_processing_config_in_app(self) -> None:
        """Test that app config contains processing config with proper defaults."""
        config = AppConfig()

        # Verify processing config defaults are correct within app config
        assert config.processing.max_file_size == 10_000_000
        assert config.processing.skip_empty_files is True
        assert config.processing.strict_validation is False
        assert config.processing.encoding == "utf-8"
        assert config.processing.encoding_fallback == "latin-1"


class TestConfigValidationScenarios:
    """Test various configuration validation scenarios."""

    def test_edge_case_values(self) -> None:
        """Test configuration with edge case values."""
        # Minimum chunk size (now 50)
        chunking_config = ChunkingConfig(default_size=50)
        assert chunking_config.default_size == 50

        # Maximum chunk size (now 50000)
        chunking_config_max = ChunkingConfig(default_size=50000)
        assert chunking_config_max.default_size == 50000

        # Maximum valid port
        chromadb_config = ChromaDBConfig(port=65535)
        assert chromadb_config.port == 65535

        # Minimum valid timeout
        chromadb_config_timeout = ChromaDBConfig(timeout=1)
        assert chromadb_config_timeout.timeout == 1

    def test_extreme_values(self) -> None:
        """Test configuration with extreme values."""
        # Very large chunk size (within new limits)
        chunking_config = ChunkingConfig(default_size=50000)
        assert chunking_config.default_size == 50000

        # Very high worker count
        processing_config = ProcessingConfig(max_workers=16)  # Updated to max
        assert processing_config.max_workers == 16

        # Very large timeout
        chromadb_config = ChromaDBConfig(timeout=3600)
        assert chromadb_config.timeout == 3600

        # Very large file size limit
        processing_config_large = ProcessingConfig(max_file_size=1_000_000_000)  # 1GB
        assert processing_config_large.max_file_size == 1_000_000_000

    def test_boundary_values(self) -> None:
        """Test configuration with boundary values."""
        # Minimum valid chunk size (now 50)
        chunking_config = ChunkingConfig(default_size=50)
        assert chunking_config.default_size == 50

        # Maximum valid port
        chromadb_config = ChromaDBConfig(port=65535)
        assert chromadb_config.port == 65535

        # Minimum valid timeout
        chromadb_config_timeout = ChromaDBConfig(timeout=1)
        assert chromadb_config_timeout.timeout == 1

        # Minimum file size (1 byte)
        processing_config = ProcessingConfig(max_file_size=1)
        assert processing_config.max_file_size == 1

    def test_configuration_combinations(self) -> None:
        """Test valid combinations of configuration values."""
        # High chunk size with high overlap
        chunking_config = ChunkingConfig(default_size=5000, default_overlap=2000)
        assert chunking_config.default_size == 5000
        assert chunking_config.default_overlap == 2000

        # Large batch with many workers
        processing_config = ProcessingConfig(batch_size=100, max_workers=16)
        assert processing_config.batch_size == 100
        assert processing_config.max_workers == 16

        # Strict validation with custom encoding
        processing_config_strict = ProcessingConfig(
            strict_validation=True,
            encoding="iso-8859-1",
            encoding_fallback="utf-8",
            skip_empty_files=False,
        )
        assert processing_config_strict.strict_validation is True
        assert processing_config_strict.encoding == "iso-8859-1"
        assert processing_config_strict.encoding_fallback == "utf-8"
        assert processing_config_strict.skip_empty_files is False

    def test_config_validation_error_messages(self) -> None:
        """Test that validation errors provide helpful messages."""
        # Test port validation error
        try:
            ChromaDBConfig(port=70000)
            raise AssertionError("Should have raised ValidationError")
        except ValidationError as e:
            error_msg = str(e)
            assert "port" in error_msg.lower() or "65535" in error_msg

        # Test chunk size validation error (updated for new minimum)
        try:
            ChunkingConfig(default_size=49)  # Now 49 is too small
            raise AssertionError("Should have raised ValidationError")
        except ValidationError as e:
            error_msg = str(e)
            assert "size" in error_msg.lower() or "50" in error_msg

        # Test file size validation error
        try:
            ProcessingConfig(max_file_size=0)
            raise AssertionError("Should have raised ValidationError")
        except ValidationError as e:
            error_msg = str(e)
            assert "size" in error_msg.lower() or "greater" in error_msg.lower()

    def test_config_conversion(self) -> None:
        """Test config conversion between settings and core models."""
        settings_config = ChunkingConfig(
            default_size=2000,
            default_overlap=300,
            method=ChunkingMethod.STRUCTURE,
            respect_boundaries=True,
            max_tokens=4000,
        )

        # Test conversion to core config
        core_config = settings_config.to_core_config()
        assert core_config.chunk_size == 2000
        assert core_config.overlap == 300
        assert core_config.method == "structure"
        assert core_config.respect_boundaries is True
        assert core_config.max_tokens == 4000


class TestConfigDefaults:
    """Test that all configuration defaults match requirements."""

    def test_processing_config_required_defaults(self) -> None:
        """Test that ProcessingConfig has the exact defaults specified in issue."""
        config = ProcessingConfig()

        # Verify exact default values as specified in the issue
        assert config.max_file_size == 10_000_000, (
            "max_file_size should default to 10MB"
        )
        assert config.skip_empty_files is True, (
            "skip_empty_files should default to True"
        )
        assert config.strict_validation is False, (
            "strict_validation should default to False"
        )
        assert config.encoding == "utf-8", "encoding should default to 'utf-8'"
        assert config.encoding_fallback == "latin-1", (
            "encoding_fallback should default to 'latin-1'"
        )

    def test_config_factory_compatibility(self) -> None:
        """Test that config can be created for tests easily."""
        # Should be easy to create a test config
        test_config = ProcessingConfig(
            batch_size=1,  # Small batch for tests
            max_workers=1,  # Single worker for tests
            max_file_size=1_000_000,  # 1MB for tests
        )

        assert test_config.batch_size == 1
        assert test_config.max_workers == 1
        assert test_config.max_file_size == 1_000_000
        # Other values should still use defaults
        assert test_config.skip_empty_files is True
        assert test_config.encoding == "utf-8"
