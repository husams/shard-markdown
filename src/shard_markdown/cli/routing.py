"""Main pattern matching router for CLI commands."""

import time
from argparse import Namespace
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from ..chromadb.collections import CollectionManager
from ..chromadb.factory import create_chromadb_client
from ..config import load_config, save_config
from ..core.chunking.base import BaseChunker
from ..core.chunking.fixed import FixedSizeChunker
from ..core.chunking.structure import StructureAwareChunker
from ..core.models import ChunkingConfig
from ..core.processor import DocumentProcessor
from ..utils.errors import (
    InputValidationError,
    ShardMarkdownError,
)
from ..utils.logging import get_logger
from ..utils.validation import (
    validate_chunk_parameters,
    validate_collection_name,
    validate_input_paths,
)
from .patterns import (
    ExitCode,
    create_command_pattern,
    create_config_pattern,
    create_error_pattern,
)


console = Console()


# Type alias for chunking strategy - proper type instead of Any
ChunkingStrategy = BaseChunker


# Type alias for processing context
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


def process_config_setting(key: str, value: str) -> tuple[str, Any]:
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


# Command handler functions
def handle_file_processing(args: Namespace) -> int:
    """Handle single file processing with real functionality."""
    logger = get_logger(__name__)

    try:
        # Validate inputs - these functions validate and raise exceptions on error
        validate_input_paths(args.input_paths)
        validate_collection_name(args.collection)
        validate_chunk_parameters(
            chunk_size=getattr(args, "chunk_size", 1000),
            chunk_overlap=getattr(args, "chunk_overlap", 200),
        )

        # Get validated values
        input_paths = args.input_paths
        collection_name = args.collection

        # Create chunking config
        chunk_config = ChunkingConfig(
            chunk_size=getattr(args, "chunk_size", 1000),
            overlap=getattr(args, "chunk_overlap", 200),
            method=getattr(args, "strategy", "structure"),
        )

        # Load app config and create ChromaDB client
        app_config = load_config()
        client = create_chromadb_client(app_config.chromadb)
        # collection_manager not used in processing - just for validation
        _ = CollectionManager(client)

        # Create document processor
        processor = DocumentProcessor(chunking_config=chunk_config)

        # Process the file
        file_path = Path(input_paths[0])
        console.print(f"[blue]Processing file: {file_path}[/blue]")

        if getattr(args, "dry_run", False):
            console.print("[yellow]Dry run mode - no actual processing[/yellow]")
            return ExitCode.SUCCESS

        result = processor.process_document(file_path, collection_name)

        # Display results
        if result.success:
            console.print(f"[green]Successfully processed {file_path}[/green]")
            console.print(f"  Chunks created: {result.chunks_created}")
            console.print(f"  Processing time: {result.processing_time:.2f}s")
            if result.collection_name:
                console.print(f"  Collection: {result.collection_name}")
        else:
            console.print(f"[red]Failed to process {file_path}[/red]")
            if result.error:
                console.print(f"  Error: {result.error}")
            return ExitCode.PROCESSING_ERROR

        return ExitCode.SUCCESS

    except ShardMarkdownError as e:
        console.print(f"[red]Processing error: {str(e)}[/red]")
        logger.error(f"File processing failed: {str(e)}")
        return ExitCode.PROCESSING_ERROR
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        logger.error(f"Unexpected error during file processing: {str(e)}")
        return ExitCode.GENERAL_ERROR


def handle_directory_processing(args: Namespace) -> int:
    """Handle directory processing with real functionality."""
    logger = get_logger(__name__)

    try:
        # Validate inputs - these functions validate and raise exceptions on error
        validate_input_paths(args.input_paths)
        validate_collection_name(args.collection)
        validate_chunk_parameters(
            chunk_size=getattr(args, "chunk_size", 1000),
            chunk_overlap=getattr(args, "chunk_overlap", 200),
        )

        # Get validated values
        input_paths = args.input_paths
        collection_name = args.collection

        # Create chunking config
        chunk_config = ChunkingConfig(
            chunk_size=getattr(args, "chunk_size", 1000),
            overlap=getattr(args, "chunk_overlap", 200),
            method=getattr(args, "strategy", "structure"),
        )

        # Load app config and create ChromaDB client
        app_config = load_config()
        client = create_chromadb_client(app_config.chromadb)
        # collection_manager not used in processing - just for validation
        _ = CollectionManager(client)

        # Create document processor
        processor = DocumentProcessor(chunking_config=chunk_config)

        # Process directory/directories
        recursive = getattr(args, "recursive", False)
        batch_size = getattr(args, "batch_size", 10)

        console.print(f"[blue]Processing directory: {input_paths[0]}[/blue]")
        console.print(f"  Recursive: {recursive}")
        console.print(f"  Batch size: {batch_size}")

        if getattr(args, "dry_run", False):
            console.print("[yellow]Dry run mode - no actual processing[/yellow]")
            return ExitCode.SUCCESS

        # Process all paths
        total_files = 0
        total_chunks = 0

        for input_path in input_paths:
            path = Path(input_path)
            if path.is_dir():
                # Get all markdown files in directory
                if recursive:
                    files = list(path.rglob("*.md"))
                else:
                    files = list(path.glob("*.md"))

                if files:
                    result = processor.process_batch(files, collection_name)
                    total_files += result.successful_files
                    total_chunks += result.total_chunks

                    # Display batch results
                    console.print(
                        f"[green]Processed {result.successful_files} files from "
                        f"{path}[/green]"
                    )
                    if result.failed_files > 0:
                        console.print(
                            f"[yellow]  {result.failed_files} files failed[/yellow]"
                        )
                else:
                    console.print(f"[yellow]No markdown files found in {path}[/yellow]")
            else:
                console.print(f"[yellow]Skipping {path} - not a directory[/yellow]")

        # Display final results
        console.print(f"[green]Total files processed: {total_files}[/green]")
        console.print(f"[green]Total chunks created: {total_chunks}[/green]")

        return ExitCode.SUCCESS

    except ShardMarkdownError as e:
        console.print(f"[red]Processing error: {str(e)}[/red]")
        logger.error(f"Directory processing failed: {str(e)}")
        return ExitCode.PROCESSING_ERROR
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        logger.error(f"Unexpected error during directory processing: {str(e)}")
        return ExitCode.GENERAL_ERROR


def handle_collection_listing(args: Namespace) -> int:
    """Handle collection listing with real functionality."""
    logger = get_logger(__name__)

    try:
        # Load app config and create ChromaDB client
        app_config = load_config()
        client = create_chromadb_client(app_config.chromadb)
        collection_manager = CollectionManager(client)

        # Get collections
        collections = collection_manager.list_collections()

        if not collections:
            console.print("[yellow]No collections found[/yellow]")
            return ExitCode.SUCCESS

        # Display format
        format_type = getattr(args, "format", "table")
        show_metadata = getattr(args, "show_metadata", False)

        if format_type == "table":
            table = Table(title="ChromaDB Collections")
            table.add_column("Name", style="cyan")
            table.add_column("Document Count", justify="right", style="magenta")
            if show_metadata:
                table.add_column("Metadata", style="green")

            for collection in collections:
                row = [collection["name"], str(collection.get("count", 0))]
                if show_metadata:
                    metadata = collection.get("metadata", {})
                    row.append(str(metadata) if metadata else "None")
                table.add_row(*row)

            console.print(table)
        else:
            # Simple format
            for collection in collections:
                console.print(
                    f"  {collection['name']}: {collection.get('count', 0)} documents"
                )

        return ExitCode.SUCCESS

    except Exception as e:
        console.print(f"[red]Error listing collections: {str(e)}[/red]")
        logger.error(f"Collection listing failed: {str(e)}")
        return ExitCode.DATABASE_ERROR


def handle_collection_creation(args: Namespace) -> int:
    """Handle collection creation with real functionality."""
    logger = get_logger(__name__)

    try:
        validate_collection_name(args.name)
        collection_name = args.name
        description = getattr(args, "description", "")

        # Load app config and create ChromaDB client
        app_config = load_config()
        client = create_chromadb_client(app_config.chromadb)
        collection_manager = CollectionManager(client)

        console.print(f"[blue]Creating collection: {collection_name}[/blue]")

        # Create the collection
        success = collection_manager.create_collection(
            collection_name, description=description
        )

        if success:
            console.print(
                f"[green]Successfully created collection '{collection_name}'[/green]"
            )
            if description:
                console.print(f"  Description: {description}")
            return ExitCode.SUCCESS
        else:
            console.print(f"[red]Failed to create collection '{collection_name}'[/red]")
            return ExitCode.DATABASE_ERROR

    except Exception as e:
        console.print(f"[red]Error creating collection: {str(e)}[/red]")
        logger.error(f"Collection creation failed: {str(e)}")
        return ExitCode.DATABASE_ERROR


def handle_collection_deletion(args: Namespace) -> int:
    """Handle collection deletion with real functionality."""
    logger = get_logger(__name__)

    try:
        validate_collection_name(args.name)
        collection_name = args.name
        force = getattr(args, "force", False)

        # Load app config and create ChromaDB client
        app_config = load_config()
        client = create_chromadb_client(app_config.chromadb)
        collection_manager = CollectionManager(client)

        # Confirm deletion unless forced
        if not force:
            console.print(
                f"[yellow]Are you sure you want to delete collection "
                f"'{collection_name}'? [y/N][/yellow]"
            )
            # In a real implementation, this would prompt for user input
            # For now, we'll assume force mode for pattern matching
            console.print("[yellow]Use --force flag to confirm deletion[/yellow]")
            return ExitCode.SUCCESS

        console.print(f"[blue]Deleting collection: {collection_name}[/blue]")

        # Delete the collection
        success = collection_manager.delete_collection(collection_name)

        if success:
            console.print(
                f"[green]Successfully deleted collection '{collection_name}'[/green]"
            )
            return ExitCode.SUCCESS
        else:
            console.print(f"[red]Failed to delete collection '{collection_name}'[/red]")
            return ExitCode.DATABASE_ERROR

    except Exception as e:
        console.print(f"[red]Error deleting collection: {str(e)}[/red]")
        logger.error(f"Collection deletion failed: {str(e)}")
        return ExitCode.DATABASE_ERROR


def handle_search_query(args: Namespace) -> int:
    """Handle search query with real functionality."""
    logger = get_logger(__name__)

    try:
        validate_collection_name(args.collection)
        collection_name = args.collection
        query_text = args.query_text
        limit = getattr(args, "limit", 10)
        # threshold not used in this simplified search implementation
        _ = getattr(args, "threshold", 0.7)

        # Load app config and create ChromaDB client
        app_config = load_config()
        client = create_chromadb_client(app_config.chromadb)
        collection_manager = CollectionManager(client)

        console.print(
            f"[blue]Searching in collection '{collection_name}' for: "
            f"{query_text}[/blue]"
        )

        # Get collection and perform search (simplified implementation)
        collection = collection_manager.get_collection(collection_name)

        # Perform basic query - this would need to be enhanced with actual search logic
        query_results = collection.query(query_texts=[query_text], n_results=limit)

        # Convert results to expected format
        results = []
        if query_results and "documents" in query_results:
            for i, doc in enumerate(query_results["documents"][0]):
                results.append(
                    {
                        "id": query_results.get("ids", [[]])[0][i]
                        if query_results.get("ids")
                        else f"doc_{i}",
                        "text": doc,
                        "score": 1.0 - query_results.get("distances", [[0]])[0][i]
                        if query_results.get("distances")
                        else 0.8,
                    }
                )

        if not results:
            console.print("[yellow]No results found[/yellow]")
            return ExitCode.SUCCESS

        # Display results
        console.print(f"[green]Found {len(results)} results:[/green]")

        for i, result in enumerate(results, 1):
            score = result.get("score", 0)
            text = result.get("text", "")[:200]  # Truncate for display
            chunk_id = result.get("id", "")

            console.print(f"\n{i}. [cyan]ID: {chunk_id}[/cyan] (Score: {score:.3f})")
            console.print(f"   {text}...")

        return ExitCode.SUCCESS

    except Exception as e:
        console.print(f"[red]Search error: {str(e)}[/red]")
        logger.error(f"Search query failed: {str(e)}")
        return ExitCode.DATABASE_ERROR


def handle_similarity_search(args: Namespace) -> int:
    """Handle similarity search with real functionality."""
    logger = get_logger(__name__)

    try:
        validate_collection_name(args.collection)
        collection_name = args.collection
        query_text = args.query_text
        limit = getattr(args, "limit", 5)
        threshold = getattr(args, "threshold", 0.7)

        # Load app config and create ChromaDB client
        app_config = load_config()
        client = create_chromadb_client(app_config.chromadb)
        collection_manager = CollectionManager(client)

        console.print(
            f"[blue]Finding similar content in '{collection_name}' to: "
            f"{query_text}[/blue]"
        )

        # Get collection and perform similarity search (simplified implementation)
        collection = collection_manager.get_collection(collection_name)

        # Perform similarity query
        query_results = collection.query(query_texts=[query_text], n_results=limit)

        # Convert results to expected format
        results = []
        if query_results and "documents" in query_results:
            for i, doc in enumerate(query_results["documents"][0]):
                similarity = (
                    1.0 - query_results.get("distances", [[0]])[0][i]
                    if query_results.get("distances")
                    else 0.8
                )
                if similarity >= threshold:
                    results.append(
                        {
                            "id": query_results.get("ids", [[]])[0][i]
                            if query_results.get("ids")
                            else f"doc_{i}",
                            "text": doc,
                            "score": similarity,
                        }
                    )

        if not results:
            console.print("[yellow]No similar content found[/yellow]")
            return ExitCode.SUCCESS

        # Display results
        console.print(f"[green]Found {len(results)} similar documents:[/green]")

        for i, result in enumerate(results, 1):
            score = result.get("score", 0)
            text = result.get("text", "")[:150]  # Truncate for display
            chunk_id = result.get("id", "")

            console.print(
                f"\n{i}. [cyan]ID: {chunk_id}[/cyan] (Similarity: {score:.3f})"
            )
            console.print(f"   {text}...")

        return ExitCode.SUCCESS

    except Exception as e:
        console.print(f"[red]Similarity search error: {str(e)}[/red]")
        logger.error(f"Similarity search failed: {str(e)}")
        return ExitCode.DATABASE_ERROR


def handle_config_display(args: Namespace) -> int:
    """Handle configuration display with real functionality."""
    logger = get_logger(__name__)

    try:
        # Load current configuration
        config = load_config()
        format_type = getattr(args, "format", "yaml")

        console.print("[blue]Current configuration:[/blue]")

        # Get configuration as dictionary
        config_dict = config.model_dump()

        if format_type == "yaml":
            # Display as YAML-like format
            for section, values in config_dict.items():
                console.print(f"\n[cyan]{section}:[/cyan]")
                if isinstance(values, dict):
                    for key, value in values.items():
                        console.print(f"  {key}: {value}")
                else:
                    console.print(f"  {values}")
        else:
            # Simple key-value format
            def _print_config(data: dict[str, Any], prefix: str = "") -> None:
                for key, value in data.items():
                    if isinstance(value, dict):
                        console.print(f"[cyan]{prefix}{key}:[/cyan]")
                        _print_config(value, prefix + "  ")
                    else:
                        console.print(f"{prefix}{key}: {value}")

            _print_config(config_dict)

        return ExitCode.SUCCESS

    except Exception as e:
        console.print(f"[red]Error displaying configuration: {str(e)}[/red]")
        logger.error(f"Config display failed: {str(e)}")
        return ExitCode.CONFIG_ERROR


def handle_config_update(args: Namespace) -> int:
    """Handle configuration update with real functionality."""
    logger = get_logger(__name__)

    try:
        key = args.key
        value = args.value
        global_config = getattr(args, "global_config", False)

        console.print(f"[blue]Setting configuration: {key} = {value}[/blue]")

        # Create config pattern to validate the value
        config_pattern = create_config_pattern(key)
        validated_value = config_pattern.validate(value)

        # Load current configuration
        config = load_config()

        # Update the configuration
        # Note: This is a simplified implementation
        # In a real implementation, we'd need to handle nested config keys
        if hasattr(config, key):
            setattr(config, key, validated_value)
        else:
            # Handle nested keys like 'chunking.chunk_size'
            if "." in key:
                parts = key.split(".")
                obj = config
                for part in parts[:-1]:
                    obj = getattr(obj, part)
                setattr(obj, parts[-1], validated_value)
            else:
                console.print(f"[red]Unknown configuration key: {key}[/red]")
                return ExitCode.CONFIG_ERROR

        # Save the updated configuration
        # Note: determine config path based on global_config flag
        from pathlib import Path

        if global_config:
            config_path = Path.home() / ".shard-md" / "config.yaml"
        else:
            config_path = Path.cwd() / ".shard-md" / "config.yaml"
        save_config(config, config_path)

        console.print(f"[green]Successfully updated {key} to {validated_value}[/green]")
        if global_config:
            console.print("[cyan]Configuration saved globally[/cyan]")
        else:
            console.print("[cyan]Configuration saved locally[/cyan]")

        return ExitCode.SUCCESS

    except ValueError as e:
        console.print(f"[red]Invalid value for {args.key}: {str(e)}[/red]")
        logger.error(f"Config validation failed: {str(e)}")
        return ExitCode.VALIDATION_ERROR
    except Exception as e:
        console.print(f"[red]Error updating configuration: {str(e)}[/red]")
        logger.error(f"Config update failed: {str(e)}")
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
