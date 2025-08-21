"""Simple configuration loading with clear precedence."""

import os
from pathlib import Path
from typing import Any

import yaml

from .settings import Settings


def load_config(config_file: Path | None = None) -> Settings:
    """Load configuration with simple precedence: Env > Local > Global.

    Args:
        config_file: Optional path to configuration file

    Returns:
        Loaded and validated Settings instance

    Raises:
        ValueError: If configuration is invalid
        FileNotFoundError: If explicit config path doesn't exist
    """
    config_data: dict[str, Any] = {}

    # 1. Load global config if exists (~/.shard-md/config.yaml)
    global_config = Path.home() / ".shard-md" / "config.yaml"
    if global_config.exists():
        with open(global_config) as f:
            config_data.update(yaml.safe_load(f) or {})

    # 2. Load local or specified config (overwrites global)
    if config_file:
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        with open(config_file) as f:
            config_data.update(yaml.safe_load(f) or {})
    elif (local_config := Path.cwd() / "shard-md.yaml").exists():
        with open(local_config) as f:
            config_data.update(yaml.safe_load(f) or {})

    # 3. Apply environment variables (highest precedence)
    prefix = "SHARD_MD_"
    for key, value in os.environ.items():
        if key.startswith(prefix):
            config_key = key[len(prefix) :].lower()
            parsed_value: Any
            if value.lower() in ("true", "false"):
                parsed_value = value.lower() == "true"
            elif value.isdigit():
                parsed_value = int(value)
            else:
                parsed_value = value
            config_data[config_key] = parsed_value

    return Settings(**config_data)


def save_config(config: Settings, config_path: Path) -> None:
    """Save configuration to YAML file.

    Args:
        config: Configuration to save
        config_path: Path where to save configuration
    """
    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dictionary with mode='json' to properly serialize enums
    config_dict = config.model_dump(mode="json")

    # Write to YAML file
    with open(config_path, "w") as f:
        yaml.dump(config_dict, f, default_flow_style=False, indent=2)


def create_default_config(config_path: Path, force: bool = False) -> None:
    """Create default configuration file.

    Args:
        config_path: Path where to create configuration
        force: Whether to overwrite existing file

    Raises:
        FileExistsError: If file exists and force is False
    """
    if config_path.exists() and not force:
        raise FileExistsError(f"Configuration file already exists: {config_path}")

    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Create default configuration
    default_config = Settings()
    save_config(default_config, config_path)
