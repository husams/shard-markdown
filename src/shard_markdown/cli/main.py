"""Main CLI application using Click framework."""

import sys
from pathlib import Path

import click
from rich.traceback import install

from ..config import load_config
from ..utils.logging import setup_logging
from .commands import collections, config, process, query
from .utils import console


# Install rich tracebacks for better error display
install(show_locals=True)


@click.group()
@click.option(
    "--config", "-c", type=click.Path(exists=True), help="Configuration file path"
)
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (can be repeated: -v, -vv, -vvv)",
)
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-error output")
@click.option("--log-file", type=click.Path(), help="Write logs to specified file")
@click.version_option(version="0.1.0", prog_name="shard-md")
@click.pass_context
def cli(
    ctx: click.Context, config: str, verbose: int, quiet: bool, log_file: str
) -> None:
    """Shard Markdown - Intelligent document chunking for ChromaDB.

    This tool processes markdown documents into intelligent chunks and stores
    them in ChromaDB collections for efficient retrieval and processing.

    Examples:
      # Process a single document
      shard-md process --collection my-docs document.md

      # Process multiple documents with custom settings
      shard-md process --collection tech-docs --chunk-size 1500 *.md

      # List available collections
      shard-md collections list

      # Query a collection
      shard-md query search --collection my-docs "search term"
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    try:
        # Load configuration
        config_path = Path(config) if config else None
        app_config = load_config(config_path)
        ctx.obj["config"] = app_config

        # Setup logging
        log_level = (
            40 if quiet else max(10, 30 - (verbose * 10))
        )  # DEBUG=10, INFO=20, WARNING=30, ERROR=40
        log_file_path = Path(log_file) if log_file else app_config.logging.file_path

        setup_logging(
            level=log_level,
            file_path=log_file_path,
            max_file_size=app_config.logging.max_file_size,
            backup_count=app_config.logging.backup_count,
        )

        # Store CLI options for commands
        ctx.obj["verbose"] = verbose
        ctx.obj["quiet"] = quiet
        ctx.obj["log_file"] = log_file

    except (OSError, ValueError) as e:
        console.print(f"[red]Error initializing shard-md:[/red] {str(e)}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error initializing shard-md:[/red] {str(e)}")
        sys.exit(1)


@cli.command()
@click.pass_context
def version(ctx: click.Context) -> None:
    """Show version information."""
    console.print("shard-md version 0.1.0")
    console.print("Intelligent markdown document chunking for ChromaDB")


# Register command groups
cli.add_command(process.process)
cli.add_command(collections.collections)
cli.add_command(query.query)
cli.add_command(config.config)


def main() -> None:
    """Entry point for the CLI application."""
    cli()


if __name__ == "__main__":
    main()
