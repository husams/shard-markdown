"""Simplified configuration system with only used options."""

import os
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from ..utils import ensure_directory_exists


# Simplified default locations
DEFAULT_CONFIG_LOCATIONS = [
    Path.home() / ".shard-md" / "config.yaml",
    Path.cwd() / ".shard-md" / "config.yaml",
    Path.cwd() / "shard-md.yaml",
]

# Minimal default configuration
DEFAULT_CONFIG_YAML = """# Shard Markdown Configuration
chromadb:
  host: localhost
  port: 8000
  auth_token: null
  timeout: 30

chunking:
  default_size: 1000
  default_overlap: 200
  method: structure

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file_path: null
  max_file_size: 10485760
  backup_count: 5
"""

# Only used environment variables
ENV_VAR_MAPPINGS = {
    "CHROMA_HOST": "chromadb.host",
    "CHROMA_PORT": "chromadb.port",
    "CHROMA_AUTH_TOKEN": "chromadb.auth_token",
    "SHARD_MD_CHUNK_SIZE": "chunking.default_size",
    "SHARD_MD_CHUNK_OVERLAP": "chunking.default_overlap",
    "SHARD_MD_LOG_LEVEL": "logging.level",
}


def set_nested_value(data: dict[str, Any], path: str, value: Any) -> None:
    """Set nested value in dictionary using dot notation."""
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


class ChunkingMethod(str, Enum):
    """Available chunking methods."""

    STRUCTURE = "structure"


class ChromaDBConfig(BaseModel):
    """ChromaDB connection configuration."""

    host: str = Field(default="localhost")
    port: int = Field(default=8000, ge=1, le=65535)
    auth_token: str | None = Field(default=None)
    timeout: int = Field(default=30, ge=1)


class ChunkingConfig(BaseModel):
    """Document chunking configuration."""

    default_size: int = Field(default=1000, ge=100, le=10000)
    default_overlap: int = Field(default=200, ge=0, le=1000)
    method: ChunkingMethod = Field(default=ChunkingMethod.STRUCTURE)


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_path: Path | None = Field(default=None)
    max_file_size: int = Field(default=10485760)
    backup_count: int = Field(default=5)


class AppConfig(BaseModel):
    """Main application configuration."""

    chromadb: ChromaDBConfig = Field(default_factory=ChromaDBConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load configuration from file and environment variables."""
    load_dotenv()

    # Find config file
    config_file = None
    if config_path:
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        config_file = config_path
    else:
        for location in DEFAULT_CONFIG_LOCATIONS:
            if location.exists():
                config_file = location
                break

    # Load from file
    config_data: dict[str, Any] = {}
    if config_file:
        with open(config_file) as f:
            loaded_data = yaml.safe_load(f)
            config_data = loaded_data if isinstance(loaded_data, dict) else {}

    # Apply environment overrides

    for env_var, config_path_str in ENV_VAR_MAPPINGS.items():
        env_value = os.getenv(env_var)
        if env_value is not None:
            set_nested_value(config_data, config_path_str, env_value)

    return AppConfig(**config_data)


def save_config(config: AppConfig, config_path: Path) -> None:
    """Save configuration to YAML file."""
    ensure_directory_exists(config_path.parent)
    config_dict = config.model_dump(mode="json")
    with open(config_path, "w") as f:
        yaml.dump(config_dict, f, default_flow_style=False, indent=2)


def create_default_config(config_path: Path, force: bool = False) -> None:
    """Create default configuration file."""
    if config_path.exists() and not force:
        raise FileExistsError(f"Configuration file already exists: {config_path}")

    ensure_directory_exists(config_path.parent)
    with open(config_path, "w") as f:
        f.write(DEFAULT_CONFIG_YAML)
