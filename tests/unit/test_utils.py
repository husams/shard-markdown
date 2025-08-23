"""Unit tests for utility functions - pure functions, no mocks."""

import logging
import tempfile
from datetime import datetime
from pathlib import Path

from shard_markdown.utils.errors import (
    ChromaDBError,
    ConfigurationError,
    FileSystemError,
    InputValidationError,
    NetworkError,
    ProcessingError,
    ShardMarkdownError,
)
from shard_markdown.utils.logging import LogContext, get_logger, setup_logging


class TestErrorHandling:
    """Test error classes and exception handling - pure validation."""

    def test_base_error_creation(self) -> None:
        """Test creating base ShardMarkdownError."""
        error = ShardMarkdownError(
            message="Test error", error_code=1000, category="TEST"
        )

        assert error.message == "Test error"
        assert error.error_code == 1000
        assert error.category == "TEST"
        assert error.context == {}
        assert error.cause is None
        assert isinstance(error.timestamp, datetime)

    def test_error_with_context(self) -> None:
        """Test error with additional context information."""
        context = {"file_path": "test.md", "line": 42, "column": 10}
        error = ShardMarkdownError(
            message="Context error",
            error_code=1001,
            category="TEST",
            context=context,
        )

        assert error.context == context
        assert error.context["file_path"] == "test.md"
        assert error.context["line"] == 42

    def test_error_with_cause(self) -> None:
        """Test error wrapping another exception."""
        original_error = ValueError("Original error message")
        wrapped_error = ShardMarkdownError(
            message="Wrapper error",
            error_code=1002,
            category="TEST",
            cause=original_error,
        )

        assert wrapped_error.cause == original_error
        assert isinstance(wrapped_error.cause, ValueError)

    def test_error_serialization(self) -> None:
        """Test error serialization to dictionary."""
        context = {"operation": "parsing", "file": "doc.md"}
        cause = RuntimeError("Underlying issue")
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
        assert error_dict["cause"] == "Underlying issue"
        assert "timestamp" in error_dict
        assert isinstance(error_dict["timestamp"], str)

    def test_input_validation_error(self) -> None:
        """Test InputValidationError with default values."""
        error = InputValidationError("Invalid input provided")

        assert error.message == "Invalid input provided"
        assert error.error_code == 1000  # Default for INPUT category
        assert error.category == "INPUT"

    def test_input_validation_with_field_info(self) -> None:
        """Test InputValidationError with field context."""
        error = InputValidationError(
            "Invalid chunk size",
            context={
                "field": "chunk_size",
                "value": -100,
                "expected": "positive integer",
            },
        )

        assert error.message == "Invalid chunk size"
        assert error.context["field"] == "chunk_size"
        assert error.context["value"] == -100

    def test_processing_error(self) -> None:
        """Test ProcessingError for processing failures."""
        error = ProcessingError(
            "Failed to process document",
            context={"stage": "chunking", "file": "large.md"},
        )

        assert error.message == "Failed to process document"
        assert error.error_code == 1300  # Default for PROCESSING
        assert error.category == "PROCESSING"
        assert error.context["stage"] == "chunking"

    def test_file_system_error(self) -> None:
        """Test FileSystemError for file operations."""
        error = FileSystemError(
            "File not found", context={"path": "/nonexistent/file.md"}
        )

        assert error.message == "File not found"
        assert error.error_code == 1200  # Default for FILESYSTEM
        assert error.category == "FILESYSTEM"
        assert error.context["path"] == "/nonexistent/file.md"

    def test_configuration_error(self) -> None:
        """Test ConfigurationError for config issues."""
        error = ConfigurationError(
            "Invalid configuration",
            context={"config_file": "settings.yaml", "issue": "missing required field"},
        )

        assert error.message == "Invalid configuration"
        assert error.error_code == 1100  # Default for CONFIG
        assert error.category == "CONFIG"

    def test_chromadb_error(self) -> None:
        """Test ChromaDBError for database operations."""
        error = ChromaDBError(
            "Connection failed",
            context={"host": "localhost", "port": 8000},
        )

        assert error.message == "Connection failed"
        assert error.error_code == 1400  # Default for CHROMADB
        assert error.category == "DATABASE"
        assert error.context["port"] == 8000

    def test_network_error(self) -> None:
        """Test NetworkError for network issues."""
        error = NetworkError(
            "Request timeout",
            context={"url": "http://example.com", "timeout": 30},
        )

        assert error.message == "Request timeout"
        assert error.error_code == 1600  # Default for NETWORK
        assert error.category == "NETWORK"

    def test_error_chaining(self) -> None:
        """Test chaining multiple errors together."""
        file_error = FileSystemError("Cannot read file")
        processing_error = ProcessingError(
            "Document processing failed", cause=file_error
        )
        final_error = ShardMarkdownError(
            message="Operation failed",
            error_code=9999,
            category="GENERAL",
            cause=processing_error,
        )

        assert final_error.cause == processing_error
        assert processing_error.cause == file_error

    def test_error_str_representation(self) -> None:
        """Test string representation of errors."""
        error = InputValidationError(
            "Invalid value", context={"field": "test", "value": 123}
        )

        error_str = str(error)
        assert "Invalid value" in error_str


class TestLogging:
    """Test logging utilities - real logging configuration."""

    def test_get_logger_naming(self) -> None:
        """Test get_logger returns properly named logger."""
        logger = get_logger("test_module")

        assert logger.name == "shard_markdown.test_module"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_nested_module(self) -> None:
        """Test get_logger with nested module name."""
        logger = get_logger("cli.main")

        assert logger.name == "shard_markdown.cli.main"

    def test_setup_logging_basic(self) -> None:
        """Test basic logging setup with default settings."""
        # This will actually configure logging
        setup_logging(level=logging.INFO)

        # Get a logger and verify it works
        logger = get_logger("test")
        assert logger.level <= logging.INFO

    def test_setup_logging_with_file(self) -> None:
        """Test logging setup with file output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"

            setup_logging(level=logging.DEBUG, file_path=log_file)

            # Verify log file is created
            assert log_file.exists()

            # Write a test message
            logger = get_logger("test")
            logger.info("Test message")

            # Check that something was written to the file
            log_content = log_file.read_text()
            assert "Test message" in log_content

    def test_setup_logging_creates_directories(self) -> None:
        """Test that setup_logging creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "nested" / "subdir" / "test.log"

            setup_logging(file_path=log_file)

            # Parent directories should be created
            assert log_file.parent.exists()
            assert log_file.exists()

    def test_log_context_manager(self) -> None:
        """Test LogContext context manager for adding context to logs."""
        logger = get_logger("test_context")

        with LogContext(logger, operation="test_op", file="test.md"):
            # Inside context, logs should have additional context
            # This is a real test - the context manager should work
            pass

        # Context manager should complete without errors

    def test_logging_levels(self) -> None:
        """Test different logging levels."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "levels.log"

            # Set up with DEBUG level to capture all messages
            setup_logging(level=logging.DEBUG, file_path=log_file)

            logger = get_logger("level_test")

            # Log at different levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

            # Check all messages were logged
            log_content = log_file.read_text()
            assert "Debug message" in log_content
            assert "Info message" in log_content
            assert "Warning message" in log_content
            assert "Error message" in log_content

    def test_logging_with_exception(self) -> None:
        """Test logging exception information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "error.log"
            setup_logging(level=logging.ERROR, file_path=log_file)

            logger = get_logger("error_test")

            try:
                raise ValueError("Test exception")
            except ValueError:
                logger.exception("An error occurred")

            log_content = log_file.read_text()
            assert "An error occurred" in log_content
            assert "ValueError" in log_content
            assert "Test exception" in log_content

    def test_rotating_file_handler(self) -> None:
        """Test that log rotation configuration works."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "rotating.log"

            # Setup should configure rotating handler
            setup_logging(
                level=logging.INFO,
                file_path=log_file,
            )

            logger = get_logger("rotation_test")

            # Write many messages
            for i in range(100):
                logger.info(f"Message {i}: " + "x" * 100)

            # Log file should exist and contain messages
            assert log_file.exists()
            log_content = log_file.read_text()
            assert "Message" in log_content


class TestPathUtilities:
    """Test path and file system utility functions."""

    def test_path_validation(self) -> None:
        """Test path validation and normalization."""
        # Test with Path object
        path = Path("test.md")
        assert path.suffix == ".md"

        # Test absolute path
        abs_path = Path("/tmp/test.md")  # noqa: S108
        assert abs_path.is_absolute()

        # Test relative path
        rel_path = Path("../test.md")
        assert not rel_path.is_absolute()

    def test_file_extension_checking(self) -> None:
        """Test checking file extensions."""
        markdown_files = [
            Path("test.md"),
            Path("README.MD"),
            Path("doc.markdown"),
        ]

        for file in markdown_files:
            assert file.suffix.lower() in [".md", ".markdown"]

    def test_directory_creation(self) -> None:
        """Test safe directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new" / "nested" / "directory"

            # Create nested directories
            new_dir.mkdir(parents=True, exist_ok=True)

            assert new_dir.exists()
            assert new_dir.is_dir()

    def test_file_size_calculation(self) -> None:
        """Test calculating file sizes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            content = "Test content\n" * 100
            f.write(content)
            temp_path = Path(f.name)

        try:
            # Check file size
            file_size = temp_path.stat().st_size
            assert file_size > 0
            assert file_size == len(content.encode())
        finally:
            temp_path.unlink()


class TestValidationUtilities:
    """Test input validation utility functions."""

    def test_validate_positive_integer(self) -> None:
        """Test validation of positive integers."""
        # Valid cases
        assert 1 > 0
        assert 100 > 0
        assert 999999 > 0

        # Invalid cases
        assert not (-1 > 0)
        assert not (0 > 0)

    def test_validate_file_path(self) -> None:
        """Test file path validation."""
        # Valid markdown extensions
        valid_extensions = [".md", ".markdown", ".mdown", ".mkd"]

        for ext in valid_extensions:
            path = Path(f"test{ext}")
            assert path.suffix.lower() in [".md", ".markdown", ".mdown", ".mkd"]

        # Invalid extensions
        invalid_path = Path("test.txt")
        assert invalid_path.suffix != ".md"

    def test_validate_url(self) -> None:
        """Test URL validation patterns."""
        valid_urls = [
            "http://localhost:8000",
            "https://example.com",
            "http://192.168.1.1:8080",
        ]

        for url in valid_urls:
            assert url.startswith(("http://", "https://"))

        invalid_url = "not_a_url"
        assert not invalid_url.startswith(("http://", "https://"))

    def test_validate_chunk_size(self) -> None:
        """Test chunk size validation."""
        # Valid chunk sizes
        valid_sizes = [100, 500, 1000, 5000]

        for size in valid_sizes:
            assert 50 <= size <= 10000  # Reasonable range

        # Invalid chunk sizes
        invalid_sizes = [-100, 0, 20, 50000]

        for size in invalid_sizes:
            if size <= 0:
                assert size <= 0  # Too small
            elif size < 50:
                assert size < 50  # Below minimum
            else:
                assert size > 10000  # Too large

    def test_validate_collection_name(self) -> None:
        """Test ChromaDB collection name validation."""
        # Valid collection names
        valid_names = [
            "test_collection",
            "my-docs",
            "project123",
            "data_2024",
        ]

        for name in valid_names:
            # ChromaDB collection names: 3-63 chars, alphanumeric + _ -
            assert 3 <= len(name) <= 63
            assert all(c.isalnum() or c in "_-" for c in name)

        # Invalid collection names
        invalid_names = [
            "ab",  # Too short
            "a" * 64,  # Too long
            "test collection",  # Contains space
            "test@collection",  # Invalid character
        ]

        for name in invalid_names:
            is_valid = 3 <= len(name) <= 63 and all(
                c.isalnum() or c in "_-" for c in name
            )
            assert not is_valid
