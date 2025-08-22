"""File processing utilities for the CLI."""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from ..core.chunking.engine import ChunkingEngine
from ..core.metadata import MetadataExtractor
from ..core.parser import MarkdownParser
from ..utils.logging import get_logger


console = Console()
logger = get_logger(__name__)


def process_file(
    file_path: Path,
    parser: MarkdownParser,
    chunker: ChunkingEngine,
    metadata_extractor: MetadataExtractor,
    store: str | None,
    collection: str | None,
    include_metadata: bool,
    preserve_structure: bool,
    dry_run: bool,
    quiet: bool,
) -> dict | None:
    """Process a single markdown file."""
    try:
        # Read file
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            return None

        # Parse and chunk
        ast = parser.parse(content)
        chunks = chunker.chunk_document(ast)

        if not chunks:
            return None

        # Add metadata if requested
        if include_metadata:
            file_metadata = metadata_extractor.extract_file_metadata(file_path)
            doc_metadata = metadata_extractor.extract_document_metadata(ast)

            for chunk in chunks:
                chunk.metadata.update(file_metadata)
                chunk.metadata.update(doc_metadata)
                chunk.metadata["source_file"] = str(file_path)
        else:
            # Always include source file at minimum
            for chunk in chunks:
                chunk.metadata["source_file"] = str(file_path)

        # Store if requested (and not a dry run)
        if store and not dry_run:
            # Determine storage type
            storage_type = "vectordb" if store in [True, "True", "true", ""] else store

            # Validate collection name for vectordb
            if storage_type == "vectordb" and not collection:
                if not quiet:
                    console.print(
                        "[red]Error:[/red] --collection is required with --store"
                    )
                return None

        if store and not dry_run and storage_type == "vectordb":
            try:
                from ..storage.vectordb import VectorDBStorage

                storage = VectorDBStorage()
                if storage.is_available():
                    # Collection must be non-None here due to validation above
                    if collection is None:
                        raise ValueError(
                            "Collection name is required for vectordb storage"
                        )
                    # Convert chunks to dictionaries for storage
                    chunk_dicts = [
                        {"content": chunk.content, "metadata": chunk.metadata}
                        for chunk in chunks
                    ]
                    storage.store(chunk_dicts, collection)
                    if not quiet:
                        console.print(
                            f"[green]✓[/green] Stored {len(chunks)} chunks "
                            f"from {file_path.name} to collection '{collection}'"
                        )
                else:
                    if not quiet:
                        console.print(
                            "[yellow]Warning:[/yellow] Vector database not available"
                        )
            except ImportError:
                if not quiet:
                    console.print("[yellow]Storage backend not available[/yellow]")

        return {"file": file_path.name, "chunks": chunks, "count": len(chunks)}

    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")
        return None


def display_results(results: list[dict]) -> None:
    """Display processing results in a table."""
    table = Table(title="Processing Results")
    table.add_column("File", style="cyan")
    table.add_column("Chunks", justify="right", style="green")
    table.add_column("Avg Size", justify="right")

    total_chunks = 0
    for result in results:
        chunks = result["chunks"]
        avg_size = sum(len(c.content) for c in chunks) // len(chunks) if chunks else 0
        table.add_row(result["file"], str(result["count"]), str(avg_size))
        total_chunks += result["count"]

    console.print(table)
    console.print(f"\nTotal chunks: {total_chunks}")
