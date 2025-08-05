"""Unit tests for error handling and exception classes."""

from datetime import datetime

from shard_markdown.utils.errors import (
    ChromaDBError,
    ConfigurationError,
    FileSystemError,
    InputValidationError,
    NetworkError,
    ProcessingError,
    ShardMarkdownError,
    SystemError,
)


class TestShardMarkdownError:
    """Test ShardMarkdownError base class."""

    def test_create_basic_error(self) -> None:
        """Test creating basic error with required parameters."""
        error = ShardMarkdownError(
            message="Test error", error_code=1000, category="TEST"
        )

        assert error.message == "Test error"
        assert error.error_code == 1000
        assert error.category == "TEST"
        assert error.context == {}
        assert error.cause is None
        assert isinstance(error.timestamp, datetime)

    def test_create_error_with_context(self) -> None:
        """Test creating error with context."""
        context = {"file_path": "test.md", "line": 42}
        error = ShardMarkdownError(
            message="Context error",
            error_code=1001,
            category="TEST",
            context=context,
        )

        assert error.context == context

    def test_create_error_with_cause(self) -> None:
        """Test creating error with underlying cause."""
        cause = ValueError("Original error")
        error = ShardMarkdownError(
            message="Wrapper error",
            error_code=1002,
            category="TEST",
            cause=cause,
        )

        assert error.cause == cause

    def test_to_dict_method(self) -> None:
        """Test error serialization to dictionary."""
        context = {"key": "value"}
        cause = RuntimeError("Underlying error")
        error = ShardMarkdownError(
            message="Test error",
            error_code=1003,
            category="TEST",
            context=context,
            cause=cause,
        )

        error_dict = error.to_dict()

        assert error_dict["error_code"] == 1003
        assert error_dict["category"] == "TEST"
        assert error_dict["message"] == "Test error"
        assert error_dict["context"] == context
        assert error_dict["cause"] == "Underlying error"
        assert "timestamp" in error_dict

    def test_to_dict_without_cause(self) -> None:
        """Test error serialization without cause."""
        error = ShardMarkdownError(
            message="No cause error", error_code=1004, category="TEST"
        )

        error_dict = error.to_dict()

        assert error_dict["cause"] is None


class TestInputValidationError:
    """Test InputValidationError class."""

    def test_create_default_validation_error(self) -> None:
        """Test creating validation error with default error code."""
        error = InputValidationError("Invalid input")

        assert error.message == "Invalid input"
        assert error.error_code == 1000
        assert error.category == "INPUT"

    def test_create_custom_validation_error(self) -> None:
        """Test creating validation error with custom error code."""
        error = InputValidationError("Custom validation", error_code=1050)

        assert error.message == "Custom validation"
        assert error.error_code == 1050
        assert error.category == "INPUT"

    def test_validation_error_with_context(self) -> None:
        """Test validation error with context."""
        context = {"field": "chunk_size", "value": -1}
        error = InputValidationError("Invalid chunk size", context=context)

        assert error.context == context


class TestConfigurationError:
    """Test ConfigurationError class."""

    def test_create_default_config_error(self) -> None:
        """Test creating configuration error with default error code."""
        error = ConfigurationError("Config missing")

        assert error.message == "Config missing"
        assert error.error_code == 1100
        assert error.category == "CONFIG"

    def test_create_custom_config_error(self) -> None:
        """Test creating configuration error with custom error code."""
        error = ConfigurationError("Invalid config", error_code=1150)

        assert error.message == "Invalid config"
        assert error.error_code == 1150
        assert error.category == "CONFIG"


class TestFileSystemError:
    """Test FileSystemError class."""

    def test_create_default_filesystem_error(self) -> None:
        """Test creating filesystem error with default error code."""
        error = FileSystemError("File not found")

        assert error.message == "File not found"
        assert error.error_code == 1200
        assert error.category == "FILESYSTEM"

    def test_create_custom_filesystem_error(self) -> None:
        """Test creating filesystem error with custom error code."""
        error = FileSystemError("Permission denied", error_code=1250)

        assert error.message == "Permission denied"
        assert error.error_code == 1250
        assert error.category == "FILESYSTEM"


class TestProcessingError:
    """Test ProcessingError class."""

    def test_create_default_processing_error(self) -> None:
        """Test creating processing error with default error code."""
        error = ProcessingError("Processing failed")

        assert error.message == "Processing failed"
        assert error.error_code == 1300
        assert error.category == "PROCESSING"

    def test_create_custom_processing_error(self) -> None:
        """Test creating processing error with custom error code."""
        error = ProcessingError("Parse error", error_code=1350)

        assert error.message == "Parse error"
        assert error.error_code == 1350
        assert error.category == "PROCESSING"


class TestChromaDBError:
    """Test ChromaDBError class."""

    def test_create_default_chromadb_error(self) -> None:
        """Test creating ChromaDB error with default error code."""
        error = ChromaDBError("Connection failed")

        assert error.message == "Connection failed"
        assert error.error_code == 1400
        assert error.category == "DATABASE"

    def test_create_custom_chromadb_error(self) -> None:
        """Test creating ChromaDB error with custom error code."""
        error = ChromaDBError("Query timeout", error_code=1450)

        assert error.message == "Query timeout"
        assert error.error_code == 1450
        assert error.category == "DATABASE"


class TestSystemError:
    """Test SystemError class."""

    def test_create_default_system_error(self) -> None:
        """Test creating system error with default error code."""
        error = SystemError("System failure")

        assert error.message == "System failure"
        assert error.error_code == 1500
        assert error.category == "SYSTEM"

    def test_create_custom_system_error(self) -> None:
        """Test creating system error with custom error code."""
        error = SystemError("Memory error", error_code=1550)

        assert error.message == "Memory error"
        assert error.error_code == 1550
        assert error.category == "SYSTEM"


class TestNetworkError:
    """Test NetworkError class."""

    def test_create_default_network_error(self) -> None:
        """Test creating network error with default error code."""
        error = NetworkError("Network timeout")

        assert error.message == "Network timeout"
        assert error.error_code == 1600
        assert error.category == "NETWORK"

    def test_create_custom_network_error(self) -> None:
        """Test creating network error with custom error code."""
        error = NetworkError("DNS failure", error_code=1650)

        assert error.message == "DNS failure"
        assert error.error_code == 1650
        assert error.category == "NETWORK"


class TestErrorInheritance:
    """Test error class inheritance and polymorphism."""

    def test_all_errors_inherit_from_base(self) -> None:
        """Test that all error classes inherit from ShardMarkdownError."""
        errors = [
            InputValidationError("test"),
            ConfigurationError("test"),
            FileSystemError("test"),
            ProcessingError("test"),
            ChromaDBError("test"),
            SystemError("test"),
            NetworkError("test"),
        ]

        for error in errors:
            assert isinstance(error, ShardMarkdownError)
            assert isinstance(error, Exception)

    def test_error_string_representation(self) -> None:
        """Test error string representation."""
        error = InputValidationError("Test validation error")
        error_str = str(error)

        assert "Test validation error" in error_str

    def test_error_inheritance_chain(self) -> None:
        """Test error inheritance chain."""
        error = ProcessingError("Processing issue")

        # Should be instance of all base classes
        assert isinstance(error, ProcessingError)
        assert isinstance(error, ShardMarkdownError)
        assert isinstance(error, Exception)
        assert isinstance(error, BaseException)
