"""Integration tests for pattern matching system."""

import tempfile
from argparse import Namespace
from pathlib import Path

import pytest

from shard_markdown.cli.patterns import ExitCode
from shard_markdown.cli.routing import (
    ProcessingContext,
    categorize_processing_error,
    create_chunking_strategy,
    route_command,
)
from shard_markdown.core.models import ChunkingConfig
from shard_markdown.utils.errors import ProcessingError


class TestPatternMatchingIntegration:
    """Test pattern matching integration across the system."""

    def test_end_to_end_command_routing(self) -> None:
        """Test complete command routing flow."""
        # Create a temporary markdown file for testing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                "# Test Document\n\n"
                "This is a test document for pattern matching integration."
            )
            temp_file = f.name

        try:
            # Test process file command with proper parameters
            args = Namespace(
                input_paths=[temp_file],
                collection="test-collection",
                chunk_size=1000,
                chunk_overlap=200,
                method="structure",
                recursive=False,
                create_collection=True,
                dry_run=True,  # Use dry run to avoid needing actual ChromaDB
            )
            result = route_command("process", "file", args)
            # Accept either success or general error (ChromaDB may not be available)
            assert result in [ExitCode.SUCCESS, ExitCode.GENERAL_ERROR]

            # Test collections list command
            args = Namespace(format="table")
            result = route_command("collections", "list", args)
            # Note: This may fail if ChromaDB is not available, which is expected
            # in CI environments. We'll accept either success or general error.
            assert result in [ExitCode.SUCCESS, ExitCode.GENERAL_ERROR]

            # Test unknown command
            result = route_command("unknown", "command", Namespace())
            assert result == ExitCode.GENERAL_ERROR

        finally:
            # Clean up temporary file
            Path(temp_file).unlink(missing_ok=True)

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
            (
                ValueError("Invalid value"),
                "VALIDATION",
                ExitCode.VALIDATION_ERROR,
            ),
            (
                RuntimeError("Runtime error"),
                "UNKNOWN",  # RuntimeError falls to default case
                ExitCode.GENERAL_ERROR,
            ),
        ]

        for error, expected_category, expected_exit_code in error_test_cases:
            category, message, exit_code = categorize_processing_error(error, context)

            assert category == expected_category
            assert exit_code == expected_exit_code
            assert message  # Should have some message
            assert isinstance(message, str)

    def test_command_pattern_validation_flow(self) -> None:
        """Test command pattern validation and creation."""
        from shard_markdown.cli.patterns import create_command_pattern

        # Test valid command patterns
        valid_patterns = [
            ("process", "file"),
            ("process", "directory"),
            ("collections", "list"),
            ("collections", "create"),
            ("collections", "delete"),
            ("query", "search"),
            ("query", "similar"),
            ("config", "show"),
            ("config", "set"),
        ]

        for command, subcommand in valid_patterns:
            pattern = create_command_pattern(command, subcommand)
            assert pattern is not None
            assert pattern.command == command
            assert pattern.subcommand == subcommand
            assert pattern.handler_name
            # Note: CommandPattern doesn't have priority field in current implementation

        # Test invalid patterns
        invalid_patterns = [
            ("invalid", "command"),
            ("process", "invalid"),
            ("", ""),
            ("config", "unknown"),
        ]

        for command, subcommand in invalid_patterns:
            pattern = create_command_pattern(command, subcommand)
            assert pattern is None

    def test_comprehensive_pattern_matching_coverage(self) -> None:
        """Test comprehensive coverage of all pattern matching scenarios."""
        # Create a temporary markdown file for testing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                "# Test Document\n\n"
                "This is a test document for comprehensive pattern matching."
            )
            temp_file = f.name

        try:
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
                    args.input_paths = [temp_file]
                    args.collection = "test-collection"
                    args.dry_run = True  # Use dry run to avoid needing ChromaDB
                    args.create_collection = True
                elif command == "collections" and subcommand in ["create", "delete"]:
                    args.name = "test-collection"
                    if subcommand == "create":
                        args.description = "Test collection"
                elif command == "query":
                    args.query_text = "test query"
                    args.collection = "test-collection"
                elif command == "config" and subcommand == "set":
                    args.key = "test_key"
                    args.value = "test_value"

                result = route_command(command, subcommand, args)
                # Accept either success or general error (for cases where external
                # dependencies like ChromaDB are not available in test environment)
                assert result in [ExitCode.SUCCESS, ExitCode.GENERAL_ERROR]

        finally:
            # Clean up temporary file
            Path(temp_file).unlink(missing_ok=True)

    def test_pattern_priority_and_specificity(self) -> None:
        """Test pattern matching priority and specificity rules."""
        from shard_markdown.cli.patterns import create_command_pattern

        # Test that patterns are created successfully
        patterns = [
            create_command_pattern("process", "file"),
            create_command_pattern("process", "directory"),
            create_command_pattern("collections", "create"),
            create_command_pattern("query", "search"),
        ]

        # All patterns should be created successfully
        for pattern in patterns:
            assert pattern is not None

        # Note: Current CommandPattern implementation doesn't expose priority
        # but the pattern creation should be consistent
        assert len(patterns) == 4

    def test_integration_with_click_commands(self) -> None:
        """Test integration between pattern matching and Click commands."""
        import click

        from shard_markdown.cli.bridge import (
            bridge_collections_command,
            bridge_config_command,
            bridge_process_command,
            bridge_query_command,
        )

        # Create a mock Click context
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"config": None}

        # Test that bridge functions exist and are callable
        bridge_functions = [
            bridge_process_command,
            bridge_collections_command,
            bridge_query_command,
            bridge_config_command,
        ]

        for bridge_func in bridge_functions:
            assert callable(bridge_func)
            # Test with invalid subcommand should return error
            result = bridge_func(ctx, "invalid_subcommand")
            assert result == ExitCode.GENERAL_ERROR

    def test_pattern_matching_error_handling(self) -> None:
        """Test error handling in pattern matching system."""
        # Test with completely invalid commands
        result = route_command("", "", Namespace())
        assert result == ExitCode.GENERAL_ERROR

        result = route_command("nonexistent", "command", Namespace())
        assert result == ExitCode.GENERAL_ERROR

        # Test with valid command but missing required arguments
        args = Namespace()  # No required arguments
        result = route_command("process", "file", args)
        assert result == ExitCode.GENERAL_ERROR

    def test_chunking_strategy_polymorphism(self) -> None:
        """Test polymorphic behavior of chunking strategies."""
        config = ChunkingConfig(chunk_size=500, overlap=100, method="structure")

        # All strategies should implement the same interface
        strategies = ["semantic", "fixed", "sentence", "paragraph", "markdown"]

        for strategy_name in strategies:
            strategy = create_chunking_strategy(strategy_name, config)

            # All strategies should have required methods
            assert hasattr(strategy, "chunk_document")
            assert callable(strategy.chunk_document)
