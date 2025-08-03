"""Query command for searching and retrieving documents."""

import json

import click
from rich.console import Console
from rich.table import Table

from ...chromadb.factory import create_chromadb_client
from ...utils.errors import ShardMarkdownError
from ...utils.logging import get_logger

_logger = get_logger(__name__)
console = Console()


@click.group()
def query():
    """Query and search documents in collections.
    This command group provides functionality to search for documents
    in ChromaDB collections using similarity search and retrieve
    specific documents by ID.

    Examples:

      # Search for documents
      shard-md query search --collection my-docs "search term"

      # Get a specific document
      shard-md query get --collection my-docs doc_id_123
    """
    pass


@query.command()
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
    ctx,
    query_text,
    collection,
    limit,
    similarity_threshold,
    include_metadata,
    format,
):
    """Search for documents using similarity search."""
    config = ctx.obj["config"]
    verbose = ctx.obj.get("verbose", 0)

    try:
        # Initialize ChromaDB client
        chroma_client = create_chromadb_client(config.chromadb)
        if not chroma_client.connect():
            raise click.ClickException("Failed to connect to ChromaDB")

        # Get collection
        try:
            collection_obj = chroma_client.get_collection(collection)
        except Exception:
            raise click.ClickException(f"Collection '{collection}' not found")

        # Perform search
        console.print(
            f"[blue]Searching for: '{query_text}' in collection "
            f"'{collection}'[/blue]"
        )

        try:
            results = collection_obj.query(
                query_texts=[query_text], n_results=limit
            )
        except Exception as e:
            raise click.ClickException(f"Search failed: {str(e)}")

        # Process results
        if not results["ids"][0]:
            console.print("[yellow]No documents found[/yellow]")
            return

        # Display results
        if format == "table":
            _display_search_results_table(
                results, include_metadata, similarity_threshold
            )
        elif format == "json":
            formatted_results = _format_search_results(
                results, include_metadata
            )
            console.print(json.dumps(formatted_results, indent=2))
        elif format == "yaml":
            import yaml

            formatted_results = _format_search_results(
                results, include_metadata
            )
            console.print(
                yaml.dump(formatted_results, default_flow_style=False)
            )

        count = len(results["ids"][0])
        console.print(f"[green]Found {count} document(s)[/green]")

    except ShardMarkdownError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if verbose > 0:
            console.print(f"[dim]Error code: {e.error_code}[/dim]")
        raise click.Abort()

    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        if verbose > 1:
            console.print_exception()
        raise click.Abort()


@query.command()
@click.argument("document_id")
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
def get(ctx, document_id, collection, format, include_metadata):  # noqa: C901
    """Get a specific document by ID."""
    config = ctx.obj["config"]
    verbose = ctx.obj.get("verbose", 0)

    try:
        # Initialize ChromaDB client
        chroma_client = create_chromadb_client(config.chromadb)
        if not chroma_client.connect():
            raise click.ClickException("Failed to connect to ChromaDB")

        # Get collection
        try:
            collection_obj = chroma_client.get_collection(collection)
        except Exception:
            raise click.ClickException(f"Collection '{collection}' not found")

        # Get document
        console.print(
            f"[blue]Retrieving document '{document_id}' from collection "
            f"'{collection}'[/blue]"
        )

        try:
            results = collection_obj.get(
                ids=[document_id],
                include=(
                    ["documents", "metadatas"]
                    if include_metadata
                    else ["documents"]
                ),
            )
        except Exception as e:
            raise click.ClickException(
                f"Failed to retrieve document: {str(e)}"
            )

        # Check if document exists
        if not results["ids"]:
            console.print(
                f"[yellow]Document '{document_id}' not found[/yellow]"
            )
            return

        # Display result
        if format == "table":
            _display_document_table(results, include_metadata)
        elif format == "json":
            formatted_result = _format_document_result(
                results, include_metadata
            )
            console.print(json.dumps(formatted_result, indent=2))
        elif format == "yaml":
            import yaml

            formatted_result = _format_document_result(
                results, include_metadata
            )
            console.print(
                yaml.dump(formatted_result, default_flow_style=False)
            )

        console.print("[green]✓ Document retrieved successfully[/green]")

    except ShardMarkdownError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if verbose > 0:
            console.print(f"[dim]Error code: {e.error_code}[/dim]")
        raise click.Abort()

    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        if verbose > 1:
            console.print_exception()
        raise click.Abort()


def _display_search_results_table(
    results, include_metadata, similarity_threshold
):
    """Display search results in table format."""
    table = Table(title="Search Results")
    table.add_column("Rank", style="cyan", width=6)
    table.add_column("ID", style="white")
    table.add_column("Content Preview", style="white")
    table.add_column("Distance", style="yellow", width=10)

    if include_metadata:
        table.add_column("Metadata", style="dim")

    ids = results["ids"][0]
    documents = results["documents"][0]
    distances = results["distances"][0]
    metadatas = (
        results.get("metadatas", [[]])[0] if include_metadata else []
    )

    for i, (doc_id, doc, distance) in enumerate(
        zip(ids, documents, distances)
    ):
        # Skip if below similarity threshold
        similarity = 1 - distance  # Convert distance to similarity
        if similarity < similarity_threshold:
            continue

        # Truncate content for preview
        content_preview = doc[:100] + "..." if len(doc) > 100 else doc
        content_preview = content_preview.replace("\n", " ")

        row = [str(i + 1), doc_id, content_preview, f"{similarity:.3f}"]

        if include_metadata and i < len(metadatas):
            metadata = metadatas[i] if metadatas else {}
            if metadata:
                # Show key metadata fields
                key_fields = [
                    "source_file",
                    "chunk_index",
                    "structural_context",
                ]
                metadata_str = ", ".join([
                    f"{k}: {v}"
                    for k, v in metadata.items()
                    if k in key_fields and v is not None
                ])
                if len(metadata_str) > 50:
                    metadata_str = metadata_str[:47] + "..."
                row.append(metadata_str or "")
            else:
                row.append("")

        table.add_row(*row)

    console.print(table)


def _display_document_table(results, include_metadata):
    """Display document in table format."""
    doc_id = results["ids"][0]
    document = results["documents"][0]
    metadata = (
        results.get("metadatas", [{}])[0] if include_metadata else {}
    )

    table = Table(title=f"Document: {doc_id}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("ID", doc_id)
    table.add_row("Content Length", f"{len(document)} characters")

    if include_metadata and metadata:
        for key, value in metadata.items():
            table.add_row(f"Metadata.{key}", str(value))

    console.print(table)

    # Display content in a separate section
    console.print("[blue]Content:[/blue]")
    console.print(f"[white]{document}[/white]")


def _format_search_results(results, include_metadata):
    """Format search results for JSON/YAML output."""
    ids = results["ids"][0]
    documents = results["documents"][0]
    distances = results["distances"][0]
    metadatas = (
        results.get("metadatas", [[]])[0] if include_metadata else []
    )

    formatted = []
    for i, (doc_id, doc, distance) in enumerate(
        zip(ids, documents, distances)
    ):
        result = {
            "id": doc_id,
            "content": doc,
            "distance": distance,
            "similarity": 1 - distance,
        }

        if include_metadata and i < len(metadatas) and metadatas[i]:
            result["metadata"] = metadatas[i]

        formatted.append(result)

    return formatted


def _format_document_result(results, include_metadata):
    """Format document result for JSON/YAML output."""
    result = {"id": results["ids"][0], "content": results["documents"][0]}

    metadata_exists = (
        include_metadata
        and results.get("metadatas")
        and results["metadatas"][0]
    )
    if metadata_exists:
        result["metadata"] = results["metadatas"][0]

    return result
