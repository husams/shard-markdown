"""Config command for configuration management."""

import json
from typing import Any

import click
import yaml
from rich.table import Table

from ...config.settings import (
    DEFAULT_CONFIG_LOCATIONS,
    create_default_config,
    save_config,
    set_nested_value,
)
from ...utils.logging import get_logger
from ..utils import console


_logger = get_logger(__name__)


@click.group()
def config() -> None:
    """Manage shard-markdown configuration.

    This command group provides operations for viewing, editing, and managing
    the shard-markdown configuration file.
    """
    pass


@config.command()
@click.option(
    "--format",
    type=click.Choice(["yaml", "json", "table"]),
    default="yaml",
    help="Output format [default: yaml]",
)
@click.option("--section", help="Show specific configuration section only")
@click.pass_context
def show(ctx: click.Context, format: str, section: str) -> None:
    """Show current configuration.

    Examples:
      # Show full configuration
      shard-md config show

      # Show specific section
      shard-md config show --section chromadb

      # Show in JSON format
      shard-md config show --format json
    """
    config_obj = ctx.obj["config"]
    verbose = ctx.obj.get("verbose", 0)

    try:
        # Get configuration as dictionary with mode='json' to properly serialize enums
        config_dict = config_obj.model_dump(mode="json")

        # Filter to specific section if requested
        if section:
            if section not in config_dict:
                console.print(f"[red]Configuration section '{section}' not found[/red]")
                available_sections = list(config_dict.keys())
                console.print(f"Available sections: {', '.join(available_sections)}")
                return
            config_dict = {section: config_dict[section]}

        # Display based on format
        if format == "yaml":
            console.print(yaml.dump(config_dict, default_flow_style=False, indent=2))
        elif format == "json":
            console.print(json.dumps(config_dict, indent=2))
        elif format == "table":
            _display_config_table(config_dict)

    except (OSError, ValueError, RuntimeError) as e:
        console.print(f"[red]Error displaying configuration:[/red] {str(e)}")
        if verbose > 1:
            console.print_exception()
        raise click.Abort() from e


@config.command()
@click.argument("key")
@click.argument("value")
@click.option(
    "--global",
    "is_global",
    is_flag=True,
    help="Set global configuration (user-level)",
)
@click.option(
    "--local",
    "is_local",
    is_flag=True,
    help="Set local configuration (project-level)",
)
@click.pass_context
def set(
    ctx: click.Context, key: str, value: str, is_global: bool, is_local: bool
) -> None:  # noqa: C901
    """Set a configuration value.

    Key should be in dot notation (e.g., chromadb.host, chunking.default_size).

    Examples:
      # Set ChromaDB host
      shard-md config set chromadb.host localhost

      # Set default chunk size
      shard-md config set chunking.default_size 1500

      # Set global configuration
      shard-md config set chromadb.port 8001 --global
    """
    verbose = ctx.obj.get("verbose", 0)

    try:
        # Determine configuration file path
        config_path = None
        if is_global:
            config_path = DEFAULT_CONFIG_LOCATIONS[0]
        elif is_local:
            config_path = DEFAULT_CONFIG_LOCATIONS[1]
        else:
            # Use the first existing config file, or global if none exist
            for location in DEFAULT_CONFIG_LOCATIONS:
                if location.exists():
                    config_path = location
                    break
            if not config_path:
                config_path = DEFAULT_CONFIG_LOCATIONS[0]

        # Load current configuration
        current_config = ctx.obj["config"]
        config_dict = current_config.model_dump()

        # Pass string value directly to Pydantic for proper type conversion
        set_nested_value(config_dict, key, value)

        # Validate the new configuration
        from ...config.settings import AppConfig

        try:
            updated_config = AppConfig(**config_dict)
        except (ValueError, TypeError) as e:
            console.print(f"[red]Invalid configuration value:[/red] {str(e)}")
            return

        # Save the configuration
        save_config(updated_config, config_path)

        console.print(f"[green][OK] Set {key} = {value}[/green]")
        console.print(f"[dim]Saved to: {config_path}[/dim]")

    except (OSError, ValueError, RuntimeError) as e:
        console.print(f"[red]Error setting configuration:[/red] {str(e)}")
        if verbose > 1:
            console.print_exception()
        raise click.Abort() from e


@config.command()
@click.option(
    "--global",
    "is_global",
    is_flag=True,
    help="Initialize global configuration",
)
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
@click.option("--template", help="Use configuration template (future feature)")
@click.pass_context
def init(ctx: click.Context, is_global: bool, force: bool, template: str) -> None:
    """Initialize configuration file with defaults.

    Examples:
      # Initialize local configuration
      shard-md config init

      # Initialize global configuration
      shard-md config init --global

      # Force overwrite existing configuration
      shard-md config init --force
    """
    verbose = ctx.obj.get("verbose", 0)

    try:
        # Determine configuration file path
        if is_global:
            config_path = DEFAULT_CONFIG_LOCATIONS[0]
        else:
            config_path = DEFAULT_CONFIG_LOCATIONS[1]

        # Check if file already exists
        if config_path.exists() and not force:
            console.print(
                f"[yellow]Configuration file already exists: {config_path}[/yellow]"
            )
            console.print("Use --force to overwrite, or edit the existing file.")
            return

        # Create default configuration
        create_default_config(config_path, force=force)

        console.print(
            f"[green][OK] Initialized configuration file: {config_path}[/green]"
        )
        console.print(
            "You can now edit the file or use 'shard-md config set' to modify values."
        )

    except (OSError, ValueError, RuntimeError) as e:
        console.print(f"[red]Error initializing configuration:[/red] {str(e)}")
        if verbose > 1:
            console.print_exception()
        raise click.Abort() from e


@config.command()
@click.pass_context
def path(ctx: click.Context) -> None:
    """Show configuration file locations.

    This shows the order of configuration file locations that shard-md checks.
    """
    console.print(
        "[blue]Configuration file locations (in order of precedence):[/blue]\n"
    )

    for i, location in enumerate(DEFAULT_CONFIG_LOCATIONS, 1):
        exists = "YES" if location.exists() else "NO"
        status = (
            "[green]exists[/green]" if location.exists() else "[dim]not found[/dim]"
        )
        console.print(f"  {i}. {exists} {location} ({status})")

    console.print("\n[dim]The first existing file will be used.[/dim]")
    console.print(
        "[dim]Use 'shard-md config init' to create a new configuration file.[/dim]"
    )


def _display_config_table(config_dict: dict[str, Any]) -> None:
    """Display configuration in table format."""

    def flatten_dict(
        d: dict[str, Any], parent_key: str = "", sep: str = "."
    ) -> dict[str, Any]:
        """Flatten nested dictionary with dot notation keys."""
        items: list[tuple[str, Any]] = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    flat_config = flatten_dict(config_dict)

    # Group by section
    sections: dict[str, list[tuple[str, Any]]] = {}
    for key, value in flat_config.items():
        section = key.split(".")[0]
        if section not in sections:
            sections[section] = []
        sections[section].append((key, value))

    # Display each section
    for section_name, items in sections.items():
        table = Table(title=f"Configuration: {section_name}")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")

        items_list: list[tuple[str, Any]] = items
        for key, value in items_list:
            # Remove section prefix from key for display
            display_key = ".".join(key.split(".")[1:]) if "." in key else key
            table.add_row(display_key, str(value))

        console.print(table)
        console.print()
