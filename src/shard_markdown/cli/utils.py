"""Shared utilities for CLI commands."""

import sys
from typing import Any

import click
from rich.console import Console

from ..chromadb.factory import create_chromadb_client
from ..utils.errors import ShardMarkdownError


# Shared console instance for all CLI commands
console = Console()


def handle_chromadb_errors(e: Exception, verbose: int) -> None:
    """Handle ChromaDB errors with consistent formatting.

    Args:
        e: The exception to handle
        verbose: Verbosity level for error output

    Raises:
        click.Abort: Always raised to terminate the CLI command
    """
    if isinstance(e, ShardMarkdownError):
        console.print(f"[red]Error:[/red] {e.message}")
        if verbose > 0:
            console.print(f"[dim]Error code: {e.error_code}[/dim]")
    elif isinstance(e, ConnectionError | RuntimeError | ValueError):
        console.print("[red]Unexpected error:[/red] %s", str(e))
        if verbose > 1:
            # Only print exception if we're in an exception context
            exc_type, exc_value, traceback = sys.exc_info()
            if exc_type is not None and exc_value is not None and traceback is not None:
                console.print_exception()
    raise click.Abort() from e


def get_connected_chromadb_client(config: Any) -> Any:
    """Get connected ChromaDB client or raise exception.

    Args:
        config: Configuration object with chromadb settings

    Returns:
        Connected ChromaDB client

    Raises:
        click.ClickException: If connection fails
    """
    chroma_client = create_chromadb_client(config.chromadb)
    if not chroma_client.connect():
        raise click.ClickException("Failed to connect to ChromaDB")
    return chroma_client
