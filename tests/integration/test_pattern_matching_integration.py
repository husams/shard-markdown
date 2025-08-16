"""Integration tests for the pattern matching CLI system."""

import sys
from argparse import Namespace

import pytest

# Pattern matching tests require Python 3.10+
from shard_markdown.cli.patterns import ExitCode
from shard_markdown.cli.routing import (
    ProcessingContext,
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


class TestPatternMatchingIntegration:
    """Integration tests for the complete pattern matching system."""

    def test_end_to_end_command_routing(self) -> None:
        """Test complete command routing flow."""
        # Test process file command
        args = Namespace(input_paths=["test.md"])
        result = route_command("process", "file", args)
        assert result == ExitCode.SUCCESS

        # Test collections list command
        args = Namespace(format="table")
        result = route_command("collections", "list", args)
        assert result == ExitCode.SUCCESS

        # Test unknown command
        result = route_command("unknown", "command", Namespace())
        assert result == ExitCode.GENERAL_ERROR

    def test_chunking_strategy_creation_flow(self) -> None:
        """Test chunking strategy creation with different options."""
        config = ChunkingConfig(chunk_size=1000, overlap=200, method="fixed")

        # Test all supported strategies
        strategies = ["semantic", "fixed", "sentence", "paragraph", "markdown"]
        for strategy_name in strategies:
            strategy = create_chunking_strategy(strategy_name, config)
            assert strategy is not None
            assert hasattr(strategy, "chunk_document")

        # Test unknown strategy
        with pytest.raises(ValueError, match="Unknown chunking strategy"):
            create_chunking_strategy("unknown", config)

    def test_error_categorization_and_recovery_flow(self) -> None:
        """Test complete error categorization and recovery flow."""
        context = ProcessingContext()

        # Test different error types and their categorization
        error_test_cases = [
            (
                FileNotFoundError("File not found"),
                "FILE_ACCESS",
                ExitCode.FILE_ACCESS_ERROR,
            ),
            (
                PermissionError("Permission denied"),
                "PERMISSION",
                ExitCode.PERMISSION_ERROR,
            ),
            (
                ProcessingError("Processing failed"),
                "PROCESSING",
                ExitCode.PROCESSING_ERROR,
            ),
            (ChromaDBError("Database error"), "DATABASE", ExitCode.DATABASE_ERROR),
            (
                InputValidationError("Invalid input"),
                "VALIDATION",
                ExitCode.VALIDATION_ERROR,
            ),
            (ConfigurationError("Config error"), "CONFIG", ExitCode.CONFIG_ERROR),
            (RuntimeError("Unknown error"), "UNKNOWN", ExitCode.GENERAL_ERROR),
        ]

        for error, expected_category, expected_exit_code in error_test_cases:
            # Test categorization
            category, message, exit_code = categorize_processing_error(error, context)
            assert category == expected_category
            assert exit_code == expected_exit_code
            assert str(error) in message

            # Test recovery (reset context for each test)
            context = ProcessingContext()
            recovery_result = handle_error_with_recovery(error, context)
            assert isinstance(recovery_result, int)
            assert 0 <= recovery_result <= 7  # Valid exit code range

    def test_config_setting_processing_flow(self) -> None:
        """Test configuration setting processing with type validation."""
        test_cases = [
            # Integer configurations
            ("chunk_size", "1500", 1500),
            ("batch_size", "10", 10),
            # Float configurations
            ("similarity_threshold", "0.8", 0.8),
            ("overlap_percentage", "0.2", 0.2),
            # Boolean configurations
            ("enable_async", "true", True),
            ("debug_mode", "false", False),
            ("verbose", "1", True),
            ("recursive", "0", False),
            # String configurations
            ("chromadb_host", "localhost", "localhost"),
            ("log_level", "INFO", "INFO"),
        ]

        for key, value, expected in test_cases:
            processed_key, processed_value = process_config_setting(key, value)
            assert processed_key == key
            assert processed_value == expected
            assert isinstance(processed_value, type(expected))

    def test_config_validation_errors(self) -> None:
        """Test configuration validation error handling."""
        # Test invalid integer
        with pytest.raises(ValueError, match="Invalid integer value"):
            process_config_setting("chunk_size", "not_a_number")

        # Test invalid float
        with pytest.raises(ValueError, match="Invalid float value"):
            process_config_setting("similarity_threshold", "not_a_float")

        # Test invalid boolean
        with pytest.raises(ValueError, match="Invalid boolean value"):
            process_config_setting("enable_async", "maybe")

    def test_error_recovery_strategies(self) -> None:
        """Test different error recovery strategies."""
        context = ProcessingContext()

        # Test retry strategy (network errors)
        network_error = NetworkError("Connection timeout")
        result = handle_error_with_recovery(network_error, context)
        assert result == ExitCode.SUCCESS
        assert context.retry_count == 1

        # Test suggest fix strategy (permission errors)
        context = ProcessingContext()
        permission_error = PermissionError("Access denied")
        result = handle_error_with_recovery(permission_error, context)
        assert result == ExitCode.PERMISSION_ERROR

        # Test skip and continue strategy (file access errors)
        context = ProcessingContext()
        file_error = FileNotFoundError("File not found")
        result = handle_error_with_recovery(file_error, context)
        assert result == ExitCode.SUCCESS

        # Test reset to defaults strategy (config errors)
        context = ProcessingContext()
        config_error = ConfigurationError("Invalid config")
        result = handle_error_with_recovery(config_error, context)
        assert result == ExitCode.SUCCESS

    def test_comprehensive_pattern_matching_coverage(self) -> None:
        """Test comprehensive coverage of all pattern matching scenarios."""
        # Test all command patterns
        command_patterns = [
            ("process", "file", "handle_file_processing"),
            ("process", "directory", "handle_directory_processing"),
            ("collections", "list", "handle_collection_listing"),
            ("collections", "create", "handle_collection_creation"),
            ("collections", "delete", "handle_collection_deletion"),
            ("query", "search", "handle_search_query"),
            ("query", "similar", "handle_similarity_search"),
            ("config", "show", "handle_config_display"),
            ("config", "set", "handle_config_update"),
        ]

        for command, subcommand, _expected_handler in command_patterns:
            args = Namespace()
            # Add required attributes based on command type
            if command == "process":
                args.input_paths = ["test.md"]
            elif command == "collections" and subcommand in ["create", "delete"]:
                args.name = "test-collection"
            elif command == "query":
                args.query_text = "test query"
            elif command == "config" and subcommand == "set":
                args.key = "test_key"
                args.value = "test_value"

            result = route_command(command, subcommand, args)
            assert result == ExitCode.SUCCESS

    def test_pattern_matching_exhaustiveness(self) -> None:
        """Test that pattern matching handles all cases exhaustively."""
        # Test config type matching for all supported types
        config_type_tests = {
            "integer": ["chunk_size", "batch_size", "port"],
            "float": ["similarity_threshold", "overlap_percentage"],
            "boolean": ["enable_async", "debug_mode", "verbose"],
            "string": ["chromadb_host", "log_level", "output_format"],
        }

        for expected_type, keys in config_type_tests.items():
            for key in keys:
                processed_key, processed_value = process_config_setting(
                    key, "test_value" if expected_type == "string" else "1"
                )
                assert processed_key == key

        # Test error category matching for all error types
        error_categories = [
            (FileNotFoundError(), "FILE_ACCESS"),
            (PermissionError(), "PERMISSION"),
            (ProcessingError("test"), "PROCESSING"),
            (ChromaDBError("test"), "DATABASE"),
            (InputValidationError("test"), "VALIDATION"),
            (ConfigurationError("test"), "CONFIG"),
            (RuntimeError(), "UNKNOWN"),
        ]

        context = ProcessingContext()
        for error, expected_category in error_categories:
            category, _, _ = categorize_processing_error(error, context)
            assert category == expected_category

    def test_pattern_matching_performance(self) -> None:
        """Test that pattern matching performs well with many operations."""
        import time

        # Test command routing performance
        start_time = time.time()
        for _ in range(1000):
            args = Namespace(input_paths=["test.md"])
            route_command("process", "file", args)
        command_time = time.time() - start_time

        # Test config processing performance
        start_time = time.time()
        for _ in range(1000):
            process_config_setting("chunk_size", "1000")
        config_time = time.time() - start_time

        # Test error categorization performance
        start_time = time.time()
        context = ProcessingContext()
        for _ in range(1000):
            categorize_processing_error(FileNotFoundError(), context)
        error_time = time.time() - start_time

        # Assert reasonable performance (all operations should complete quickly)
        assert command_time < 1.0
        assert config_time < 1.0
        assert error_time < 1.0

    def test_pattern_matching_memory_usage(self) -> None:
        """Test that pattern matching doesn't create memory leaks."""
        import gc

        # Get initial memory usage
        gc.collect()
        initial_refs = sys.getrefcount(ProcessingContext)

        # Create many pattern matching operations
        contexts = []
        for i in range(100):
            context = ProcessingContext()
            contexts.append(context)

            # Perform various pattern matching operations
            args = Namespace(input_paths=[f"test_{i}.md"])
            route_command("process", "file", args)

            process_config_setting("chunk_size", str(1000 + i))

            categorize_processing_error(FileNotFoundError(f"Error {i}"), context)

        # Clean up and check memory
        del contexts
        gc.collect()
        final_refs = sys.getrefcount(ProcessingContext)

        # Memory usage should be reasonable (allowing for some variation)
        assert abs(final_refs - initial_refs) < 10
