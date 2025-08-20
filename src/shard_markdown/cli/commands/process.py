"""Process command for document processing."""

from pathlib import Path
from typing import Any

import click
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from ...chromadb.collections import CollectionManager
from ...chromadb.factory import create_chromadb_client
from ...core.models import BatchResult, ProcessingResult
from ...core.processor import DocumentProcessor
from ...utils.errors import ShardMarkdownError
from ...utils.logging import get_logger
from ...utils.validation import (
    validate_chunk_parameters,
    validate_collection_name,
    validate_input_paths,
)
from ..utils import console


logger = get_logger(__name__)


@click.command()
@click.argument("input_paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.option(
    "--collection", "-c", required=True, help="Target ChromaDB collection name"
)
@click.option(
    "--chunk-size",
    "-s",
    default=1000,
    type=int,
    help="Maximum chunk size in characters [default: 1000]",
)
@click.option(
    "--chunk-overlap",
    "-o",
    default=200,
    type=int,
    help="Overlap between chunks in characters [default: 200]",
)
@click.option(
    "--chunk-method",
    type=click.Choice(["structure", "fixed"]),
    default="structure",
    help="Chunking method [default: structure]",
)
@click.option("--recursive", "-r", is_flag=True, help="Process directories recursively")
@click.option(
    "--create-collection",
    is_flag=True,
    help="Create collection if it doesn't exist",
)
@click.option(
    "--clear-collection",
    is_flag=True,
    help="Clear existing collection before processing",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be processed without executing",
)
@click.option(
    "--collection-metadata",
    help="Additional metadata for new collections (JSON format)",
)
@click.pass_context
def process(  # noqa: C901
    ctx: click.Context,
    input_paths: tuple,
    collection: str,
    chunk_size: int,
    chunk_overlap: int,
    chunk_method: str,
    recursive: bool,
    create_collection: bool,
    clear_collection: bool,
    dry_run: bool,
    collection_metadata: str | None,
) -> None:
    """Process markdown files into ChromaDB collections.

    This command processes one or more markdown files, intelligently chunks
    them based on document structure, and stores the results in a ChromaDB
    collection.

    Examples:
      # Process a single file
      shard-md process --collection my-docs document.md

      # Process multiple files with custom chunking
      shard-md process -c tech-docs --chunk-size 1500 --chunk-overlap 300 *.md

      # Process directory recursively
      shard-md process -c all-docs --recursive ./docs/

      # Create new collection and clear it first
      shard-md process -c new-docs --create-collection --clear-collection *.md
    """
    # Handle cases where ctx.obj might be None (e.g., in tests)
    if ctx.obj is None:
        ctx.obj = {}

    config = ctx.obj.get("config")
    if config is None:
        # Create a default config for testing
        from ...config.settings import Settings

        config = Settings()

    verbose = ctx.obj.get("verbose", 0)

    try:
        # Validate and prepare
        validated_paths = _validate_and_prepare(
            input_paths, chunk_size, chunk_overlap, collection, recursive
        )
        if dry_run:
            _show_dry_run_preview(
                validated_paths, collection, chunk_size, chunk_overlap
            )
            return

        console.print(
            f"[blue]Processing {len(validated_paths)} markdown files...[/blue]"
        )

        # Setup ChromaDB and collection
        chroma_client, collection_obj = _setup_chromadb_and_collection(
            config, collection, clear_collection, create_collection
        )

        # Initialize processor
        from ...config.settings import ChunkingParams

        processor = DocumentProcessor(
            ChunkingParams(
                chunk_size=chunk_size, overlap=chunk_overlap, method=chunk_method
            )
        )

        # Process files
        _process_files_with_progress(
            validated_paths,
            collection,
            processor,
            chroma_client,
            collection_obj,
            verbose,
        )

    except ShardMarkdownError as e:
        _handle_shard_error(e, verbose)
    except Exception as e:
        _handle_unexpected_error(e, verbose)


def _validate_and_prepare(
    input_paths: tuple,
    chunk_size: int,
    chunk_overlap: int,
    collection: str,
    recursive: bool,
) -> list[Path]:
    """Validate parameters and prepare input paths."""
    validate_chunk_parameters(chunk_size, chunk_overlap)
    validate_collection_name(collection)
    return validate_input_paths(list(input_paths), recursive)


def _setup_chromadb_and_collection(
    config: Any,
    collection: str,
    clear_collection: bool,
    create_collection: bool,
) -> tuple:
    """Set up ChromaDB client and collection."""
    from ...utils.errors import ChromaDBError, NetworkError

    chroma_client = create_chromadb_client(config.get_chromadb_params())
    try:
        if not chroma_client.connect():
            raise click.ClickException("Failed to connect to ChromaDB")
    except (NetworkError, ChromaDBError) as e:
        # Re-raise with the specific error message from the exception
        raise click.ClickException(str(e)) from e

    collection_manager = CollectionManager(chroma_client)

    # Handle collection clearing
    if clear_collection:
        _handle_collection_clearing(chroma_client, collection_manager, collection)

    collection_obj = chroma_client.get_or_create_collection(
        collection, create_if_missing=create_collection
    )
    return chroma_client, collection_obj


def _handle_collection_clearing(
    chroma_client: Any, collection_manager: CollectionManager, collection: str
) -> None:
    """Handle collection clearing if requested."""
    try:
        chroma_client.get_collection(collection)
        if click.confirm(f"Clear all documents from collection '{collection}'?"):
            try:
                collection_manager.clear_collection(collection)
                console.print(f"[yellow]Cleared collection '{collection}'[/yellow]")
            except AttributeError:
                console.print(
                    "[yellow]Collection clearing not implemented in "
                    "mock client[/yellow]"
                )
    except (ValueError, RuntimeError):
        pass  # Collection doesn't exist


def _process_files_with_progress(
    validated_paths: list[Path],
    collection: str,
    processor: Any,
    chroma_client: Any,
    collection_obj: Any,
    verbose: int,
) -> None:
    """Process files with progress tracking."""
    progress_config = [
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
    ]
    with Progress(*progress_config) as progress:
        if len(validated_paths) == 1:
            _process_single_file(
                validated_paths[0],
                collection,
                processor,
                chroma_client,
                collection_obj,
                progress,
            )
        else:
            _process_batch_files(
                validated_paths,
                collection,
                processor,
                chroma_client,
                collection_obj,
                verbose,
                progress,
            )


def _process_single_file(
    file_path: Path,
    collection: str,
    processor: Any,
    chroma_client: Any,
    collection_obj: Any,
    progress: Any,
) -> None:
    """Process a single file."""
    task = progress.add_task("Processing document...", total=1)
    result = processor.process_document(file_path, collection)
    progress.update(task, advance=1)

    if not result.success:
        console.print(f"[red]Processing failed: {result.error}[/red]")
        return

    # Get and insert chunks
    content = processor._read_file(file_path)
    ast = processor.parser.parse(content)
    chunks = processor._enhance_chunks(
        processor.chunker.chunk_document(ast),
        processor.metadata_extractor.extract_file_metadata(file_path),
        processor.metadata_extractor.extract_document_metadata(ast),
        file_path,
    )

    insert_result = chroma_client.bulk_insert(collection_obj, chunks)
    if insert_result.success:
        _display_single_result(result, insert_result)
    else:
        console.print(f"[red]Failed to insert chunks: {insert_result.error}[/red]")


def _process_batch_files(
    validated_paths: list[Path],
    collection: str,
    processor: Any,
    chroma_client: Any,
    collection_obj: Any,
    verbose: int,
    progress: Any,
) -> None:
    """Process multiple files in batch."""
    batch_result = processor.process_batch(validated_paths, collection)

    # Collect all chunks from successful results
    all_chunks = []
    for result in batch_result.results:
        if result.success:
            try:
                content = processor._read_file(result.file_path)
                ast = processor.parser.parse(content)
                chunks = processor.chunker.chunk_document(ast)

                metadata_pair = (
                    processor.metadata_extractor.extract_file_metadata(
                        result.file_path
                    ),
                    processor.metadata_extractor.extract_document_metadata(ast),
                )
                enhanced_chunks = processor._enhance_chunks(
                    chunks, metadata_pair[0], metadata_pair[1], result.file_path
                )
                all_chunks.extend(enhanced_chunks)
            except Exception as e:
                logger.error(f"Failed to get chunks for {result.file_path}: {e}")

    if all_chunks:
        insert_task = progress.add_task(
            f"Inserting {len(all_chunks)} chunks...", total=1
        )
        insert_result = chroma_client.bulk_insert(collection_obj, all_chunks)
        progress.update(insert_task, advance=1)
        _display_batch_results(batch_result, insert_result, verbose)
    else:
        console.print("[red]No chunks to insert[/red]")


def _handle_shard_error(e: ShardMarkdownError, verbose: int) -> None:
    """Handle ShardMarkdownError exceptions."""
    console.print(f"[red]Error:[/red] {e.message}")
    if verbose > 0:
        console.print(f"[dim]Error code: {e.error_code}[/dim]")
        if e.context:
            console.print(f"[dim]Context: {e.context}[/dim]")
    raise click.Abort()


def _handle_unexpected_error(e: Exception, verbose: int) -> None:
    """Handle unexpected exceptions."""
    console.print(f"[red]Unexpected error:[/red] {str(e)}")
    if verbose > 1:
        console.print_exception()
    raise click.Abort()


def _show_dry_run_preview(
    paths: list[Path], collection: str, chunk_size: int, chunk_overlap: int
) -> None:
    """Display dry run preview of what would be processed."""
    table = Table(title="Dry Run Preview")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Collection", collection)
    table.add_row("Chunk Size", str(chunk_size))
    table.add_row("Chunk Overlap", str(chunk_overlap))
    table.add_row("Files to Process", str(len(paths)))

    console.print(table)

    console.print("[blue]Files to be processed:[/blue]")
    for i, path in enumerate(paths[:10]):  # Show first 10 files
        console.print(f"  {i + 1:2d}. {path}")

    if len(paths) > 10:
        console.print(f"  ... and {len(paths) - 10} more files")


def _display_single_result(
    processing_result: ProcessingResult, insert_result: Any
) -> None:
    """Display results for single file processing."""
    table = Table(title="Processing Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("File", str(processing_result.file_path.name))
    table.add_row("Chunks Created", str(processing_result.chunks_created))
    table.add_row("Processing Time", f"{processing_result.processing_time:.2f}s")
    table.add_row("Chunks Inserted", str(insert_result.chunks_inserted))
    table.add_row("Insertion Time", f"{insert_result.processing_time:.2f}s")

    console.print(table)
    console.print(
        f"[green]✓ Successfully processed and stored "
        f"{processing_result.chunks_created} chunks[/green]"
    )


def _display_batch_results(
    batch_result: BatchResult, insert_result: Any, verbose: int
) -> None:
    """Display results for batch processing."""
    # Summary table
    table = Table(title="Batch Processing Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Total Files", str(batch_result.total_files))
    table.add_row("Successful", str(batch_result.successful_files))
    table.add_row("Failed", str(batch_result.failed_files))
    table.add_row("Success Rate", f"{batch_result.success_rate:.1f}%")
    table.add_row("Total Chunks", str(batch_result.total_chunks))
    table.add_row("Avg Chunks/File", f"{batch_result.average_chunks_per_file:.1f}")
    table.add_row("Processing Time", f"{batch_result.total_processing_time:.2f}s")
    table.add_row("Processing Speed", f"{batch_result.processing_speed:.1f} files/s")

    if insert_result.success:
        table.add_row("Chunks Inserted", str(insert_result.chunks_inserted))
        table.add_row("Insertion Time", f"{insert_result.processing_time:.2f}s")
        table.add_row("Insertion Rate", f"{insert_result.insertion_rate:.1f} chunks/s")

    console.print(table)

    # Show failed files if any
    if batch_result.failed_files > 0 and verbose > 0:
        console.print(f"[red]Failed files ({batch_result.failed_files}):[/red]")
        for result in batch_result.results:
            if not result.success:
                console.print(f"  • {result.file_path.name}: {result.error}")

    if insert_result.success:
        console.print(
            f"[green]✓ Successfully processed "
            f"{batch_result.successful_files} files and stored "
            f"{insert_result.chunks_inserted} chunks[/green]"
        )
    else:
        console.print(
            f"[red]✗ Processing completed but insertion failed: "
            f"{insert_result.error}[/red]"
        )
