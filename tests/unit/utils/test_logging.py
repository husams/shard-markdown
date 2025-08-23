"""Refactored logging tests using real logging instead of mocks."""

import logging
import tempfile
from pathlib import Path

import pytest

from shard_markdown.utils.logging import LogContext, get_logger, setup_logging


class TestLoggingSetup:
    """Test logging setup with real logging objects."""

    @pytest.fixture(autouse=True)
    def reset_logging(self):
        """Reset logging configuration after each test."""
        yield
        # Clear all handlers from shard_markdown logger
        logger = logging.getLogger("shard_markdown")
        logger.handlers.clear()
        logger.setLevel(logging.WARNING)

    @pytest.mark.unit
    def test_setup_logging_console_only(self):
        """Test basic logging setup with console handler only."""
        setup_logging(level=logging.DEBUG)

        logger = logging.getLogger("shard_markdown")
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) == 1
        # The project uses RichHandler (which extends StreamHandler)
        handler_name = type(logger.handlers[0]).__name__
        assert handler_name in ["StreamHandler", "RichHandler"]

    @pytest.mark.unit
    def test_setup_logging_with_file(self):
        """Test logging setup with file handler."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"

            setup_logging(level=logging.INFO, file_path=log_file)

            logger = logging.getLogger("shard_markdown")
            assert logger.level == logging.INFO
            assert len(logger.handlers) == 2  # Console + file

            # Verify handlers (RichHandler is used instead of StreamHandler)
            handler_types = [type(h).__name__ for h in logger.handlers]
            assert any(h in handler_types for h in ["StreamHandler", "RichHandler"])
            assert "RotatingFileHandler" in handler_types

            # Test that logging actually writes to file
            logger.info("Test message")
            assert log_file.exists()
            assert "Test message" in log_file.read_text()

    @pytest.mark.unit
    def test_setup_logging_creates_parent_directories(self):
        """Test that setup_logging creates parent directories for log file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "nested" / "subdir" / "test.log"

            setup_logging(file_path=log_file)

            assert log_file.parent.exists()

            # Test that logging works
            logger = logging.getLogger("shard_markdown")
            logger.info("Directory test")
            assert log_file.exists()

    @pytest.mark.unit
    def test_third_party_loggers_silenced(self):
        """Test that third-party loggers are set to WARNING level."""
        setup_logging(level=logging.DEBUG)

        # Check third-party loggers
        assert logging.getLogger("chromadb").level == logging.WARNING
        assert logging.getLogger("httpx").level == logging.WARNING
        assert logging.getLogger("urllib3").level == logging.WARNING

        # Main logger should still be DEBUG
        assert logging.getLogger("shard_markdown").level == logging.DEBUG


class TestGetLogger:
    """Test get_logger function."""

    @pytest.mark.unit
    def test_get_logger(self):
        """Test get_logger returns properly named logger."""
        logger = get_logger("test_module")

        assert logger.name == "shard_markdown.test_module"
        assert isinstance(logger, logging.Logger)

    @pytest.mark.unit
    def test_get_logger_with_qualified_name(self):
        """Test get_logger with fully qualified module name."""
        logger = get_logger("cli.main")

        assert logger.name == "shard_markdown.cli.main"

    @pytest.mark.unit
    def test_get_logger_caching(self):
        """Test that get_logger returns the same instance for same name."""
        logger1 = get_logger("test")
        logger2 = get_logger("test")

        assert logger1 is logger2


class TestLogContext:
    """Test LogContext context manager with real logging."""

    @pytest.mark.unit
    def test_log_context_initialization(self):
        """Test LogContext initialization."""
        logger = logging.getLogger("test")
        context = {"user_id": "123", "operation": "test"}

        log_context = LogContext(logger, **context)

        assert log_context.logger is logger
        assert log_context.context == context
        assert log_context.old_factory is None

    @pytest.mark.unit
    def test_log_context_adds_attributes(self, caplog):
        """Test that LogContext adds context to log records."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        context = {"user_id": "123", "operation": "test_op"}

        with LogContext(logger, **context):
            logger.info("Test message")

        # Check that the log record has our context attributes
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert hasattr(record, "user_id")
        assert hasattr(record, "operation")
        assert record.user_id == "123"
        assert record.operation == "test_op"

    @pytest.mark.unit
    def test_log_context_nested(self, caplog):
        """Test nested LogContext managers."""
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)

        with LogContext(logger, request_id="req123"):
            with LogContext(logger, user_id="user456"):
                logger.info("Nested context")

        # Both contexts should be present
        record = caplog.records[0]
        assert hasattr(record, "request_id")
        assert hasattr(record, "user_id")
        assert record.request_id == "req123"
        assert record.user_id == "user456"

    @pytest.mark.unit
    def test_log_context_restoration(self):
        """Test that LogContext restores original factory on exit."""
        original_factory = logging.getLogRecordFactory()
        logger = logging.getLogger("test")

        with LogContext(logger, test_key="test_value"):
            # Factory should be different inside context
            assert logging.getLogRecordFactory() != original_factory

        # Factory should be restored after context
        assert logging.getLogRecordFactory() == original_factory

    @pytest.mark.unit
    def test_log_context_with_statement(self):
        """Test LogContext as context manager with statement."""
        logger = logging.getLogger("test")
        context = {"session_id": "session123"}

        with LogContext(logger, **context) as log_ctx:
            assert log_ctx.context == context
            assert log_ctx.logger is logger


class TestIntegrationLogging:
    """Integration tests for logging functionality."""

    @pytest.mark.unit
    def test_complete_logging_workflow(self):
        """Test complete logging workflow with real components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "app.log"

            # Setup logging
            setup_logging(
                level=logging.DEBUG,
                file_path=log_file,
                max_file_size=1024 * 1024,  # 1MB
                backup_count=2,
            )

            # Get logger
            logger = get_logger("test.module")

            # Log with context
            with LogContext(logger, request_id="req789", user="testuser"):
                logger.info("Processing request")
                logger.debug("Debug information")
                logger.warning("Warning message")

            # Verify file output
            log_content = log_file.read_text()
            assert "Processing request" in log_content
            assert "Debug information" in log_content
            assert "Warning message" in log_content

            # Verify logger is in correct hierarchy
            assert logger.name.startswith("shard_markdown")

    @pytest.mark.unit
    def test_multiple_handlers_formatting(self):
        """Test that multiple handlers work correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "multi.log"

            setup_logging(level=logging.INFO, file_path=log_file)
            logger = get_logger("multi.test")

            # Log a message
            test_message = "Multiple handler test"
            logger.info(test_message)

            # Message should be in file
            assert test_message in log_file.read_text()

            # Both handlers should be active
            root_logger = logging.getLogger("shard_markdown")
            assert len(root_logger.handlers) == 2
