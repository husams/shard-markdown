"""Bridge module to integrate pattern matching system with Click CLI.

This module provides the integration layer between the existing Click-based CLI
and the new pattern matching routing system, enabling gradual migration.
"""

import sys
from argparse import Namespace
from typing import Any

import click
from rich.console import Console

from .patterns import ExitCode


console = Console()


class ClickToPatternBridge:
    """Bridge between Click context and pattern matching system."""

    def __init__(self, ctx: click.Context) -> None:
        """Initialize bridge with Click context.

        Args:
            ctx: Click context containing CLI state and configuration
        """
        self.ctx = ctx
        self.config = ctx.obj.get("config") if ctx.obj else None
        self.verbose = ctx.obj.get("verbose", 0) if ctx.obj else 0
        self.quiet = ctx.obj.get("quiet", False) if ctx.obj else False

    def create_namespace(self, **kwargs: Any) -> Namespace:
        """Create argparse Namespace from Click context and additional arguments.

        Args:
            **kwargs: Additional arguments to include in namespace

        Returns:
            Namespace object for pattern matching system
        """
        # Base namespace with CLI context
        ns_dict = {
            "config": self.config,
            "verbose": self.verbose,
            "quiet": self.quiet,
        }

        # Add additional arguments
        ns_dict.update(kwargs)

        return Namespace(**ns_dict)

    def route_to_pattern_handler(
        self, command: str, subcommand: str, **kwargs: Any
    ) -> int:
        """Route command to pattern matching handler.

        Args:
            command: Main command name
            subcommand: Subcommand name
            **kwargs: Additional arguments for the command

        Returns:
            Exit code from pattern matching handler
        """
        # Import here to avoid circular import
        from .routing import route_command

        args = self.create_namespace(**kwargs)

        try:
            return route_command(command, subcommand, args)
        except Exception as e:
            if self.verbose > 1:
                console.print_exception()
            else:
                console.print(f"[red]Command execution failed: {str(e)}[/red]")
            return ExitCode.GENERAL_ERROR

    def handle_exit_code(self, exit_code: int) -> None:
        """Handle exit code from pattern matching system.

        Args:
            exit_code: Exit code from pattern handler
        """
        if exit_code != ExitCode.SUCCESS:
            sys.exit(exit_code)


def click_to_pattern_route(command: str, subcommand: str) -> Any:
    """Decorator to bridge Click commands to pattern matching handlers.

    Args:
        command: Main command name
        subcommand: Subcommand name

    Returns:
        Decorator function
    """

    def decorator(func: Any) -> Any:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract Click context
            ctx = None
            for arg in args:
                if isinstance(arg, click.Context):
                    ctx = arg
                    break

            if ctx is None:
                # Look for context in kwargs or use current context
                ctx = click.get_current_context()

            # Create bridge and route to pattern handler
            bridge = ClickToPatternBridge(ctx)

            # Filter out Click context from kwargs for pattern handler
            pattern_kwargs = {k: v for k, v in kwargs.items() if k not in ["ctx"]}

            exit_code = bridge.route_to_pattern_handler(
                command, subcommand, **pattern_kwargs
            )

            # Handle exit code
            bridge.handle_exit_code(exit_code)

            return None  # Click command should not return values

        return wrapper

    return decorator


def get_real_config_handler() -> Any:
    """Get real configuration handler function.

    This function provides access to the actual Click-based config handlers
    for the pattern matching system to call.

    Returns:
        Dictionary mapping subcommands to their Click handlers
    """
    from .commands.config import init, path, set, show

    return {
        "show": show,
        "set": set,
        "init": init,
        "path": path,
    }


def bridge_config_command(ctx: click.Context, subcommand: str, **kwargs: Any) -> int:
    """Bridge config commands to existing Click implementations.

    This function allows pattern matching handlers to call the actual
    Click-based config command implementations.

    Args:
        ctx: Click context
        subcommand: Config subcommand (show, set, init, path)
        **kwargs: Arguments for the config command

    Returns:
        Exit code (0 for success)
    """
    handlers = get_real_config_handler()

    if subcommand not in handlers:
        console.print(f"[red]Unknown config subcommand: {subcommand}[/red]")
        return ExitCode.GENERAL_ERROR

    try:
        handler = handlers[subcommand]

        # Call the Click handler with appropriate arguments using Click's invoke
        if subcommand == "show":
            ctx.invoke(
                handler,
                format=kwargs.get("format", "yaml"),
                section=kwargs.get("section"),
            )
        elif subcommand == "set":
            ctx.invoke(
                handler,
                key=kwargs.get("key", ""),
                value=kwargs.get("value", ""),
                is_global=kwargs.get("is_global", False),
                is_local=kwargs.get("is_local", False),
            )
        elif subcommand == "init":
            ctx.invoke(
                handler,
                is_global=kwargs.get("is_global", False),
                force=kwargs.get("force", False),
                template=kwargs.get("template"),
            )
        elif subcommand == "path":
            ctx.invoke(handler)

        return ExitCode.SUCCESS

    except click.Abort:
        # Click command was aborted (expected behavior for some errors)
        return ExitCode.GENERAL_ERROR
    except Exception as e:
        console.print(f"[red]Config command failed: {str(e)}[/red]")
        return ExitCode.GENERAL_ERROR


def bridge_collections_command(
    ctx: click.Context, subcommand: str, **kwargs: Any
) -> int:
    """Bridge collections commands to existing Click implementations.

    Args:
        ctx: Click context
        subcommand: Collections subcommand
        **kwargs: Arguments for the collections command

    Returns:
        Exit code (0 for success)
    """
    # Import here to avoid circular imports
    from .commands.collections import create, delete, list

    handlers = {
        "list": list,
        "create": create,
        "delete": delete,
    }

    if subcommand not in handlers:
        console.print(f"[red]Unknown collections subcommand: {subcommand}[/red]")
        return ExitCode.GENERAL_ERROR

    try:
        handler = handlers[subcommand]

        # Use Click's invoke mechanism
        if subcommand == "list":
            ctx.invoke(
                handler,
                format=kwargs.get("format", "table"),
                show_metadata=kwargs.get("show_metadata", False),
                filter=kwargs.get("filter", ""),
            )
        elif subcommand == "create":
            ctx.invoke(
                handler,
                name=kwargs.get("name", ""),
                description=kwargs.get("description", ""),
                embedding_function=kwargs.get("embedding_function", "default"),
                metadata=kwargs.get("metadata", {}),
            )
        elif subcommand == "delete":
            ctx.invoke(
                handler,
                name=kwargs.get("name", ""),
                force=kwargs.get("force", False),
                backup=kwargs.get("backup", False),
            )

        return ExitCode.SUCCESS

    except click.Abort:
        return ExitCode.GENERAL_ERROR
    except Exception as e:
        console.print(f"[red]Collections command failed: {str(e)}[/red]")
        return ExitCode.GENERAL_ERROR


def bridge_process_command(ctx: click.Context, subcommand: str, **kwargs: Any) -> int:
    """Bridge process commands to existing Click implementations.

    Args:
        ctx: Click context
        subcommand: Process subcommand (should be empty for main process command)
        **kwargs: Arguments for the process command

    Returns:
        Exit code (0 for success)
    """
    # Import here to avoid circular imports
    from .commands.process import process as process_handler

    try:
        # The process command doesn't have subcommands in current implementation
        # All arguments are passed as kwargs

        # Convert input_paths to tuple as expected by Click command
        input_paths = kwargs.get("input_paths", [])
        if isinstance(input_paths, list):
            input_paths = tuple(input_paths)

        # Use Click's invoke mechanism instead of calling the handler directly
        ctx.invoke(
            process_handler,
            input_paths=input_paths,
            collection=kwargs.get("collection", ""),
            chunk_size=kwargs.get("chunk_size"),
            chunk_overlap=kwargs.get("chunk_overlap"),
            chunk_method=kwargs.get("method", "structure"),
            recursive=kwargs.get("recursive", False),
            create_collection=kwargs.get("create_collection", False),
            clear_collection=kwargs.get("clear_collection", False),
            dry_run=kwargs.get("dry_run", False),
            collection_metadata=kwargs.get("collection_metadata"),
        )

        return ExitCode.SUCCESS

    except click.Abort:
        return ExitCode.GENERAL_ERROR
    except Exception as e:
        console.print(f"[red]Process command failed: {str(e)}[/red]")
        # console.print_exception()  # Disable debug output
        return ExitCode.GENERAL_ERROR


def bridge_query_command(ctx: click.Context, subcommand: str, **kwargs: Any) -> int:
    """Bridge query commands to existing Click implementations.

    Args:
        ctx: Click context
        subcommand: Query subcommand
        **kwargs: Arguments for the query command

    Returns:
        Exit code (0 for success)
    """
    # Import here to avoid circular imports
    from .commands.query import search

    # Only search is available, map "similar" to search with high similarity
    handlers = {
        "search": search,
        "similar": search,  # Map similar to search for now
    }

    if subcommand not in handlers:
        console.print(f"[red]Unknown query subcommand: {subcommand}[/red]")
        return ExitCode.GENERAL_ERROR

    try:
        handler = handlers[subcommand]

        if subcommand in ("search", "similar"):
            # For similarity search, we could modify the search behavior
            search_kwargs = {
                "collection": kwargs.get("collection", ""),
                "query_text": kwargs.get("query_text", ""),
                "limit": kwargs.get("limit", 10),
                "format": kwargs.get("format", "table"),
                "include_metadata": kwargs.get("include_metadata", False),
                "similarity_threshold": kwargs.get("threshold", 0.7)
                if subcommand == "similar"
                else None,
            }

            # Filter out None values for the actual handler call
            filtered_kwargs = {k: v for k, v in search_kwargs.items() if v is not None}

            # Use Click's invoke mechanism
            ctx.invoke(handler, **filtered_kwargs)

        return ExitCode.SUCCESS

    except click.Abort:
        return ExitCode.GENERAL_ERROR
    except Exception as e:
        console.print(f"[red]Query command failed: {str(e)}[/red]")
        return ExitCode.GENERAL_ERROR
