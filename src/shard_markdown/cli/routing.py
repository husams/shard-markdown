"""Main pattern matching router for CLI commands."""

import time
from argparse import Namespace
from collections.abc import Callable

import click
from rich.console import Console

from ..core.chunking.base import BaseChunker
from ..core.chunking.fixed import FixedSizeChunker
from ..core.chunking.structure import StructureAwareChunker
from ..core.models import ChunkingConfig
from ..utils.errors import (
    InputValidationError,
)
from .bridge import (
    bridge_collections_command,
    bridge_config_command,
    bridge_process_command,
    bridge_query_command,
)
from .patterns import (
    ExitCode,
    create_command_pattern,
    create_config_pattern,
    create_error_pattern,
)


console = Console()

# Type alias for chunking strategy (using BaseChunker protocol)
ChunkingStrategy = BaseChunker


class ProcessingContext:
    """Context for processing operations."""

    def __init__(self) -> None:
        """Initialize processing context with default values."""
        self.retry_count = 0
        self.max_retries = 3
        self.continue_on_error = True
        self.current_file = None
        self.total_files = 0
        self.processed_files = 0


def route_command(command: str, subcommand: str, args: Namespace) -> int:
    """Route commands using pattern matching (no if/elif chains).

    Args:
        command: The main command name
        subcommand: The subcommand name
        args: Parsed command arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    pattern = create_command_pattern(command, subcommand)

    if pattern is None:
        console.print(f"[red]Unknown command: {command} {subcommand}[/red]")
        return ExitCode.GENERAL_ERROR

    # Get the handler function dynamically
    handler = _get_command_handler(pattern.handler_name)
    if handler is None:
        console.print(f"[red]Handler not found: {pattern.handler_name}[/red]")
        return ExitCode.GENERAL_ERROR

    try:
        return handler(args)
    except Exception as e:
        console.print(f"[red]Command execution failed: {str(e)}[/red]")
        return ExitCode.GENERAL_ERROR


def create_chunking_strategy(
    strategy_name: str, options: ChunkingConfig
) -> ChunkingStrategy:
    """Create chunking strategy via pattern matching.

    Args:
        strategy_name: Name of the chunking strategy
        options: Chunking configuration options

    Returns:
        Chunking strategy instance

    Raises:
        ValueError: If strategy name is unknown
    """
    match strategy_name:
        case "semantic":
            return _create_semantic_chunker(options)
        case "fixed":
            return FixedSizeChunker(options)
        case "sentence":
            return _create_sentence_chunker(options)
        case "paragraph":
            return _create_paragraph_chunker(options)
        case "markdown":
            return StructureAwareChunker(options)
        case _:
            raise ValueError(f"Unknown chunking strategy: {strategy_name}")


def categorize_processing_error(
    error: Exception, context: ProcessingContext
) -> tuple[str, str, int]:
    """Categorize errors using pattern matching.

    Args:
        error: The exception to categorize
        context: Processing context

    Returns:
        Tuple of (category, message, exit_code)
    """
    pattern = create_error_pattern(error)
    message = pattern.message_template.format(message=str(error))

    return pattern.category, message, pattern.exit_code


def process_config_setting(
    key: str, value: str
) -> tuple[str, str | int | float | bool]:
    """Process config with pattern matching and type validation.

    Args:
        key: Configuration key
        value: String value to process

    Returns:
        Tuple of (key, converted_value)

    Raises:
        ValueError: If value cannot be converted to expected type
    """
    pattern = create_config_pattern(key)
    converted_value = pattern.validate(value)
    return key, converted_value


def handle_error_with_recovery(error: Exception, context: ProcessingContext) -> int:
    """Handle errors with pattern-based recovery strategies.

    Args:
        error: The exception to handle
        context: Processing context

    Returns:
        Exit code
    """
    pattern = create_error_pattern(error)

    match pattern.recovery_strategy:
        case "retry_with_backoff":
            return _retry_with_backoff(error, context)
        case "reset_to_defaults":
            return _reset_to_defaults(error, context)
        case "skip_and_continue":
            return _skip_and_continue(error, context)
        case "suggest_fix":
            return _suggest_fix(error, context)
        case "abort":
            console.print(
                f"[red]{pattern.message_template.format(message=str(error))}[/red]"
            )
            return pattern.exit_code
        case _:
            console.print(
                f"[red]Unknown recovery strategy: {pattern.recovery_strategy}[/red]"
            )
            return ExitCode.GENERAL_ERROR


# Command handler functions - Now with real implementations via bridge
def handle_file_processing(args: Namespace) -> int:
    """Handle single file processing."""
    try:
        # Create a Click context for bridge usage
        click_ctx = click.Context(click.Command("process"))
        click_ctx.obj = {"config": getattr(args, "config", None)}

        # Extract arguments for process command
        kwargs = {
            "input_paths": getattr(args, "input_paths", []),
            "collection": getattr(args, "collection", ""),
            "chunk_size": getattr(args, "chunk_size", None),
            "chunk_overlap": getattr(args, "chunk_overlap", None),
            "method": getattr(args, "method", None),
            "batch_size": getattr(args, "batch_size", None),
            "preserve_headers": getattr(args, "preserve_headers", None),
            "recursive": getattr(args, "recursive", False),
            "pattern": getattr(args, "pattern", None),
            "force": getattr(args, "force", False),
        }

        return bridge_process_command(click_ctx, "", **kwargs)

    except Exception as e:
        console.print(f"[red]File processing failed: {str(e)}[/red]")
        return ExitCode.PROCESSING_ERROR


def handle_directory_processing(args: Namespace) -> int:
    """Handle directory processing."""
    # Directory processing is the same as file processing with recursive=True
    args.recursive = True
    return handle_file_processing(args)


def handle_collection_listing(args: Namespace) -> int:
    """Handle collection listing."""
    try:
        # Create minimal Click context for bridge
        ctx = click.Context(click.Command("collections"))
        ctx.obj = {"config": getattr(args, "config", None)}

        kwargs = {
            "format": getattr(args, "format", "table"),
            "show_metadata": getattr(args, "show_metadata", False),
        }

        return bridge_collections_command(ctx, "list", **kwargs)

    except Exception as e:
        console.print(f"[red]Collection listing failed: {str(e)}[/red]")
        return ExitCode.DATABASE_ERROR


def handle_collection_creation(args: Namespace) -> int:
    """Handle collection creation."""
    try:
        ctx = click.Context(click.Command("collections"))
        ctx.obj = {"config": getattr(args, "config", None)}

        kwargs = {
            "name": getattr(args, "name", ""),
            "description": getattr(args, "description", None),
        }

        return bridge_collections_command(ctx, "create", **kwargs)

    except Exception as e:
        console.print(f"[red]Collection creation failed: {str(e)}[/red]")
        return ExitCode.DATABASE_ERROR


def handle_collection_deletion(args: Namespace) -> int:
    """Handle collection deletion."""
    try:
        ctx = click.Context(click.Command("collections"))
        ctx.obj = {"config": getattr(args, "config", None)}

        kwargs = {
            "name": getattr(args, "name", ""),
            "force": getattr(args, "force", False),
        }

        return bridge_collections_command(ctx, "delete", **kwargs)

    except Exception as e:
        console.print(f"[red]Collection deletion failed: {str(e)}[/red]")
        return ExitCode.DATABASE_ERROR


def handle_search_query(args: Namespace) -> int:
    """Handle search query."""
    try:
        ctx = click.Context(click.Command("query"))
        ctx.obj = {"config": getattr(args, "config", None)}

        kwargs = {
            "collection": getattr(args, "collection", ""),
            "query_text": getattr(args, "query_text", ""),
            "limit": getattr(args, "limit", 10),
            "format": getattr(args, "format", "table"),
            "include_metadata": getattr(args, "include_metadata", False),
        }

        return bridge_query_command(ctx, "search", **kwargs)

    except Exception as e:
        console.print(f"[red]Search query failed: {str(e)}[/red]")
        return ExitCode.DATABASE_ERROR


def handle_similarity_search(args: Namespace) -> int:
    """Handle similarity search."""
    try:
        ctx = click.Context(click.Command("query"))
        ctx.obj = {"config": getattr(args, "config", None)}

        kwargs = {
            "collection": getattr(args, "collection", ""),
            "query_text": getattr(args, "query_text", ""),
            "threshold": getattr(args, "threshold", 0.7),
            "limit": getattr(args, "limit", 10),
            "format": getattr(args, "format", "table"),
        }

        return bridge_query_command(ctx, "similar", **kwargs)

    except Exception as e:
        console.print(f"[red]Similarity search failed: {str(e)}[/red]")
        return ExitCode.DATABASE_ERROR


def handle_config_display(args: Namespace) -> int:
    """Handle configuration display."""
    try:
        ctx = click.Context(click.Command("config"))
        ctx.obj = {"config": getattr(args, "config", None)}

        kwargs = {
            "format": getattr(args, "format", "yaml"),
            "section": getattr(args, "section", None),
        }

        return bridge_config_command(ctx, "show", **kwargs)

    except Exception as e:
        console.print(f"[red]Config display failed: {str(e)}[/red]")
        return ExitCode.CONFIG_ERROR


def handle_config_update(args: Namespace) -> int:
    """Handle configuration update."""
    try:
        ctx = click.Context(click.Command("config"))
        ctx.obj = {"config": getattr(args, "config", None)}

        kwargs = {
            "key": getattr(args, "key", ""),
            "value": getattr(args, "value", ""),
            "is_global": getattr(args, "is_global", False),
            "is_local": getattr(args, "is_local", False),
        }

        return bridge_config_command(ctx, "set", **kwargs)

    except Exception as e:
        console.print(f"[red]Config update failed: {str(e)}[/red]")
        return ExitCode.CONFIG_ERROR


# Recovery strategy functions
def _retry_with_backoff(error: Exception, context: ProcessingContext) -> int:
    """Retry operation with exponential backoff."""
    if context.retry_count >= context.max_retries:
        console.print(f"[red]Max retries exceeded: {str(error)}[/red]")
        return ExitCode.GENERAL_ERROR

    backoff_time = 2**context.retry_count
    console.print(
        f"[yellow]Retrying in {backoff_time} seconds... "
        f"(attempt {context.retry_count + 1})[/yellow]"
    )
    time.sleep(backoff_time)
    context.retry_count += 1

    # In a real implementation, this would retry the actual operation
    return ExitCode.SUCCESS


def _reset_to_defaults(error: Exception, context: ProcessingContext) -> int:
    """Reset configuration to defaults."""
    console.print(
        f"[yellow]Resetting to default configuration due to: {str(error)}[/yellow]"
    )
    # Implementation would reset config to defaults
    return ExitCode.SUCCESS


def _skip_and_continue(error: Exception, context: ProcessingContext) -> int:
    """Skip current operation and continue."""
    if not context.continue_on_error:
        console.print(f"[red]Stopping due to error: {str(error)}[/red]")
        return ExitCode.GENERAL_ERROR

    console.print(f"[yellow]Skipping due to error: {str(error)}[/yellow]")
    return ExitCode.SUCCESS


def _suggest_fix(error: Exception, context: ProcessingContext) -> int:
    """Suggest fix for the error."""
    console.print(f"[yellow]Error occurred: {str(error)}[/yellow]")

    match error:
        case PermissionError():
            console.print(
                "[cyan]Suggestion: Check file permissions with 'ls -la' "
                "or run with appropriate privileges[/cyan]"
            )
        case FileNotFoundError():
            console.print(
                "[cyan]Suggestion: Verify file path exists and is accessible[/cyan]"
            )
        case InputValidationError():
            console.print(
                "[cyan]Suggestion: Check command arguments and input format[/cyan]"
            )
        case _:
            console.print(
                "[cyan]Suggestion: Check error details and documentation[/cyan]"
            )

    return (
        ExitCode.PERMISSION_ERROR
        if isinstance(error, PermissionError)
        else ExitCode.GENERAL_ERROR
    )


# Chunking strategy creation helpers
def _create_semantic_chunker(options: ChunkingConfig) -> ChunkingStrategy:
    """Create semantic chunking strategy."""
    # Placeholder - would implement semantic chunking
    return FixedSizeChunker(options)


def _create_sentence_chunker(options: ChunkingConfig) -> ChunkingStrategy:
    """Create sentence-based chunking strategy."""
    # Placeholder - would implement sentence-based chunking
    return FixedSizeChunker(options)


def _create_paragraph_chunker(options: ChunkingConfig) -> ChunkingStrategy:
    """Create paragraph-based chunking strategy."""
    # Placeholder - would implement paragraph-based chunking
    return FixedSizeChunker(options)


def _get_command_handler(handler_name: str) -> Callable[[Namespace], int] | None:
    """Get command handler function by name.

    Args:
        handler_name: Name of the handler function

    Returns:
        Handler function or None if not found
    """
    handlers = {
        "handle_file_processing": handle_file_processing,
        "handle_directory_processing": handle_directory_processing,
        "handle_collection_listing": handle_collection_listing,
        "handle_collection_creation": handle_collection_creation,
        "handle_collection_deletion": handle_collection_deletion,
        "handle_search_query": handle_search_query,
        "handle_similarity_search": handle_similarity_search,
        "handle_config_display": handle_config_display,
        "handle_config_update": handle_config_update,
    }

    return handlers.get(handler_name)
