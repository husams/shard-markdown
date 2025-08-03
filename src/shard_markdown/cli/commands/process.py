"""Process command for document processing."""

from pathlib import Path
from typing import List

import click
from rich.console import Console
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
from ...core.models import ChunkingConfig
from ...core.processor import DocumentProcessor
from ...utils.errors import ShardMarkdownError
from ...utils.logging import get_logger
from ...utils.validation import (
    validate_chunk_parameters,
    validate_collection_name,
    validate_input_paths,
)

logger = get_logger(__name__)
console = Console()


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
    "--create-collection", is_flag=True, help="Create collection if it doesn't exist"
)
@click.option(
    "--clear-collection",
    is_flag=True,
    help="Clear existing collection before processing",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be processed without executing"
)
@click.option(
    "--max-workers",
    default=4,
    type=int,
    help="Maximum worker threads for processing [default: 4]",
)
@click.option(
    "--collection-metadata",
    help="Additional metadata for new collections (JSON format)",
)
@click.option(
    "--use-mock", is_flag=True, help="Force use of mock ChromaDB client for testing"
)
@click.pass_context
def process(
    ctx,
    input_paths,
    collection,
    chunk_size,
    chunk_overlap,
    chunk_method,
    recursive,
    create_collection,
    clear_collection,
    dry_run,
    max_workers,
    collection_metadata,
    use_mock,
):
    """Process markdown files into ChromaDB collections.

    This command processes one or more markdown files, intelligently chunks them
    based on document structure, and stores the results in a ChromaDB collection.

    Examples:

      # Process a single file
      shard-md process --collection my-docs document.md

      # Process multiple files with custom chunking
      shard-md process -c tech-docs --chunk-size 1500 --chunk-overlap 300 *.md

      # Process directory recursively
      shard-md process -c all-docs --recursive ./docs/

      # Create new collection and clear it first
      shard-md process -c new-docs --create-collection --clear-collection *.md

      # Use mock ChromaDB for testing
      shard-md process -c test-docs --use-mock *.md
    """
    config = ctx.obj["config"]
    verbose = ctx.obj.get("verbose", 0)

    try:
        # Validate parameters
        validate_chunk_parameters(chunk_size, chunk_overlap)
        validate_collection_name(collection)

        # Validate and collect input files
        validated_paths = validate_input_paths(list(input_paths), recursive)

        if dry_run:
            _show_dry_run_preview(
                validated_paths, collection, chunk_size, chunk_overlap
            )
            return

        console.print(
            f"[blue]Processing {len(validated_paths)} markdown files...[/blue]"
        )

        # Initialize ChromaDB client (with automatic mock fallback)
        chroma_client = create_chromadb_client(config.chromadb, use_mock=use_mock)
        if not chroma_client.connect():
            raise click.ClickException("Failed to connect to ChromaDB")

        # Handle collection creation/clearing
        collection_manager = CollectionManager(chroma_client)

        # Check if collection exists for clearing
        try:
            collection_exists = hasattr(chroma_client, "get_collection")
            if collection_exists:
                try:
                    chroma_client.get_collection(collection)
                    collection_exists = True
                except Exception:
                    collection_exists = False
        except Exception:
            collection_exists = False

        if clear_collection and collection_exists:
            if click.confirm(f"Clear all documents from collection '{collection}'?"):
                try:
                    collection_manager.clear_collection(collection)
                    console.print(f"[yellow]Cleared collection '{collection}'[/yellow]")
                except AttributeError:
                    console.print(
                        "[yellow]Collection clearing not implemented in mock client[/yellow]"
                    )

        # Get or create collection
        collection_obj = chroma_client.get_or_create_collection(
            collection, create_if_missing=create_collection
        )

        # Initialize document processor
        chunking_config = ChunkingConfig(
            chunk_size=chunk_size, overlap=chunk_overlap, method=chunk_method
        )
        processor = DocumentProcessor(chunking_config)

        # Process documents with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
        ) as progress:

            if len(validated_paths) == 1:
                # Single file processing
                task = progress.add_task("Processing document...", total=1)

                result = processor.process_document(validated_paths[0], collection)
                progress.update(task, advance=1)

                if result.success:
                    # Insert chunks into ChromaDB
                    chunks = processor._enhance_chunks(
                        processor.chunker.chunk_document(
                            processor.parser.parse(
                                processor._read_file(validated_paths[0])
                            )
                        ),
                        processor.metadata_extractor.extract_file_metadata(
                            validated_paths[0]
                        ),
                        processor.metadata_extractor.extract_document_metadata(
                            processor.parser.parse(
                                processor._read_file(validated_paths[0])
                            )
                        ),
                        validated_paths[0],
                    )

                    insert_result = chroma_client.bulk_insert(collection_obj, chunks)

                    if insert_result.success:
                        _display_single_result(result, insert_result)
                    else:
                        console.print(
                            f"[red]Failed to insert chunks: {insert_result.error}[/red]"
                        )
                else:
                    console.print(f"[red]Processing failed: {result.error}[/red]")

            else:
                # Batch processing
                batch_result = processor.process_batch(
                    validated_paths, collection, max_workers=max_workers
                )

                # Insert all successful chunks
                all_chunks = []
                for result in batch_result.results:
                    if result.success:
                        try:
                            # Re-process to get chunks (this is not optimal, should be refactored)
                            content = processor._read_file(result.file_path)
                            ast = processor.parser.parse(content)
                            chunks = processor.chunker.chunk_document(ast)

                            file_metadata = (
                                processor.metadata_extractor.extract_file_metadata(
                                    result.file_path
                                )
                            )
                            doc_metadata = (
                                processor.metadata_extractor.extract_document_metadata(
                                    ast
                                )
                            )

                            enhanced_chunks = processor._enhance_chunks(
                                chunks, file_metadata, doc_metadata, result.file_path
                            )
                            all_chunks.extend(enhanced_chunks)

                        except Exception as e:
                            logger.error(
                                f"Failed to get chunks for {result.file_path}: {e}"
                            )

                if all_chunks:
                    # Show insertion progress
                    insert_task = progress.add_task(
                        f"Inserting {len(all_chunks)} chunks...", total=1
                    )
                    insert_result = chroma_client.bulk_insert(
                        collection_obj, all_chunks
                    )
                    progress.update(insert_task, advance=1)

                    _display_batch_results(batch_result, insert_result, verbose)
                else:
                    console.print("[red]No chunks to insert[/red]")

    except ShardMarkdownError as e:
        console.print(f"[red]Error:[/red] {e.message}")
        if verbose > 0:
            console.print(f"[dim]Error code: {e.error_code}[/dim]")
            if e.context:
                console.print(f"[dim]Context: {e.context}[/dim]")
        raise click.Abort()

    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
        if verbose > 1:
            console.print_exception()
        raise click.Abort()


def _show_dry_run_preview(
    paths: List[Path], collection: str, chunk_size: int, chunk_overlap: int
):
    """Display dry run preview of what would be processed."""

    table = Table(title="Dry Run Preview")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Collection", collection)
    table.add_row("Chunk Size", str(chunk_size))
    table.add_row("Chunk Overlap", str(chunk_overlap))
    table.add_row("Files to Process", str(len(paths)))

    console.print(table)

    console.print(f"\n[blue]Files to be processed:[/blue]")
    for i, path in enumerate(paths[:10]):  # Show first 10 files
        console.print(f"  {i+1:2d}. {path}")

    if len(paths) > 10:
        console.print(f"  ... and {len(paths) - 10} more files")


def _display_single_result(processing_result, insert_result):
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
        f"[green]✓ Successfully processed and stored {processing_result.chunks_created} chunks[/green]"
    )


def _display_batch_results(batch_result, insert_result, verbose: int):
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
        console.print(f"\n[red]Failed files ({batch_result.failed_files}):[/red]")
        for result in batch_result.results:
            if not result.success:
                console.print(f"  • {result.file_path.name}: {result.error}")

    if insert_result.success:
        console.print(
            f"[green]✓ Successfully processed {batch_result.successful_files} files and stored {insert_result.chunks_inserted} chunks[/green]"
        )
    else:
        console.print(
            f"[red]✗ Processing completed but insertion failed: {insert_result.error}[/red]"
        )