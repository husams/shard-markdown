"""Data command for unified ChromaDB operations."""

import json
from typing import Any

import click
from rich.table import Table

from ...chromadb.collections import CollectionManager
from ...utils.errors import ShardMarkdownError
from ...utils.logging import get_logger
from ..utils import console, get_connected_chromadb_client, handle_chromadb_errors


_logger = get_logger(__name__)


@click.group()
def data() -> None:
    """Manage and query ChromaDB data."""
    pass


# Collection Management Commands


@data.command()
@click.option(
    "-f", "--format", type=click.Choice(["table", "json", "yaml"]), default="table"
)
@click.option("--show-metadata", is_flag=True, help="Include metadata")
@click.option("--filter", help="Filter by name pattern")
@click.pass_context
def list(ctx: click.Context, format: str, show_metadata: bool, filter: str) -> None:
    """List all ChromaDB collections."""
    config = ctx.obj["config"]
    verbose = ctx.obj.get("verbose", 0)
    try:
        chroma_client = get_connected_chromadb_client(config)
        collection_manager = CollectionManager(chroma_client)
        collections_info = collection_manager.list_collections()
        if filter:
            collections_info = [
                c for c in collections_info if filter.lower() in c["name"].lower()
            ]
        _display_output(format, collections_info, "Collections", show_metadata)
        msg = (
            "No collections found"
            if not collections_info
            else f"Found {len(collections_info)} collection(s)"
        )
        console.print(f"[{'yellow' if not collections_info else 'green'}]{msg}[/]")
    except (ShardMarkdownError, ConnectionError, RuntimeError, ValueError) as e:
        handle_chromadb_errors(e, verbose)


@data.command()
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
        chroma_client = get_connected_chromadb_client(config)

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
        handle_chromadb_errors(e, verbose)


@data.command()
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
        chroma_client = get_connected_chromadb_client(config)

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
        handle_chromadb_errors(e, verbose)


@data.command()
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
        chroma_client = get_connected_chromadb_client(config)

        collection_manager = CollectionManager(chroma_client)

        # Check if collection exists
        if not collection_manager.collection_exists(name):
            raise click.ClickException(f"Collection '{name}' does not exist")

        # Get collection info
        info_data = collection_manager.get_collection_info(name)

        # Display results
        if format == "table":
            _display_output(
                "table", info_data, f"Collection: {info_data['name']}", show_documents
            )
        elif format == "json":
            console.print(json.dumps(info_data, indent=2))
        elif format == "yaml":
            import yaml

            console.print(yaml.dump(info_data, default_flow_style=False))

    except (ShardMarkdownError, ConnectionError, RuntimeError, ValueError) as e:
        handle_chromadb_errors(e, verbose)


# Query Commands


@data.command()
@click.argument("query_text")
@click.option("--collection", "-c", required=True, help="Collection to search")
@click.option(
    "--limit",
    "-n",
    default=10,
    type=int,
    help="Maximum results to return [default: 10]",
)
@click.option(
    "--similarity-threshold",
    default=0.0,
    type=float,
    help="Minimum similarity score [default: 0.0]",
)
@click.option(
    "--include-metadata",
    is_flag=True,
    default=True,
    help="Include metadata in results [default: true]",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format [default: table]",
)
@click.pass_context
def search(  # noqa: C901
    ctx: click.Context,
    query_text: str,
    collection: str,
    limit: int,
    similarity_threshold: float,
    include_metadata: bool,
    format: str,
) -> None:
    """Search for documents using similarity search."""
    config = ctx.obj["config"]
    verbose = ctx.obj.get("verbose", 0)

    try:
        # Initialize ChromaDB client
        chroma_client = get_connected_chromadb_client(config)

        # Get collection
        try:
            collection_obj = chroma_client.get_collection(collection)
        except (ValueError, RuntimeError):
            raise click.ClickException(f"Collection '{collection}' not found") from None

        # Perform search
        console.print(
            f"[blue]Searching for: '{query_text}' in collection '{collection}'[/blue]"
        )

        try:
            results = collection_obj.query(query_texts=[query_text], n_results=limit)
        except (ValueError, RuntimeError) as e:
            raise click.ClickException(f"Search failed: {str(e)}") from e

        # Process results
        if not results["ids"][0]:
            console.print("[yellow]No documents found[/yellow]")
            return

        # Display results
        if format == "table":
            _display_search_results(results, include_metadata, similarity_threshold)
        elif format == "json":
            formatted_results = _format_results(results, include_metadata)
            console.print(json.dumps(formatted_results, indent=2))
        elif format == "yaml":
            import yaml

            formatted_results = _format_results(results, include_metadata)
            console.print(yaml.dump(formatted_results, default_flow_style=False))

        count = len(results["ids"][0])
        console.print(f"[green]Found {count} document(s)[/green]")

    except (ShardMarkdownError, ConnectionError, RuntimeError, ValueError) as e:
        handle_chromadb_errors(e, verbose)


@data.command()
@click.argument("document_id", required=False)
@click.option("--collection", "-c", required=True, help="Collection name")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format [default: table]",
)
@click.option(
    "--include-metadata",
    is_flag=True,
    default=True,
    help="Include metadata in results [default: true]",
)
@click.pass_context
def similar(
    ctx: click.Context,
    document_id: str,
    collection: str,
    format: str,
    include_metadata: bool,
) -> None:  # noqa: C901
    """Find similar documents or get a specific document by ID."""
    config = ctx.obj["config"]
    verbose = ctx.obj.get("verbose", 0)

    if not document_id:
        console.print("[yellow]Document ID required for similarity search[/yellow]")
        return

    try:
        # Initialize ChromaDB client
        chroma_client = get_connected_chromadb_client(config)

        # Get collection
        try:
            collection_obj = chroma_client.get_collection(collection)
        except (ValueError, RuntimeError):
            raise click.ClickException(f"Collection '{collection}' not found") from None

        # Get document
        console.print(
            f"[blue]Finding documents similar to '{document_id}' in collection "
            f"'{collection}'[/blue]"
        )

        try:
            results = collection_obj.get(
                ids=[document_id],
                include=(
                    ["documents", "metadatas"] if include_metadata else ["documents"]
                ),
            )
        except (ValueError, RuntimeError) as e:
            raise click.ClickException(f"Failed to retrieve document: {str(e)}") from e

        # Check if document exists
        if not results["ids"]:
            console.print(f"[yellow]Document '{document_id}' not found[/yellow]")
            return

        # Display result
        if format == "table":
            doc_data = {
                "id": results["ids"][0],
                "content": results["documents"][0][:200] + "...",
                "length": len(results["documents"][0]),
            }
            if include_metadata and results.get("metadatas"):
                doc_data["metadata"] = results["metadatas"][0]
            _display_output(
                "table", doc_data, f"Document: {results['ids'][0]}", include_metadata
            )
        elif format == "json":
            formatted_result = _format_results(results, include_metadata)
            console.print(json.dumps(formatted_result, indent=2))
        elif format == "yaml":
            import yaml

            formatted_result = _format_results(results, include_metadata)
            console.print(yaml.dump(formatted_result, default_flow_style=False))

        console.print("[green]✓ Document retrieved successfully[/green]")

    except (ShardMarkdownError, ConnectionError, RuntimeError, ValueError) as e:
        handle_chromadb_errors(e, verbose)


# Display Helper Functions


def _display_output(
    fmt: str, data: Any, title: str = "", show_meta: bool = False
) -> None:
    import builtins

    if fmt == "json":
        console.print(json.dumps(data, indent=2))
    elif fmt == "yaml":
        import yaml

        console.print(yaml.dump(data, default_flow_style=False))
    elif isinstance(data, builtins.list) and data:
        table = Table(title=title)
        if "name" in data[0]:
            table.add_column("Name", style="cyan")
            table.add_column("Count")
            if show_meta:
                table.add_column("Metadata", style="dim")
            for item in data:
                row = [item.get("name", ""), str(item.get("count", 0))]
                if show_meta and item.get("metadata"):
                    row.append(str(item["metadata"])[:50])
                elif show_meta:
                    row.append("")
                table.add_row(*row)
        console.print(table)
    elif isinstance(data, builtins.dict):
        table = Table(title=title)
        table.add_column("Property", style="cyan")
        table.add_column("Value")
        for k, v in data.items():
            if k != "metadata" or show_meta:
                table.add_row(k.replace("_", " ").title(), str(v))
        console.print(table)


def _display_search_results(
    results: dict[str, Any], include_metadata: bool, similarity_threshold: float
) -> None:
    table = Table(title="Search Results")
    table.add_column("Rank", width=6)
    table.add_column("ID")
    table.add_column("Content")
    table.add_column("Score")
    if include_metadata:
        table.add_column("Metadata", style="dim")
    for i, (doc_id, doc, dist) in enumerate(
        zip(
            results["ids"][0],
            results["documents"][0],
            results["distances"][0],
            strict=False,
        )
    ):
        if 1 - dist < similarity_threshold:
            continue
        content = (doc[:100] + "...") if len(doc) > 100 else doc
        row = [str(i + 1), doc_id, content.replace("\n", " "), f"{1 - dist:.3f}"]
        if include_metadata and i < len(results.get("metadatas", [[]])[0]):
            meta = results["metadatas"][0][i]
            if meta:
                row.append(str(meta)[:50])
            else:
                row.append("")
        table.add_row(*row)
    console.print(table)


def _format_results(results: dict[str, Any], include_metadata: bool) -> Any:
    if "distances" in results:
        formatted = []
        for i, (doc_id, doc, dist) in enumerate(
            zip(
                results["ids"][0],
                results["documents"][0],
                results["distances"][0],
                strict=False,
            )
        ):
            item = {"id": doc_id, "content": doc, "similarity": 1 - dist}
            if (
                include_metadata
                and results.get("metadatas")
                and i < len(results["metadatas"][0])
            ):
                item["metadata"] = results["metadatas"][0][i]
            formatted.append(item)
        return formatted
    item = {"id": results["ids"][0], "content": results["documents"][0]}
    if include_metadata and results.get("metadatas"):
        item["metadata"] = results["metadatas"][0]
    return item
