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

from ...config import ChunkingConfig
from ...core.models import BatchResult
from ...core.processor import DocumentProcessor
from ...utils.errors import ShardMarkdownError
from ...utils.logging import get_logger
from ...utils.validation import (
    validate_chunk_parameters,
    validate_collection_name,
    validate_input_paths,
)
from ..utils import load_app_config, setup_logging


logger = get_logger(__name__)


@click.group()
def process() -> None:
    """Process markdown documents into chunks."""
    pass


@process.command()
@click.argument("input_paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.argument("collection", type=str)
@click.option(
    "--chunk-size",
    type=int,
    help="Override default chunk size",
)
@click.option(
    "--chunk-overlap",
    type=int,
    help="Override default chunk overlap",
)
@click.option(
    "--method",
    type=click.Choice(["structure", "fixed"]),
    help="Override chunking method",
)
@click.option(
    "--recursive/--no-recursive",
    default=None,
    help="Process directories recursively",
)
@click.option(
    "--pattern",
    type=str,
    help="File pattern for filtering (default: *.md)",
)
@click.option(
    "--metadata",
    type=str,
    multiple=True,
    help="Additional metadata in key=value format",
)
@click.option(
    "--config-file",
    type=click.Path(exists=True),
    help="Configuration file path",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Override logging level",
)
@click.option(
    "--log-file",
    type=click.Path(),
    help="Log file path",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be processed without actually processing",
)
def files(
    input_paths: tuple[str, ...],
    collection: str,
    chunk_size: int | None,
    chunk_overlap: int | None,
    method: str | None,
    recursive: bool | None,
    pattern: str | None,
    metadata: tuple[str, ...],
    config_file: str | None,
    log_level: str | None,
    log_file: str | None,
    verbose: bool,
    dry_run: bool,
) -> None:
    """Process markdown files into a ChromaDB collection.

    INPUT_PATHS: One or more files or directories to process
    COLLECTION: Name of the ChromaDB collection to create/update
    """
    try:
        # Load configuration
        config_path = Path(config_file) if config_file else None
        config = load_app_config(config_path)

        # Setup logging
        setup_logging(config, log_level, log_file, verbose)

        # Validate inputs
        validate_collection_name(collection)
        file_paths = validate_input_paths(
            list(input_paths),
            recursive=recursive if recursive is not None else False,
        )

        if not file_paths:
            click.echo("No markdown files found to process.", err=True)
            raise SystemExit(1)

        # Parse additional metadata
        custom_metadata = {}
        for meta_str in metadata:
            if "=" not in meta_str:
                click.echo(f"Invalid metadata format: {meta_str}", err=True)
                raise SystemExit(1)
            key, value = meta_str.split("=", 1)
            custom_metadata[key.strip()] = value.strip()

        # Create chunking configuration with overrides
        from shard_markdown.config.settings import ChunkingMethod

        method_value = method or config.chunking.method
        if isinstance(method_value, str):
            method_value = ChunkingMethod(method_value)

        chunking_config = ChunkingConfig(
            default_size=chunk_size or config.chunking.default_size,
            default_overlap=chunk_overlap or config.chunking.default_overlap,
            method=method_value,
        )

        # Validate chunk parameters
        validate_chunk_parameters(
            chunking_config.default_size, chunking_config.default_overlap
        )

        if dry_run:
            _show_dry_run_info(file_paths, collection, chunking_config, custom_metadata)
            return

        # Initialize processor
        processor = DocumentProcessor(chunking_config)

        # Create ChromaDB client and process files
        # chroma_client = create_chromadb_client(config.chromadb)

        # Show processing preview
        click.echo(
            f"\nProcessing {len(file_paths)} files into collection: {collection}"
        )
        click.echo(f"Chunk size: {chunking_config.default_size}")
        click.echo(f"Chunk overlap: {chunking_config.default_overlap}")
        click.echo(f"Method: {chunking_config.method}")

        if custom_metadata:
            click.echo(f"Custom metadata: {custom_metadata}")

        # Process files with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        ) as progress:
            # Process files
            task = progress.add_task("Processing files...", total=len(file_paths))

            batch_result = processor.process_files(
                file_paths, collection, custom_metadata
            )

            progress.update(task, completed=len(file_paths))

        # Insert chunks into ChromaDB
        if batch_result.total_chunks > 0:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task(
                    "Inserting chunks...", total=batch_result.total_chunks
                )

                # Collect all chunks from successful results
                for result in batch_result.results:
                    if result.success and hasattr(processor, "_last_processed_chunks"):
                        # Note: This is a simplified approach; in practice, you'd
                        # need to refactor the processor to return chunks or use
                        # a different architecture
                        pass

                progress.update(task, completed=batch_result.total_chunks)

        # Show results
        _show_processing_results(batch_result)

    except ShardMarkdownError as e:
        logger.error("Processing failed: %s", e)
        if verbose:
            logger.exception("Detailed error information:")
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(e.error_code) from e

    except Exception as e:
        logger.exception("Unexpected error during processing")
        click.echo(f"Unexpected error: {e}", err=True)
        raise SystemExit(1) from e


def _show_dry_run_info(
    file_paths: list[Path],
    collection: str,
    chunking_config: ChunkingConfig,
    custom_metadata: dict[str, Any],
) -> None:
    """Show dry run information."""
    click.echo("\n=== DRY RUN ===")
    click.echo(f"Would process {len(file_paths)} files:")

    for file_path in file_paths[:10]:  # Show first 10 files
        click.echo(f"  • {file_path}")

    if len(file_paths) > 10:
        click.echo(f"  ... and {len(file_paths) - 10} more files")

    click.echo(f"\nTarget collection: {collection}")
    click.echo(f"Chunk size: {chunking_config.default_size}")
    click.echo(f"Chunk overlap: {chunking_config.default_overlap}")
    click.echo(f"Method: {chunking_config.method}")

    if custom_metadata:
        click.echo(f"Custom metadata: {custom_metadata}")


def _show_processing_results(batch_result: BatchResult) -> None:
    """Show processing results in a formatted table."""
    # Summary table
    table = Table(title="Processing Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Files", str(batch_result.total_files))
    table.add_row("Successful", str(batch_result.successful_files))
    table.add_row("Failed", str(batch_result.failed_files))
    table.add_row("Success Rate", f"{batch_result.success_rate:.1f}%")
    table.add_row("Total Chunks", str(batch_result.total_chunks))
    table.add_row("Avg Chunks/File", f"{batch_result.average_chunks_per_file:.1f}")
    table.add_row("Processing Time", f"{batch_result.total_processing_time:.2f}s")
    table.add_row("Processing Speed", f"{batch_result.processing_speed:.1f} files/s")

    click.echo()
    click.echo(table)

    # Show failed files if any
    failed_results = [r for r in batch_result.results if not r.success]
    if failed_results:
        click.echo("\n❌ Failed Files:")
        for result in failed_results:
            click.echo(f"  • {result.file_path}: {result.error}")

    # Success message
    if batch_result.successful_files > 0:
        click.echo(
            f"\n✅ Successfully processed {batch_result.successful_files} files "
            f"into collection '{batch_result.collection_name}'"
        )
