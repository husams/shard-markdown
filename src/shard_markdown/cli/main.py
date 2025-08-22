"""Shard Markdown - Intelligent markdown document chunking."""

import sys
from pathlib import Path

import click

from ..config import load_config
from ..core.chunking.engine import ChunkingEngine
from ..core.metadata import MetadataExtractor
from ..core.parser import MarkdownParser
from ..utils.logging import setup_logging
from .processor import display_results, process_file


@click.command()
@click.argument("input", type=click.Path(exists=True), required=True)
@click.option("--size", "-s", default=1000, type=int, help="Chunk size (default: 1000)")
@click.option(
    "--overlap",
    "-o",
    default=200,
    type=int,
    help="Overlap between chunks (default: 200)",
)
@click.option(
    "--strategy",
    type=click.Choice(
        ["token", "sentence", "paragraph", "section", "semantic", "structure", "fixed"]
    ),
    default="token",
    help="Chunking strategy",
)
@click.option("--recursive", "-r", is_flag=True, help="Process directories recursively")
@click.option(
    "--store",
    is_flag=True,
    flag_value="vectordb",
    default=None,
    help="Store chunks in vector database",
)
@click.option(
    "--collection",
    type=str,
    default=None,
    help="Collection name for vectordb storage",
)
@click.option("--metadata", "-m", is_flag=True, help="Include metadata in chunks")
@click.option("--preserve-structure", is_flag=True, help="Maintain markdown structure")
@click.option("--dry-run", is_flag=True, help="Preview without storing")
@click.option(
    "--config-path", type=click.Path(exists=True), help="Use alternate config file"
)
@click.option("--quiet", "-q", is_flag=True, help="Suppress output (when storing)")
@click.option("--verbose", "-v", count=True, help="Verbose output")
@click.version_option(version="0.2.0", prog_name="shard-md")
def shard_md(
    input: str,
    size: int,
    overlap: int,
    strategy: str,
    recursive: bool,
    store: str | None,
    collection: str | None,
    metadata: bool,
    preserve_structure: bool,
    dry_run: bool,
    config_path: str | None,
    quiet: bool,
    verbose: int,
) -> None:
    """Intelligently chunk markdown documents.

    Process markdown files or directories into semantic chunks optimized
    for retrieval and analysis.

    Examples:
      # Simple usage - display chunks
      shard-md document.md

      # Display with custom settings
      shard-md docs/ --size 500 --overlap 50

      # Store in ChromaDB
      shard-md manual.md --store --collection documentation

      # Or explicitly specify vectordb
      shard-md manual.md --store vectordb --collection documentation

      # Dry run with verbose output
      shard-md large-doc.md --dry-run --verbose

      # Process with custom config
      shard-md book.md --config-path ./project-config.yaml

      # Process and store quietly
      shard-md *.md --store --collection my-docs --quiet
    """
    try:
        # Setup logging
        log_level = 40 if quiet else max(10, 30 - (verbose * 10))
        setup_logging(level=log_level)

        # Load configuration
        if config_path:
            config = load_config(Path(config_path))
        else:
            config = load_config()

        # Override config with CLI options
        if size != 1000:
            config.chunk_size = size
        if overlap != 200:
            config.chunk_overlap = overlap
        if strategy:
            # Map strategy to method for backward compatibility
            if strategy in ["structure", "fixed"]:
                config.chunk_method = strategy
            else:
                config.chunk_method = strategy  # Will be handled by new strategies

        # Initialize components
        parser = MarkdownParser()
        chunker = ChunkingEngine(config)
        metadata_extractor = MetadataExtractor()

        # Process input
        input_path = Path(input)
        all_results = []

        if input_path.is_file():
            if input_path.suffix.lower() in [".md", ".markdown"]:
                results = process_file(
                    input_path,
                    parser,
                    chunker,
                    metadata_extractor,
                    store,
                    collection,
                    metadata,
                    preserve_structure,
                    dry_run,
                    quiet,
                )
                if results:
                    all_results.append(results)
        elif input_path.is_dir():
            pattern = "**/*.md" if recursive else "*.md"
            for md_file in input_path.glob(pattern):
                results = process_file(
                    md_file,
                    parser,
                    chunker,
                    metadata_extractor,
                    store,
                    collection,
                    metadata,
                    preserve_structure,
                    dry_run,
                    quiet,
                )
                if results:
                    all_results.append(results)

        # Display results
        if not quiet and all_results:
            display_results(all_results)

    except Exception as e:
        from rich.console import Console

        Console().print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI application."""
    shard_md()


if __name__ == "__main__":
    main()
