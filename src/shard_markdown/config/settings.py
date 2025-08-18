"""Consolidated configuration schema, defaults, and loading logic using Pydantic."""

import ipaddress
import os
import re
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..utils import ensure_directory_exists


# Default configuration file locations (simplified from 5 to 3)
DEFAULT_CONFIG_LOCATIONS = [
    Path.home() / ".shard-md" / "config.yaml",  # Global config
    Path.cwd() / ".shard-md" / "config.yaml",  # Local config
    Path.cwd() / "shard-md.yaml",  # Project config
]

# Default YAML configuration template
DEFAULT_CONFIG_YAML = """# Shard Markdown Configuration
chromadb:
  host: localhost
  port: 8000
  ssl: false
  timeout: 30
  auth_token: null

chunking:
  default_size: 1000
  default_overlap: 200
  method: structure
  respect_boundaries: true
  max_tokens: null

processing:
  batch_size: 10
  recursive: false
  pattern: "*.md"
  include_frontmatter: true
  include_path_metadata: true

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file_path: null
  max_file_size: 10485760
  backup_count: 5

custom_metadata: {}
plugins: []
"""

# Environment variable mappings
ENV_VAR_MAPPINGS = {
    "CHROMA_HOST": "chromadb.host",
    "CHROMA_PORT": "chromadb.port",
    "CHROMA_SSL": "chromadb.ssl",
    "CHROMA_AUTH_TOKEN": "chromadb.auth_token",
    "SHARD_MD_CHUNK_SIZE": "chunking.default_size",
    "SHARD_MD_CHUNK_OVERLAP": "chunking.default_overlap",
    "SHARD_MD_BATCH_SIZE": "processing.batch_size",
    "SHARD_MD_LOG_LEVEL": "logging.level",
}


def set_nested_value(data: dict[str, Any], path: str, value: Any) -> None:
    """Set nested value in dictionary using dot notation.

    Args:
        data: Dictionary to modify
        path: Dot-separated path (e.g., "chromadb.host")
        value: Value to set
    """
    keys = path.split(".")
    current = data

    # Navigate to parent of target key
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    # Set the final value
    current[keys[-1]] = value


class ChunkingMethod(str, Enum):
    """Available chunking methods."""

    STRUCTURE = "structure"
    _FIXED = "fixed"
    _SEMANTIC = "semantic"


class ChromaDBConfig(BaseModel):
    """ChromaDB connection configuration."""

    host: str = Field(default="localhost", description="ChromaDB server host")
    port: int = Field(default=8000, ge=1, le=65535, description="ChromaDB server port")
    ssl: bool = Field(default=False, description="Use SSL connection")
    auth_token: str | None = Field(default=None, description="Authentication token")
    timeout: int = Field(default=30, ge=1, description="Connection timeout in seconds")

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate host is not empty and is a valid hostname or IP address."""
        if not v or not v.strip():
            raise ValueError("Host cannot be empty")

        host = v.strip()

        # Check if it's a valid IP address
        try:
            ipaddress.ip_address(host)
            return host
        except ValueError:
            pass

        # Check if it's localhost
        if host in ("localhost", "127.0.0.1", "::1"):
            return host

        # Check if it looks like an IP address but failed validation
        # This prevents invalid or incomplete IP addresses from passing
        # hostname validation
        ipv4_like_pattern = re.compile(r"^\d+(\.\d+)+$")
        if ipv4_like_pattern.match(host):
            raise ValueError(
                f"Invalid host: '{host}'. Must be a valid IP address or hostname."
            )

        # Validate as hostname (RFC 1123)
        hostname_regex = re.compile(
            r"^(?=.{1,253}$)"  # Total length check
            r"(?!-)[A-Za-z0-9-]{1,63}(?<!-)"  # Label regex
            r"(\.[A-Za-z0-9-]{1,63})*$"  # Additional labels
        )

        if not hostname_regex.match(host):
            raise ValueError(
                f"Invalid host: '{host}'. Must be a valid IP address or hostname."
            )

        return host


class ChunkingConfig(BaseModel):
    """Document chunking configuration."""

    default_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Default chunk size in characters",
    )
    default_overlap: int = Field(
        default=200,
        ge=0,
        le=1000,
        description="Default overlap between chunks",
    )
    method: ChunkingMethod = Field(
        default=ChunkingMethod.STRUCTURE, description="Default chunking method"
    )
    respect_boundaries: bool = Field(
        default=True, description="Respect markdown structure boundaries"
    )
    max_tokens: int | None = Field(
        default=None, ge=1, description="Maximum tokens per chunk"
    )

    @field_validator("default_overlap")
    @classmethod
    def validate_overlap(cls, v: int, info: Any) -> int:
        """Validate overlap is less than chunk size."""
        if info.data and "default_size" in info.data and v >= info.data["default_size"]:
            raise ValueError("Overlap must be less than chunk size")
        return v


class ProcessingConfig(BaseModel):
    """Document processing configuration."""

    batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of documents to process in batch",
    )
    recursive: bool = Field(
        default=False, description="Process directories recursively by default"
    )
    pattern: str = Field(
        default="*.md", description="Default file pattern for filtering"
    )
    include_frontmatter: bool = Field(
        default=True, description="Extract YAML frontmatter as metadata"
    )
    include_path_metadata: bool = Field(
        default=True, description="Include file path information"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Default logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    file_path: Path | None = Field(default=None, description="Log file path")
    max_file_size: int = Field(
        default=10485760,
        description="Maximum log file size in bytes",  # 10MB
    )
    backup_count: int = Field(
        default=5, description="Number of backup log files to keep"
    )


class AppConfig(BaseModel):
    """Main application configuration."""

    chromadb: ChromaDBConfig = Field(default_factory=ChromaDBConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Custom user settings
    custom_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata to add to all chunks",
    )
    plugins: list[str] = Field(
        default_factory=list, description="List of plugin modules to load"
    )

    model_config = ConfigDict()


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
    ensure_directory_exists(config_path.parent)

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
    ensure_directory_exists(config_path.parent)

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


def _apply_env_overrides(config_data: Any) -> dict[str, Any]:
    """Apply environment variable overrides to configuration.

    Environment variable values are passed directly to Pydantic models,
    which handle type conversion based on field definitions.

    Args:
        config_data: Base configuration data (should be dict, but may be
                    other types in edge cases on some platforms)

    Returns:
        Configuration with environment overrides applied
    """
    # Ensure config_data is always a dictionary to handle edge cases
    # where _load_config_file might return unexpected types on some platforms
    if not isinstance(config_data, dict):
        config_data = {}

    result = config_data.copy()

    for env_var, config_path in ENV_VAR_MAPPINGS.items():
        env_value = os.getenv(env_var)
        if env_value is not None:
            # Pass string values directly to Pydantic for proper type conversion
            set_nested_value(result, config_path, env_value)

    # result is guaranteed to be a dict[str, Any] at this point
    return result  # type: ignore[no-any-return]
