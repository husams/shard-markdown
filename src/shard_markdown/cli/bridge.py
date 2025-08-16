"""Bridge module that connects Click CLI commands to pattern matching system.

This module provides the integration layer between the existing Click-based CLI
and the new pattern matching routing system, enabling incremental migration
while maintaining complete backward compatibility.
"""

from argparse import Namespace
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

from .routing import route_command


class ClickToNamespaceConverter:
    """Converts Click context objects to argparse Namespace objects."""

    def convert_process_context(self, ctx: click.Context) -> Namespace:
        """Convert process command Click context to Namespace.

        Args:
            ctx: Click context containing process command parameters

        Returns:
            Namespace object with process command arguments
        """
        params = ctx.params

        namespace = Namespace()
        namespace.input_paths = params.get("input_paths", [])
        namespace.collection = params.get("collection", "")
        namespace.chunk_size = params.get("chunk_size", 1000)
        namespace.chunk_overlap = params.get("chunk_overlap", 200)
        namespace.clear = params.get("clear", False)
        namespace.dry_run = params.get("dry_run", False)
        namespace.batch_size = params.get("batch_size", 10)
        namespace.strategy = params.get("strategy", "structure")
        namespace.recursive = params.get("recursive", False)
        namespace.force = params.get("force", False)

        return namespace

    def convert_collections_context(
        self, ctx: click.Context, subcommand: str
    ) -> Namespace:
        """Convert collections command Click context to Namespace.

        Args:
            ctx: Click context containing collections command parameters
            subcommand: The collections subcommand (list, create, delete, info)

        Returns:
            Namespace object with collections command arguments
        """
        params = ctx.params

        namespace = Namespace()
        namespace.subcommand = subcommand
        namespace.name = params.get("name", "")
        namespace.description = params.get("description", "")
        namespace.format = params.get("format", "table")
        namespace.show_metadata = params.get("show_metadata", False)
        namespace.force = params.get("force", False)

        return namespace

    def convert_query_context(self, ctx: click.Context, subcommand: str) -> Namespace:
        """Convert query command Click context to Namespace.

        Args:
            ctx: Click context containing query command parameters
            subcommand: The query subcommand (search, similar)

        Returns:
            Namespace object with query command arguments
        """
        params = ctx.params

        namespace = Namespace()
        namespace.subcommand = subcommand
        namespace.collection = params.get("collection", "")
        namespace.query_text = params.get("query_text", "")
        namespace.limit = params.get("limit", 10)
        namespace.threshold = params.get("threshold", 0.7)
        namespace.format = params.get("format", "table")
        namespace.show_scores = params.get("show_scores", False)

        return namespace

    def convert_config_context(self, ctx: click.Context, subcommand: str) -> Namespace:
        """Convert config command Click context to Namespace.

        Args:
            ctx: Click context containing config command parameters
            subcommand: The config subcommand (show, set)

        Returns:
            Namespace object with config command arguments
        """
        params = ctx.params

        namespace = Namespace()
        namespace.subcommand = subcommand
        namespace.key = params.get("key", "")
        namespace.value = params.get("value", "")
        namespace.format = params.get("format", "yaml")
        namespace.global_config = params.get("global", False)

        return namespace


def create_bridge_for_process() -> Callable[[click.Context], int]:
    """Create a bridge function for process commands.

    Returns:
        Bridge function that converts Click context to pattern matching call
    """
    converter = ClickToNamespaceConverter()

    def bridge(ctx: click.Context) -> int:
        """Bridge function for process commands."""
        namespace = converter.convert_process_context(ctx)

        # Determine subcommand based on input paths
        input_paths = namespace.input_paths
        if len(input_paths) == 1:
            path = Path(input_paths[0])
            subcommand = "directory" if path.is_dir() else "file"
        else:
            subcommand = "directory"  # Multiple paths treated as directory processing

        return route_command("process", subcommand, namespace)

    return bridge


def create_bridge_for_collections(subcommand: str) -> Callable[[click.Context], int]:
    """Create a bridge function for collections commands.

    Args:
        subcommand: The collections subcommand (list, create, delete, info)

    Returns:
        Bridge function that converts Click context to pattern matching call
    """
    converter = ClickToNamespaceConverter()

    def bridge(ctx: click.Context) -> int:
        """Bridge function for collections commands."""
        namespace = converter.convert_collections_context(ctx, subcommand)
        return route_command("collections", subcommand, namespace)

    return bridge


def create_bridge_for_query(subcommand: str) -> Callable[[click.Context], int]:
    """Create a bridge function for query commands.

    Args:
        subcommand: The query subcommand (search, similar)

    Returns:
        Bridge function that converts Click context to pattern matching call
    """
    converter = ClickToNamespaceConverter()

    def bridge(ctx: click.Context) -> int:
        """Bridge function for query commands."""
        namespace = converter.convert_query_context(ctx, subcommand)
        return route_command("query", subcommand, namespace)

    return bridge


def create_bridge_for_config(subcommand: str) -> Callable[[click.Context], int]:
    """Create a bridge function for config commands.

    Args:
        subcommand: The config subcommand (show, set)

    Returns:
        Bridge function that converts Click context to pattern matching call
    """
    converter = ClickToNamespaceConverter()

    def bridge(ctx: click.Context) -> int:
        """Bridge function for config commands."""
        namespace = converter.convert_config_context(ctx, subcommand)
        return route_command("config", subcommand, namespace)

    return bridge


def integrate_pattern_matching(cli_group: click.Group) -> click.Group:
    """Integrate pattern matching routing with existing Click CLI.

    This function modifies the existing Click CLI to route commands through
    the pattern matching system while maintaining complete backward compatibility.

    Args:
        cli_group: The main CLI group to modify

    Returns:
        Modified CLI group with pattern matching integration
    """
    # Create a copy of the CLI group to avoid modifying the original
    integrated_cli = click.Group(
        name=cli_group.name,
        commands=dict(cli_group.commands),
        invoke_without_command=cli_group.invoke_without_command,
        no_args_is_help=cli_group.no_args_is_help,
        subcommand_metavar=cli_group.subcommand_metavar,
        chain=cli_group.chain,
        result_callback=cli_group.result_callback,
        params=cli_group.params,
        help=cli_group.help,
        epilog=cli_group.epilog,
        short_help=cli_group.short_help,
        options_metavar=cli_group.options_metavar,
        add_help_option=cli_group.add_help_option,
        hidden=cli_group.hidden,
        deprecated=cli_group.deprecated,
    )

    # For now, return the CLI group as-is since we're implementing incremental migration
    # The integration will be enhanced in subsequent phases
    return integrated_cli


def apply_bridge_to_command(
    command: click.Command, bridge_func: Callable[[click.Context], int]
) -> click.Command:
    """Apply bridge function to a Click command.

    Args:
        command: Click command to modify
        bridge_func: Bridge function to apply

    Returns:
        Modified Click command that uses pattern matching
    """
    # Store the original callback (for future reference)
    _ = command.callback

    def new_callback(*args: Any, **kwargs: Any) -> int:
        """New callback that routes through pattern matching."""
        # Get the Click context
        ctx = click.get_current_context()

        # Call the bridge function with the context
        return bridge_func(ctx)

    # Create a new command with the bridge callback
    bridged_command = click.Command(
        name=command.name,
        callback=new_callback,
        params=command.params,
        help=command.help,
        epilog=command.epilog,
        short_help=command.short_help,
        options_metavar=command.options_metavar,
        add_help_option=command.add_help_option,
        hidden=command.hidden,
        deprecated=command.deprecated,
    )

    return bridged_command


def convert_click_params_to_namespace(
    ctx: click.Context, command_info: dict[str, str]
) -> Namespace:
    """Convert Click context parameters to argparse Namespace.

    Args:
        ctx: Click context containing command parameters
        command_info: Dictionary with command and subcommand information

    Returns:
        Namespace object with converted parameters
    """
    converter = ClickToNamespaceConverter()
    command = command_info.get("command", "")
    subcommand = command_info.get("subcommand", "")

    # Route to appropriate converter based on command
    match command:
        case "process":
            return converter.convert_process_context(ctx)
        case "collections":
            return converter.convert_collections_context(ctx, subcommand)
        case "query":
            return converter.convert_query_context(ctx, subcommand)
        case "config":
            return converter.convert_config_context(ctx, subcommand)
        case _:
            # Generic conversion for unknown commands
            namespace = Namespace()
            for key, value in ctx.params.items():
                setattr(namespace, key, value)
            return namespace
