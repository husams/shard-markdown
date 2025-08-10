"""Configuration loading and management."""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .defaults import DEFAULT_CONFIG_LOCATIONS, DEFAULT_CONFIG_YAML, ENV_VAR_MAPPINGS
from .settings import AppConfig
from .utils import set_nested_value


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load configuration from file, environment variables, and defaults.

    Args:
        config_path: Optional explicit path to configuration file

    Returns:
        Loaded and validated AppConfig instance

    Raises:
        ValueError: If configuration is invalid
        FileNotFoundError: If explicit config path doesn't exist
    """
    # Load environment variables from .env file if it exists
    load_dotenv()

    # Determine configuration file path
    config_file: Path | None
    if config_path:
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        config_file = config_path
    else:
        config_file = _find_config_file()

    # Load configuration data
    config_data = {}

    # Load from file if it exists
    if config_file and config_file.exists():
        config_data = _load_config_file(config_file)

    # Override with environment variables
    config_data = _apply_env_overrides(config_data)

    # Create and validate configuration
    try:
        return AppConfig(**config_data)
    except (TypeError, ValueError, KeyError) as e:
        raise ValueError(f"Invalid configuration: {e}") from e


def save_config(config: AppConfig, config_path: Path) -> None:
    """Save configuration to YAML file.

    Args:
        config: Configuration to save
        config_path: Path where to save configuration
    """
    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dictionary
    config_dict = config.model_dump()

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

    # Write default configuration
    with open(config_path, "w") as f:
        f.write(DEFAULT_CONFIG_YAML)


def _find_config_file() -> Path | None:
    """Find configuration file in default locations.

    Returns:
        Path to first found configuration file, or None
    """
    for location in DEFAULT_CONFIG_LOCATIONS:
        if location.exists():
            return location
    return None


def _load_config_file(config_path: Path) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary

    Raises:
        ValueError: If file format is invalid
    """
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return data
    except yaml.YAMLError as e:
        raise ValueError(
            f"Invalid YAML in configuration file {config_path}: {e}"
        ) from e
    except (OSError, UnicodeDecodeError) as e:
        raise ValueError(f"Error reading configuration file {config_path}: {e}") from e


def _apply_env_overrides(config_data: dict[str, Any]) -> dict[str, Any]:
    """Apply environment variable overrides to configuration.

    Args:
        config_data: Base configuration data

    Returns:
        Configuration with environment overrides applied
    """
    result = config_data.copy()

    for env_var, config_path in ENV_VAR_MAPPINGS.items():
        env_value = os.getenv(env_var)
        if env_value is not None:
            # Use string values directly to avoid corrupting IP addresses
            set_nested_value(result, config_path, env_value)

    return result