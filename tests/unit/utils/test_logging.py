"""Tests for logging utilities."""

import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shard_markdown.utils.logging import LogContext, get_logger, setup_logging


@pytest.mark.unit
def test_setup_logging_console_only() -> None:
    """Test basic logging setup with console handler only."""
    with patch("shard_markdown.utils.logging.logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_third_party_logger = MagicMock()

        def get_logger_side_effect(name):
            if name == "shard_markdown":
                return mock_logger
            else:
                return mock_third_party_logger

        mock_get_logger.side_effect = get_logger_side_effect

        setup_logging(level=logging.DEBUG)

        mock_logger.setLevel.assert_called_with(logging.DEBUG)
        mock_logger.handlers.clear.assert_called_once()
        mock_logger.addHandler.assert_called_once()


@pytest.mark.unit
def test_setup_logging_with_file() -> None:
    """Test logging setup with file handler."""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = Path(temp_dir) / "test.log"

        with patch("shard_markdown.utils.logging.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_third_party_logger = MagicMock()

            def get_logger_side_effect(name):
                if name == "shard_markdown":
                    return mock_logger
                else:
                    return mock_third_party_logger

            mock_get_logger.side_effect = get_logger_side_effect

            setup_logging(level=logging.INFO, file_path=log_file)

            mock_logger.setLevel.assert_called_with(logging.INFO)
            mock_logger.handlers.clear.assert_called_once()
            # Should have been called twice: console + file handler
            assert mock_logger.addHandler.call_count == 2


@pytest.mark.unit
def test_setup_logging_creates_parent_directories() -> None:
    """Test that setup_logging creates parent directories for log file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = Path(temp_dir) / "nested" / "subdir" / "test.log"

        setup_logging(file_path=log_file)

        assert log_file.parent.exists()


@pytest.mark.unit
def test_get_logger() -> None:
    """Test get_logger returns properly named logger."""
    logger = get_logger("test_module")

    assert logger.name == "shard_markdown.test_module"
    assert isinstance(logger, logging.Logger)


@pytest.mark.unit
def test_get_logger_with_qualified_name() -> None:
    """Test get_logger with fully qualified module name."""
    logger = get_logger("cli.commands.process")

    assert logger.name == "shard_markdown.cli.commands.process"


@pytest.mark.unit
def test_log_context_initialization() -> None:
    """Test LogContext initialization."""
    logger = logging.getLogger("test")
    context = {"user_id": "123", "operation": "test"}

    log_context = LogContext(logger, **context)

    assert log_context.logger is logger
    assert log_context.context == context
    assert log_context.old_factory is None


@pytest.mark.unit
def test_log_context_manager_enter() -> None:
    """Test LogContext context manager enter method."""
    logger = logging.getLogger("test")
    context = {"request_id": "abc123"}

    get_factory_patch = patch(
        "shard_markdown.utils.logging.logging.getLogRecordFactory"
    )
    with get_factory_patch as mock_get_factory:
        mock_factory = MagicMock()
        mock_get_factory.return_value = mock_factory

        set_factory_patch = patch(
            "shard_markdown.utils.logging.logging.setLogRecordFactory"
        )
        with set_factory_patch as mock_set_factory:
            log_context = LogContext(logger, **context)

            result = log_context.__enter__()

            assert result is log_context
            assert log_context.old_factory is mock_factory
            mock_set_factory.assert_called_once()


@pytest.mark.unit
def test_log_context_manager_exit() -> None:
    """Test LogContext context manager exit method."""
    logger = logging.getLogger("test")
    mock_factory = MagicMock()

    set_factory_patch = patch(
        "shard_markdown.utils.logging.logging.setLogRecordFactory"
    )
    with set_factory_patch as mock_set_factory:
        log_context = LogContext(logger, test_key="test_value")
        log_context.old_factory = mock_factory

        log_context.__exit__(None, None, None)

        mock_set_factory.assert_called_with(mock_factory)


@pytest.mark.unit
def test_log_context_manager_exit_no_old_factory() -> None:
    """Test LogContext exit when old_factory is None."""
    logger = logging.getLogger("test")

    set_factory_patch = patch(
        "shard_markdown.utils.logging.logging.setLogRecordFactory"
    )
    with set_factory_patch as mock_set_factory:
        log_context = LogContext(logger, test_key="test_value")
        log_context.old_factory = None

        log_context.__exit__(None, None, None)

        # Should not call setLogRecordFactory when old_factory is None
        mock_set_factory.assert_not_called()


@pytest.mark.unit
def test_log_context_record_factory() -> None:
    """Test that LogContext adds context to log records."""
    logger = logging.getLogger("test")
    context = {"user_id": "123", "operation": "test_op"}

    with LogContext(logger, **context):
        # Use the factory to create a log record
        factory = logging.getLogRecordFactory()
        record = factory(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # The factory should have added our context
        assert hasattr(record, "user_id")
        assert hasattr(record, "operation")
        assert record.user_id == "123"
        assert record.operation == "test_op"


@pytest.mark.unit
def test_log_context_with_statement() -> None:
    """Test LogContext as context manager with statement."""
    logger = logging.getLogger("test")
    context = {"session_id": "session123"}

    # Test that context manager works properly
    with LogContext(logger, **context) as log_ctx:
        assert log_ctx.context == context
        assert log_ctx.logger is logger


@pytest.mark.unit
def test_setup_logging_third_party_loggers() -> None:
    """Test that third-party loggers are set to WARNING level."""
    with patch("shard_markdown.utils.logging.logging.getLogger") as mock_get_logger:
        mock_main_logger = MagicMock()
        mock_chromadb_logger = MagicMock()
        mock_httpx_logger = MagicMock()
        mock_urllib3_logger = MagicMock()

        def logger_side_effect(name: str) -> MagicMock:
            if name == "shard_markdown":
                return mock_main_logger
            elif name == "chromadb":
                return mock_chromadb_logger
            elif name == "httpx":
                return mock_httpx_logger
            elif name == "urllib3":
                return mock_urllib3_logger
            return MagicMock()

        mock_get_logger.side_effect = logger_side_effect

        setup_logging()

        mock_chromadb_logger.setLevel.assert_called_with(logging.WARNING)
        mock_httpx_logger.setLevel.assert_called_with(logging.WARNING)
        mock_urllib3_logger.setLevel.assert_called_with(logging.WARNING)


@pytest.mark.unit
def test_setup_logging_file_rotation_config() -> None:
    """Test that file handler is configured with rotation settings."""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = Path(temp_dir) / "test.log"
        max_size = 5242880  # 5MB
        backup_count = 3

        handler_patch = patch(
            "shard_markdown.utils.logging.logging.handlers.RotatingFileHandler"
        )
        with handler_patch as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler

            setup_logging(
                file_path=log_file,
                max_file_size=max_size,
                backup_count=backup_count,
            )

            mock_handler_class.assert_called_with(
                filename=log_file,
                maxBytes=max_size,
                backupCount=backup_count,
            )


@pytest.mark.unit
def test_log_context_record_factory_fallback() -> None:
    """Test LogContext record factory fallback when old_factory is None."""
    logger = logging.getLogger("test")

    get_factory_patch = patch(
        "shard_markdown.utils.logging.logging.getLogRecordFactory",
        return_value=None,
    )
    with get_factory_patch:
        log_record_patch = patch("shard_markdown.utils.logging.logging.LogRecord")
        with log_record_patch as mock_log_record:
            mock_record = MagicMock()
            mock_log_record.return_value = mock_record

            log_context = LogContext(logger, test_attr="test_value")
            log_context.__enter__()

            # The factory should handle None old_factory case
            assert log_context.old_factory is None
