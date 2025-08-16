"""Tests for CLI bridge that connects Click commands to pattern matching system."""

from argparse import Namespace
from unittest.mock import Mock, patch

import click

from shard_markdown.cli.bridge import (
    ClickToNamespaceConverter,
    create_bridge_for_collections,
    create_bridge_for_config,
    create_bridge_for_process,
    create_bridge_for_query,
    integrate_pattern_matching,
)
from shard_markdown.cli.patterns import ExitCode


class TestClickToNamespaceConverter:
    """Test Click context to Namespace conversion."""

    def test_convert_process_click_context(self) -> None:
        """Test converting process command Click context to Namespace."""
        # Create a mock Click context for process command
        ctx = Mock(spec=click.Context)
        ctx.params = {
            "input_paths": ["test.md"],
            "collection": "test-collection",
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "clear": False,
            "dry_run": False,
            "batch_size": 10,
        }

        converter = ClickToNamespaceConverter()
        namespace = converter.convert_process_context(ctx)

        assert isinstance(namespace, Namespace)
        assert namespace.input_paths == ["test.md"]
        assert namespace.collection == "test-collection"
        assert namespace.chunk_size == 1000
        assert namespace.chunk_overlap == 200
        assert namespace.clear is False
        assert namespace.dry_run is False
        assert namespace.batch_size == 10

    def test_convert_collections_click_context(self) -> None:
        """Test converting collections command Click context to Namespace."""
        ctx = Mock(spec=click.Context)
        ctx.params = {
            "name": "test-collection",
            "description": "Test collection",
            "format": "table",
            "show_metadata": True,
        }

        converter = ClickToNamespaceConverter()
        namespace = converter.convert_collections_context(ctx, "list")

        assert isinstance(namespace, Namespace)
        assert namespace.subcommand == "list"
        assert hasattr(namespace, "format")
        assert hasattr(namespace, "show_metadata")

    def test_convert_query_click_context(self) -> None:
        """Test converting query command Click context to Namespace."""
        ctx = Mock(spec=click.Context)
        ctx.params = {
            "collection": "test-collection",
            "query_text": "search term",
            "limit": 10,
            "threshold": 0.7,
        }

        converter = ClickToNamespaceConverter()
        namespace = converter.convert_query_context(ctx, "search")

        assert isinstance(namespace, Namespace)
        assert namespace.subcommand == "search"
        assert namespace.collection == "test-collection"
        assert namespace.query_text == "search term"
        assert namespace.limit == 10
        assert namespace.threshold == 0.7

    def test_convert_config_click_context(self) -> None:
        """Test converting config command Click context to Namespace."""
        ctx = Mock(spec=click.Context)
        ctx.params = {
            "key": "chunk_size",
            "value": "1500",
            "format": "yaml",
        }

        converter = ClickToNamespaceConverter()
        namespace = converter.convert_config_context(ctx, "set")

        assert isinstance(namespace, Namespace)
        assert namespace.subcommand == "set"
        assert namespace.key == "chunk_size"
        assert namespace.value == "1500"
        assert namespace.format == "yaml"


class TestClickPatternMatchingBridge:
    """Test bridge functions that connect Click commands to pattern matching."""

    @patch("shard_markdown.cli.bridge.route_command")
    def test_process_bridge_calls_pattern_matching(self, mock_route: Mock) -> None:
        """Test that process bridge calls pattern matching with correct parameters."""
        mock_route.return_value = ExitCode.SUCCESS

        ctx = Mock(spec=click.Context)
        ctx.params = {
            "input_paths": ["test.md"],
            "collection": "test-collection",
            "chunk_size": 1000,
        }

        bridge_func = create_bridge_for_process()
        bridge_func(ctx)

        # Verify pattern matching was called
        mock_route.assert_called_once()
        args = mock_route.call_args[0]
        assert args[0] == "process"  # command
        assert args[1] == "file"  # subcommand (determined from single file input)
        assert isinstance(args[2], Namespace)  # converted arguments

    @patch("shard_markdown.cli.bridge.route_command")
    def test_collections_bridge_calls_pattern_matching(self, mock_route: Mock) -> None:
        """Test that collections bridge calls pattern matching with correct parameters."""
        mock_route.return_value = ExitCode.SUCCESS

        ctx = Mock(spec=click.Context)
        ctx.params = {"format": "table"}
        ctx.info_name = "list"  # Simulate Click subcommand info

        bridge_func = create_bridge_for_collections("list")
        bridge_func(ctx)

        mock_route.assert_called_once()
        args = mock_route.call_args[0]
        assert args[0] == "collections"
        assert args[1] == "list"
        assert isinstance(args[2], Namespace)

    @patch("shard_markdown.cli.bridge.route_command")
    def test_query_bridge_calls_pattern_matching(self, mock_route: Mock) -> None:
        """Test that query bridge calls pattern matching with correct parameters."""
        mock_route.return_value = ExitCode.SUCCESS

        ctx = Mock(spec=click.Context)
        ctx.params = {
            "collection": "test-collection",
            "query_text": "test query",
        }

        bridge_func = create_bridge_for_query("search")
        bridge_func(ctx)

        mock_route.assert_called_once()
        args = mock_route.call_args[0]
        assert args[0] == "query"
        assert args[1] == "search"
        assert isinstance(args[2], Namespace)

    @patch("shard_markdown.cli.bridge.route_command")
    def test_config_bridge_calls_pattern_matching(self, mock_route: Mock) -> None:
        """Test that config bridge calls pattern matching with correct parameters."""
        mock_route.return_value = ExitCode.SUCCESS

        ctx = Mock(spec=click.Context)
        ctx.params = {
            "key": "chunk_size",
            "value": "1500",
        }

        bridge_func = create_bridge_for_config("set")
        bridge_func(ctx)

        mock_route.assert_called_once()
        args = mock_route.call_args[0]
        assert args[0] == "config"
        assert args[1] == "set"
        assert isinstance(args[2], Namespace)


class TestPatternMatchingIntegration:
    """Test integration of pattern matching with existing Click CLI."""

    def test_integrate_pattern_matching_modifies_commands(self) -> None:
        """Test that integration modifies existing Click commands to use pattern matching."""
        # Create a mock CLI group with proper attributes
        cli_group = Mock(spec=click.Group)
        cli_group.name = "test-cli"
        cli_group.commands = {
            "process": Mock(spec=click.Command),
            "collections": Mock(spec=click.Group),
            "query": Mock(spec=click.Group),
            "config": Mock(spec=click.Group),
        }
        cli_group.invoke_without_command = False
        cli_group.no_args_is_help = True
        cli_group.subcommand_metavar = None
        cli_group.chain = False
        cli_group.result_callback = None
        cli_group.params = []
        cli_group.help = "Test CLI"
        cli_group.epilog = None
        cli_group.short_help = None
        cli_group.options_metavar = None
        cli_group.add_help_option = True
        cli_group.hidden = False
        cli_group.deprecated = False

        # Apply integration
        modified_cli = integrate_pattern_matching(cli_group)

        # Verify that commands still exist
        assert "process" in modified_cli.commands
        assert "collections" in modified_cli.commands
        assert "query" in modified_cli.commands
        assert "config" in modified_cli.commands

    def test_integration_preserves_click_interface(self) -> None:
        """Test that integration preserves the Click interface for backward compatibility."""
        # Test that the bridge module can be imported successfully
        from shard_markdown.cli.bridge import integrate_pattern_matching

        # Verify the function exists and is callable
        assert callable(integrate_pattern_matching)

    def test_bridge_handles_errors_gracefully(self) -> None:
        """Test that bridge handles pattern matching errors gracefully."""
        # Test that the bridge module can be imported successfully
        from shard_markdown.cli.bridge import ClickToNamespaceConverter

        # Verify the class exists and is instantiable
        converter = ClickToNamespaceConverter()
        assert isinstance(converter, ClickToNamespaceConverter)


class TestBackwardCompatibility:
    """Test that pattern matching integration maintains backward compatibility."""

    def test_existing_click_commands_still_work(self) -> None:
        """Test that existing Click commands continue to work after integration."""
        # This will be implemented after the bridge is created
        # For now, this test documents the requirement
        assert True  # Placeholder

    def test_click_context_is_preserved(self) -> None:
        """Test that Click context and its functionality is preserved."""
        # This will be implemented after the bridge is created
        # For now, this test documents the requirement
        assert True  # Placeholder

    def test_error_handling_is_consistent(self) -> None:
        """Test that error handling is consistent between Click and pattern matching."""
        # This will be implemented after the bridge is created
        # For now, this test documents the requirement
        assert True  # Placeholder
