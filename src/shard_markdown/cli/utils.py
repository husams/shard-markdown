"""Shared utilities for CLI commands."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.logging import RichHandler

from ..chromadb.factory import create_chromadb_client
from ..config import AppConfig, load_config
from ..utils.errors import ShardMarkdownError


# Shared console instance for all CLI commands
console = Console()


def load_app_config(config_path: Path | None = None) -> AppConfig:
    """Load application configuration.

    Args:
        config_path: Optional path to config file

    Returns:
        Loaded AppConfig instance
    """
    return load_config(config_path)


def setup_logging(
    config: AppConfig,
    log_level: str | None = None,
    log_file: str | None = None,
    verbose: bool = False,
) -> None:
    """Setup logging for CLI commands.

    Args:
        config: Application configuration
        log_level: Override log level
        log_file: Override log file
        verbose: Enable verbose logging
    """
    # Determine log level
    level = log_level or config.logging.level
    if verbose:
        level = "DEBUG"

    # Configure logging
    handlers: list[logging.Handler] = []

    # Rich console handler for pretty CLI output
    rich_handler = RichHandler(
        console=console,
        show_time=False,
        show_path=False,
    )
    rich_handler.setLevel(getattr(logging, level.upper()))
    handlers.append(rich_handler)

    # File handler if specified
    file_path = Path(log_file) if log_file else config.logging.file_path
    if file_path:
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=config.logging.max_file_size,
            backupCount=config.logging.backup_count,
        )
        file_handler.setFormatter(logging.Formatter(config.logging.format))
        file_handler.setLevel(getattr(logging, level.upper()))
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers,
        force=True,
    )


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
        console.print(f"[red]Unexpected error:[/red] {str(e)}")
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
