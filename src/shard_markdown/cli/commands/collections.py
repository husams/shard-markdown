"""Collections command for collection management."""

import builtins
import json
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from ...chromadb.collections import CollectionManager
from ...chromadb.factory import create_chromadb_client
from ...utils.errors import ShardMarkdownError
from ...utils.logging import get_logger


_logger = get_logger(__name__)
console = Console()


def _handle_chromadb_errors(e: Exception, verbose: int) -> None:
    """Handle ChromaDB errors with consistent formatting."""
    if isinstance(e, ShardMarkdownError):
        console.print(f"[red]Error:[/red] {e.message}")
        if verbose > 0:
            console.print(f"[dim]Error code: {e.error_code}[/dim]")
    elif isinstance(e, ConnectionError | RuntimeError | ValueError):
        console.print("[red]Unexpected error:[/red] %s", str(e))
        if verbose > 1:
            console.print_exception()
    raise click.Abort() from e


def _get_connected_chromadb_client(config: Any) -> Any:
    """Get connected ChromaDB client or raise exception."""
    chroma_client = create_chromadb_client(config.chromadb)
    if not chroma_client.connect():
        raise click.ClickException("Failed to connect to ChromaDB")
    return chroma_client


@click.group()
def collections() -> None:
    """Manage ChromaDB collections.

    This command group provides functionality to create, list, delete,
    and manage ChromaDB collections for storing document chunks.

    Examples:
      # List all collections
      shard-md collections list

      # Create a new collection
      shard-md collections create my-collection --description "My documents"

      # Get collection information
      shard-md collections info my-collection

      # Delete a collection
      shard-md collections delete my-collection
    """
    pass


@collections.command()
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format [default: table]",
)
@click.option(
    "--show-metadata",
    is_flag=True,
    help="Include collection metadata in output",
)
@click.option("--filter", help="Filter collections by name pattern")
@click.pass_context
def list(ctx: click.Context, format: str, show_metadata: bool, filter: str) -> None:  # noqa: C901
    """List all ChromaDB collections."""
    config = ctx.obj["config"]
    verbose = ctx.obj.get("verbose", 0)

    try:
        # Initialize ChromaDB client
        chroma_client = _get_connected_chromadb_client(config)

        # Get collections
        collection_manager = CollectionManager(chroma_client)
        collections_info = collection_manager.list_collections()

        # Apply filter if specified
        if filter:
            collections_info = [
                col for col in collections_info if filter.lower() in col["name"].lower()
            ]

        # Display results
        if format == "table":
            _display_collections_table(collections_info, show_metadata)
        elif format == "json":
            console.print(json.dumps(collections_info, indent=2))
        elif format == "yaml":
            import yaml

            console.print(yaml.dump(collections_info, default_flow_style=False))

        if not collections_info:
            console.print("[yellow]No collections found[/yellow]")
        else:
            console.print(f"[green]Found {len(collections_info)} collection(s)[/green]")

    except (ShardMarkdownError, ConnectionError, RuntimeError, ValueError) as e:
        _handle_chromadb_errors(e, verbose)


@collections.command()
@click.argument("name")
@click.option("--description", help="Collection description")
@click.option("--metadata", help="Additional metadata as JSON string")
@click.option("--force", is_flag=True, help="Force creation even if collection exists")
@click.pass_context
def create(
    ctx: click.Context, name: str, description: str, metadata: str, force: bool
) -> None:  # noqa: C901
    """Create a new ChromaDB collection."""
    config = ctx.obj["config"]
    verbose = ctx.obj.get("verbose", 0)

    try:
        # Parse metadata if provided
        collection_metadata: dict[str, Any] = {}
        if metadata:
            try:
                collection_metadata = json.loads(metadata)
            except json.JSONDecodeError as e:
                raise click.BadParameter(f"Invalid JSON metadata: {e}") from e

        # Initialize ChromaDB client
        chroma_client = _get_connected_chromadb_client(config)

        # Create collection
        collection_manager = CollectionManager(chroma_client)

        # Check if collection exists
        if collection_manager.collection_exists(name) and not force:
            raise click.ClickException(
                f"Collection '{name}' already exists. Use --force to recreate."
            )

        if force and collection_manager.collection_exists(name):
            confirm_msg = f"Delete existing collection '{name}' and recreate?"
            if click.confirm(confirm_msg):
                collection_manager.delete_collection(name)
            else:
                raise click.Abort()

        collection_manager.create_collection(
            name, description=description, metadata=collection_metadata
        )

        console.print(f"[green]✓ Created collection '{name}'[/green]")

        if description:
            console.print(f"Description: {description}")
        if collection_metadata:
            metadata_json = json.dumps(collection_metadata, indent=2)
            console.print(f"Metadata: {metadata_json}")

    except (ShardMarkdownError, ConnectionError, RuntimeError, ValueError) as e:
        _handle_chromadb_errors(e, verbose)


@collections.command()
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Force deletion without confirmation")
@click.option("--backup", is_flag=True, help="Create backup before deletion")
@click.pass_context
def delete(ctx: click.Context, name: str, force: bool, backup: bool) -> None:  # noqa: C901
    """Delete a ChromaDB collection."""
    config = ctx.obj["config"]
    verbose = ctx.obj.get("verbose", 0)

    try:
        # Initialize ChromaDB client
        chroma_client = _get_connected_chromadb_client(config)

        collection_manager = CollectionManager(chroma_client)

        # Check if collection exists
        if not collection_manager.collection_exists(name):
            raise click.ClickException(f"Collection '{name}' does not exist")

        # Get collection info for backup
        if backup:
            console.print("[yellow]Backup functionality not yet implemented[/yellow]")

        # Confirm deletion
        if not force:
            confirm_msg = f"Delete collection '{name}' and all its documents?"
            if not click.confirm(confirm_msg):
                raise click.Abort()

        # Delete collection
        collection_manager.delete_collection(name)
        console.print(f"[green]✓ Deleted collection '{name}'[/green]")

    except (ShardMarkdownError, ConnectionError, RuntimeError, ValueError) as e:
        _handle_chromadb_errors(e, verbose)


@collections.command()
@click.argument("name")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format [default: table]",
)
@click.option(
    "--show-documents",
    is_flag=True,
    help="Include document count and sample documents",
)
@click.pass_context
def info(ctx: click.Context, name: str, format: str, show_documents: bool) -> None:  # noqa: C901
    """Show detailed information about a collection."""
    config = ctx.obj["config"]
    verbose = ctx.obj.get("verbose", 0)

    try:
        # Initialize ChromaDB client
        chroma_client = _get_connected_chromadb_client(config)

        collection_manager = CollectionManager(chroma_client)

        # Check if collection exists
        if not collection_manager.collection_exists(name):
            raise click.ClickException(f"Collection '{name}' does not exist")

        # Get collection info
        info_data = collection_manager.get_collection_info(name)

        # Display results
        if format == "table":
            _display_collection_info_table(info_data, show_documents)
        elif format == "json":
            console.print(json.dumps(info_data, indent=2))
        elif format == "yaml":
            import yaml

            console.print(yaml.dump(info_data, default_flow_style=False))

    except (ShardMarkdownError, ConnectionError, RuntimeError, ValueError) as e:
        _handle_chromadb_errors(e, verbose)


def _display_collections_table(
    collections_info: builtins.list[dict[str, Any]], show_metadata: bool
) -> None:
    """Display collections in table format."""
    table = Table(title="ChromaDB Collections")
    table.add_column("Name", style="cyan")
    table.add_column("Count", style="white")

    if show_metadata:
        table.add_column("Metadata", style="dim")

    for collection in collections_info:
        row = [collection["name"], str(collection.get("count", 0))]

        if show_metadata:
            metadata = collection.get("metadata", {})
            if metadata:
                metadata_str = json.dumps(metadata, indent=None)
                if len(metadata_str) > 50:
                    metadata_str = metadata_str[:47] + "..."
                row.append(metadata_str)
            else:
                row.append("")

        table.add_row(*row)

    console.print(table)


def _display_collection_info_table(
    info_data: dict[str, Any], show_documents: bool
) -> None:
    """Display collection info in table format."""
    table = Table(title=f"Collection: {info_data['name']}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Name", info_data["name"])
    table.add_row("Document Count", str(info_data.get("count", 0)))

    metadata = info_data.get("metadata", {})
    if metadata:
        for key, value in metadata.items():
            table.add_row(f"Metadata.{key}", str(value))

    console.print(table)

    if show_documents and info_data.get("count", 0) > 0:
        count = info_data["count"]
        console.print(f"[blue]Collection contains {count} documents[/blue]")
        # Could add sample document display here
