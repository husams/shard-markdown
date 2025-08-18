"""Simplified configuration with flat structure using Pydantic."""

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


# Default configuration file locations (simplified to 3)
DEFAULT_CONFIG_LOCATIONS = [
    Path.home() / ".shard-md" / "config.yaml",  # Global config
    Path.cwd() / "shard-md.yaml",  # Project config
]

# Default YAML configuration template (simplified flat structure)
DEFAULT_CONFIG_YAML = """# Shard Markdown Configuration (Simplified)
# ChromaDB connection
chroma_host: localhost
chroma_port: 8000
chroma_ssl: false
chroma_timeout: 30
chroma_auth_token: null

# Document chunking
chunk_size: 1000
chunk_overlap: 200
chunking_method: structure
respect_boundaries: true
max_tokens: null

# Processing options
batch_size: 10
recursive: false
pattern: "*.md"
include_frontmatter: true
include_path_metadata: true

# Logging
log_level: INFO
log_format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
log_file: null
max_log_file_size: 10485760
log_backup_count: 5

# Custom settings
custom_metadata: {}
plugins: []
"""

# Environment variable mappings (updated for flat structure)
ENV_VAR_MAPPINGS = {
    "CHROMA_HOST": "chroma_host",
    "CHROMA_PORT": "chroma_port",
    "CHROMA_SSL": "chroma_ssl",
    "CHROMA_AUTH_TOKEN": "chroma_auth_token",
    "SHARD_MD_CHUNK_SIZE": "chunk_size",
    "SHARD_MD_CHUNK_OVERLAP": "chunk_overlap",
    "SHARD_MD_BATCH_SIZE": "batch_size",
    "SHARD_MD_LOG_LEVEL": "log_level",
}

# Backward compatibility mapping for nested config files
NESTED_CONFIG_MAPPINGS = {
    "chromadb.host": "chroma_host",
    "chromadb.port": "chroma_port",
    "chromadb.ssl": "chroma_ssl",
    "chromadb.timeout": "chroma_timeout",
    "chromadb.auth_token": "chroma_auth_token",
    "chunking.default_size": "chunk_size",
    "chunking.default_overlap": "chunk_overlap",
    "chunking.method": "chunking_method",
    "chunking.respect_boundaries": "respect_boundaries",
    "chunking.max_tokens": "max_tokens",
    "processing.batch_size": "batch_size",
    "processing.recursive": "recursive",
    "processing.pattern": "pattern",
    "processing.include_frontmatter": "include_frontmatter",
    "processing.include_path_metadata": "include_path_metadata",
    "logging.level": "log_level",
    "logging.format": "log_format",
    "logging.file_path": "log_file",
    "logging.max_file_size": "max_log_file_size",
    "logging.backup_count": "log_backup_count",
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


class Settings(BaseModel):
    """Simplified flat configuration for shard-markdown.

    All configuration options are now in a single flat structure for simplicity.
    This replaces the previous nested configuration model.
    """

    # ChromaDB connection settings
    chroma_host: str = Field(default="localhost", description="ChromaDB server host")
    chroma_port: int = Field(
        default=8000, ge=1, le=65535, description="ChromaDB server port"
    )
    chroma_ssl: bool = Field(default=False, description="Use SSL connection")
    chroma_auth_token: str | None = Field(
        default=None, description="Authentication token"
    )
    chroma_timeout: int = Field(
        default=30, ge=1, description="Connection timeout in seconds"
    )

    # Document chunking settings
    chunk_size: int = Field(
        default=1000, ge=100, le=10000, description="Default chunk size in characters"
    )
    chunk_overlap: int = Field(
        default=200, ge=0, le=1000, description="Default overlap between chunks"
    )
    chunking_method: ChunkingMethod = Field(
        default=ChunkingMethod.STRUCTURE, description="Default chunking method"
    )
    respect_boundaries: bool = Field(
        default=True, description="Respect markdown structure boundaries"
    )
    max_tokens: int | None = Field(
        default=None, ge=1, description="Maximum tokens per chunk"
    )

    # Processing settings
    batch_size: int = Field(
        default=10, ge=1, le=100, description="Number of documents to process in batch"
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

    # Logging settings
    log_level: str = Field(default="INFO", description="Default logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    log_file: Path | None = Field(default=None, description="Log file path")
    max_log_file_size: int = Field(
        default=10485760,  # 10MB
        description="Maximum log file size in bytes",
    )
    log_backup_count: int = Field(
        default=5, description="Number of backup log files to keep"
    )

    # Custom user settings (rarely used, kept for backward compatibility)
    custom_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata to add to all chunks"
    )
    plugins: list[str] = Field(
        default_factory=list, description="List of plugin modules to load"
    )

    model_config = ConfigDict()

    @field_validator("chroma_host")
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

    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap(cls, v: int, info: Any) -> int:
        """Validate overlap is less than chunk size."""
        if info.data and "chunk_size" in info.data and v >= info.data["chunk_size"]:
            raise ValueError("Overlap must be less than chunk size")
        return v


# Backward compatibility classes that provide old interface
class ChromaDBConfig(BaseModel):
    """Backward compatibility wrapper for ChromaDB configuration."""

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
    """Backward compatibility wrapper for chunking configuration."""

    default_size: int = Field(
        default=1000, ge=100, le=10000, description="Default chunk size in characters"
    )
    default_overlap: int = Field(
        default=200, ge=0, le=1000, description="Default overlap between chunks"
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
    """Backward compatibility wrapper for processing configuration."""

    batch_size: int = Field(
        default=10, ge=1, le=100, description="Number of documents to process in batch"
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
    """Backward compatibility wrapper for logging configuration."""

    level: str = Field(default="INFO", description="Default logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    file_path: Path | None = Field(default=None, description="Log file path")
    max_file_size: int = Field(
        default=10485760,  # 10MB
        description="Maximum log file size in bytes",
    )
    backup_count: int = Field(
        default=5, description="Number of backup log files to keep"
    )


class AppConfig(BaseModel):
    """Backward compatibility wrapper for the main application configuration."""

    chromadb: ChromaDBConfig = Field(default_factory=ChromaDBConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Custom user settings
    custom_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata to add to all chunks"
    )
    plugins: list[str] = Field(
        default_factory=list, description="List of plugin modules to load"
    )

    model_config = ConfigDict()


def load_config(config_path: Path | None = None) -> Settings:
    """Load configuration from file, environment variables, and defaults.

    Args:
        config_path: Optional explicit path to configuration file

    Returns:
        Loaded and validated Settings instance

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
        # Handle backward compatibility with nested config files
        config_data = _migrate_nested_config(config_data)

    # Override with environment variables
    config_data = _apply_env_overrides(config_data)

    # Create and validate configuration
    try:
        return Settings(**config_data)
    except (TypeError, ValueError, KeyError) as e:
        raise ValueError(f"Invalid configuration: {e}") from e


def save_config(config: Settings, config_path: Path) -> None:
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


def _migrate_nested_config(config_data: dict[str, Any]) -> dict[str, Any]:
    """Migrate nested configuration to flat structure for backward compatibility.

    Args:
        config_data: Configuration data potentially in nested format

    Returns:
        Configuration data in flat format
    """
    result = {}

    # Handle nested structure by flattening it
    def flatten_dict(d: dict[str, Any], prefix: str = "") -> None:
        for key, value in d.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                flatten_dict(value, full_key)
            else:
                # Map nested keys to flat keys
                if full_key in NESTED_CONFIG_MAPPINGS:
                    flat_key = NESTED_CONFIG_MAPPINGS[full_key]
                    result[flat_key] = value
                elif "." not in full_key:
                    # Direct flat key
                    result[full_key] = value

    flatten_dict(config_data)
    return result


def _apply_env_overrides(config_data: dict[str, Any]) -> dict[str, Any]:
    """Apply environment variable overrides to configuration.

    Args:
        config_data: Base configuration data

    Returns:
        Configuration with environment overrides applied
    """
    result = config_data.copy()

    for env_var, config_key in ENV_VAR_MAPPINGS.items():
        env_value = os.getenv(env_var)
        if env_value is not None:
            # Pass string values directly to Pydantic for proper type conversion
            result[config_key] = env_value

    return result
