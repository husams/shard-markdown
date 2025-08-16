"""Tests for CLI pattern matching routing system."""

from argparse import Namespace
from unittest.mock import Mock

import pytest

# Pattern matching tests require Python 3.10+
from shard_markdown.cli.routing import (
    categorize_processing_error,
    create_chunking_strategy,
    handle_error_with_recovery,
    process_config_setting,
    route_command,
)
from shard_markdown.core.models import ChunkingConfig
from shard_markdown.utils.errors import (
    ChromaDBError,
    ConfigurationError,
    InputValidationError,
    NetworkError,
    ProcessingError,
)


class TestRouteCommand:
    """Test command routing using pattern matching."""

    def test_process_file_command(self) -> None:
        """Test routing for process file command."""
        args = Namespace(
            input_paths=["test.md"],
            collection="test-collection",
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Mock the handler function
        with pytest.MonkeyPatch.context() as mp:
            handler_mock = Mock(return_value=0)
            mp.setattr(
                "shard_markdown.cli.routing.handle_file_processing", handler_mock
            )

            result = route_command("process", "file", args)

            assert result == 0
            handler_mock.assert_called_once_with(args)

    def test_process_directory_command(self) -> None:
        """Test routing for process directory command."""
        args = Namespace(
            input_paths=["./docs"],
            collection="docs-collection",
            recursive=True,
        )

        with pytest.MonkeyPatch.context() as mp:
            handler_mock = Mock(return_value=0)
            mp.setattr(
                "shard_markdown.cli.routing.handle_directory_processing", handler_mock
            )

            result = route_command("process", "directory", args)

            assert result == 0
            handler_mock.assert_called_once_with(args)

    def test_collections_list_command(self) -> None:
        """Test routing for collections list command."""
        args = Namespace(format="table", show_metadata=False)

        with pytest.MonkeyPatch.context() as mp:
            handler_mock = Mock(return_value=0)
            mp.setattr(
                "shard_markdown.cli.routing.handle_collection_listing", handler_mock
            )

            result = route_command("collections", "list", args)

            assert result == 0
            handler_mock.assert_called_once_with(args)

    def test_collections_create_command(self) -> None:
        """Test routing for collections create command."""
        args = Namespace(name="new-collection", description="Test collection")

        with pytest.MonkeyPatch.context() as mp:
            handler_mock = Mock(return_value=0)
            mp.setattr(
                "shard_markdown.cli.routing.handle_collection_creation", handler_mock
            )

            result = route_command("collections", "create", args)

            assert result == 0
            handler_mock.assert_called_once_with(args)

    def test_collections_delete_command(self) -> None:
        """Test routing for collections delete command."""
        args = Namespace(name="old-collection", force=False)

        with pytest.MonkeyPatch.context() as mp:
            handler_mock = Mock(return_value=0)
            mp.setattr(
                "shard_markdown.cli.routing.handle_collection_deletion", handler_mock
            )

            result = route_command("collections", "delete", args)

            assert result == 0
            handler_mock.assert_called_once_with(args)

    def test_query_search_command(self) -> None:
        """Test routing for query search command."""
        args = Namespace(
            query_text="test query",
            collection="test-collection",
            limit=10,
        )

        with pytest.MonkeyPatch.context() as mp:
            handler_mock = Mock(return_value=0)
            mp.setattr("shard_markdown.cli.routing.handle_search_query", handler_mock)

            result = route_command("query", "search", args)

            assert result == 0
            handler_mock.assert_called_once_with(args)

    def test_query_similar_command(self) -> None:
        """Test routing for query similar command."""
        args = Namespace(
            query_text="similar content",
            collection="test-collection",
            threshold=0.7,
        )

        with pytest.MonkeyPatch.context() as mp:
            handler_mock = Mock(return_value=0)
            mp.setattr(
                "shard_markdown.cli.routing.handle_similarity_search", handler_mock
            )

            result = route_command("query", "similar", args)

            assert result == 0
            handler_mock.assert_called_once_with(args)

    def test_config_show_command(self) -> None:
        """Test routing for config show command."""
        args = Namespace(format="yaml", section=None)

        with pytest.MonkeyPatch.context() as mp:
            handler_mock = Mock(return_value=0)
            mp.setattr("shard_markdown.cli.routing.handle_config_display", handler_mock)

            result = route_command("config", "show", args)

            assert result == 0
            handler_mock.assert_called_once_with(args)

    def test_config_set_command(self) -> None:
        """Test routing for config set command."""
        args = Namespace(key="chunking.default_size", value="1500")

        with pytest.MonkeyPatch.context() as mp:
            handler_mock = Mock(return_value=0)
            mp.setattr("shard_markdown.cli.routing.handle_config_update", handler_mock)

            result = route_command("config", "set", args)

            assert result == 0
            handler_mock.assert_called_once_with(args)

    def test_unknown_command_pattern(self) -> None:
        """Test routing for unknown command returns error code."""
        args = Namespace()

        result = route_command("unknown", "command", args)

        assert result == 1  # Error exit code

    def test_unknown_subcommand_pattern(self) -> None:
        """Test routing for unknown subcommand returns error code."""
        args = Namespace()

        result = route_command("process", "unknown", args)

        assert result == 1  # Error exit code


class TestCreateChunkingStrategy:
    """Test chunking strategy creation using pattern matching."""

    def test_create_semantic_strategy(self) -> None:
        """Test creating semantic chunking strategy."""
        options = ChunkingConfig(chunk_size=1000, overlap=200, method="semantic")

        strategy = create_chunking_strategy("semantic", options)

        assert strategy is not None
        assert hasattr(strategy, "chunk_document")

    def test_create_fixed_strategy(self) -> None:
        """Test creating fixed chunking strategy."""
        options = ChunkingConfig(chunk_size=1000, overlap=200, method="fixed")

        strategy = create_chunking_strategy("fixed", options)

        assert strategy is not None
        assert hasattr(strategy, "chunk_document")

    def test_create_sentence_strategy(self) -> None:
        """Test creating sentence chunking strategy."""
        options = ChunkingConfig(chunk_size=1000, overlap=200, method="sentence")

        strategy = create_chunking_strategy("sentence", options)

        assert strategy is not None
        assert hasattr(strategy, "chunk_document")

    def test_create_paragraph_strategy(self) -> None:
        """Test creating paragraph chunking strategy."""
        options = ChunkingConfig(chunk_size=1000, overlap=200, method="paragraph")

        strategy = create_chunking_strategy("paragraph", options)

        assert strategy is not None
        assert hasattr(strategy, "chunk_document")

    def test_create_markdown_strategy(self) -> None:
        """Test creating markdown structure chunking strategy."""
        options = ChunkingConfig(chunk_size=1000, overlap=200, method="markdown")

        strategy = create_chunking_strategy("markdown", options)

        assert strategy is not None
        assert hasattr(strategy, "chunk_document")

    def test_create_unknown_strategy_raises_error(self) -> None:
        """Test creating unknown strategy raises ValueError."""
        options = ChunkingConfig(chunk_size=1000, overlap=200, method="unknown")

        with pytest.raises(ValueError, match="Unknown chunking strategy"):
            create_chunking_strategy("unknown", options)


class TestCategorizeProcessingError:
    """Test error categorization using pattern matching."""

    def test_categorize_file_access_error(self) -> None:
        """Test categorizing file access errors."""
        error = FileNotFoundError("File not found")
        context = Mock()

        category, message, exit_code = categorize_processing_error(error, context)

        assert category == "FILE_ACCESS"
        assert "file access" in message.lower()
        assert exit_code == 2

    def test_categorize_permission_error(self) -> None:
        """Test categorizing permission errors."""
        error = PermissionError("Permission denied")
        context = Mock()

        category, message, exit_code = categorize_processing_error(error, context)

        assert category == "PERMISSION"
        assert "permission" in message.lower()
        assert exit_code == 3

    def test_categorize_processing_error_type(self) -> None:
        """Test categorizing ProcessingError."""
        error = ProcessingError("Processing failed")
        context = Mock()

        category, message, exit_code = categorize_processing_error(error, context)

        assert category == "PROCESSING"
        assert "processing" in message.lower()
        assert exit_code == 4

    def test_categorize_chromadb_error(self) -> None:
        """Test categorizing ChromaDB errors."""
        error = ChromaDBError("Database connection failed")
        context = Mock()

        category, message, exit_code = categorize_processing_error(error, context)

        assert category == "DATABASE"
        assert "database" in message.lower()
        assert exit_code == 5

    def test_categorize_validation_error(self) -> None:
        """Test categorizing validation errors."""
        error = InputValidationError("Invalid input")
        context = Mock()

        category, message, exit_code = categorize_processing_error(error, context)

        assert category == "VALIDATION"
        assert "validation" in message.lower()
        assert exit_code == 6

    def test_categorize_config_error(self) -> None:
        """Test categorizing configuration errors."""
        error = ConfigurationError("Invalid configuration")
        context = Mock()

        category, message, exit_code = categorize_processing_error(error, context)

        assert category == "CONFIG"
        assert "configuration" in message.lower()
        assert exit_code == 7

    def test_categorize_unknown_error(self) -> None:
        """Test categorizing unknown errors."""
        error = RuntimeError("Unknown error")
        context = Mock()

        category, message, exit_code = categorize_processing_error(error, context)

        assert category == "UNKNOWN"
        assert "unknown" in message.lower()
        assert exit_code == 1


class TestProcessConfigSetting:
    """Test config setting processing using pattern matching."""

    def test_process_integer_config(self) -> None:
        """Test processing integer configuration values."""
        key, value = process_config_setting("chunk_size", "1500")

        assert key == "chunk_size"
        assert value == 1500
        assert isinstance(value, int)

    def test_process_float_config(self) -> None:
        """Test processing float configuration values."""
        key, value = process_config_setting("overlap_percentage", "0.2")

        assert key == "overlap_percentage"
        assert value == 0.2
        assert isinstance(value, float)

    def test_process_boolean_true_config(self) -> None:
        """Test processing boolean true configuration values."""
        for true_value in ["true", "True", "TRUE", "yes", "1"]:
            key, value = process_config_setting("enable_async", true_value)

            assert key == "enable_async"
            assert value is True
            assert isinstance(value, bool)

    def test_process_boolean_false_config(self) -> None:
        """Test processing boolean false configuration values."""
        for false_value in ["false", "False", "FALSE", "no", "0"]:
            key, value = process_config_setting("enable_async", false_value)

            assert key == "enable_async"
            assert value is False
            assert isinstance(value, bool)

    def test_process_string_config(self) -> None:
        """Test processing string configuration values."""
        key, value = process_config_setting("chromadb_host", "localhost")

        assert key == "chromadb_host"
        assert value == "localhost"
        assert isinstance(value, str)

    def test_process_unknown_config_key(self) -> None:
        """Test processing unknown configuration keys returns string."""
        key, value = process_config_setting("unknown_key", "some_value")

        assert key == "unknown_key"
        assert value == "some_value"
        assert isinstance(value, str)

    def test_process_invalid_integer_config(self) -> None:
        """Test processing invalid integer values."""
        with pytest.raises(ValueError, match="Invalid integer value"):
            process_config_setting("chunk_size", "not_a_number")

    def test_process_invalid_float_config(self) -> None:
        """Test processing invalid float values."""
        with pytest.raises(ValueError, match="Invalid float value"):
            process_config_setting("overlap_percentage", "not_a_float")


class TestHandleErrorWithRecovery:
    """Test error handling with pattern-based recovery strategies."""

    def test_handle_network_error_with_retry(self) -> None:
        """Test handling network errors with retry strategy."""
        error = NetworkError("Connection timeout")
        context = Mock()
        context.retry_count = 0
        context.max_retries = 3

        with pytest.MonkeyPatch.context() as mp:
            retry_mock = Mock(return_value=0)
            mp.setattr("shard_markdown.cli.routing._retry_with_backoff", retry_mock)

            result = handle_error_with_recovery(error, context)

            assert result == 0
            retry_mock.assert_called_once()

    def test_handle_config_error_with_reset(self) -> None:
        """Test handling config errors with reset strategy."""
        error = ConfigurationError("Invalid config")
        context = Mock()

        with pytest.MonkeyPatch.context() as mp:
            reset_mock = Mock(return_value=0)
            mp.setattr("shard_markdown.cli.routing._reset_to_defaults", reset_mock)

            result = handle_error_with_recovery(error, context)

            assert result == 0
            reset_mock.assert_called_once()

    def test_handle_file_error_with_skip(self) -> None:
        """Test handling file errors with skip strategy."""
        error = FileNotFoundError("File not found")
        context = Mock()
        context.continue_on_error = True

        with pytest.MonkeyPatch.context() as mp:
            skip_mock = Mock(return_value=0)
            mp.setattr("shard_markdown.cli.routing._skip_and_continue", skip_mock)

            result = handle_error_with_recovery(error, context)

            assert result == 0
            skip_mock.assert_called_once()

    def test_handle_permission_error_with_suggest(self) -> None:
        """Test handling permission errors with suggestion strategy."""
        error = PermissionError("Permission denied")
        context = Mock()

        with pytest.MonkeyPatch.context() as mp:
            suggest_mock = Mock(return_value=3)
            mp.setattr("shard_markdown.cli.routing._suggest_fix", suggest_mock)

            result = handle_error_with_recovery(error, context)

            assert result == 3
            suggest_mock.assert_called_once()

    def test_handle_unknown_error_with_abort(self) -> None:
        """Test handling unknown errors with abort strategy."""
        error = RuntimeError("Unknown error")
        context = Mock()

        result = handle_error_with_recovery(error, context)

        assert result == 1  # Abort with general error code


class ProcessingContext:
    """Mock processing context for testing."""

    def __init__(self) -> None:
        """Initialize mock processing context."""
        self.retry_count = 0
        self.max_retries = 3
        self.continue_on_error = True
