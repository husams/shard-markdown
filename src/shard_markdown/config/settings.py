"""Configuration schema definitions using Pydantic."""

import ipaddress
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChunkingMethod(str, Enum):
    """Available chunking methods."""

    STRUCTURE = "structure"
    _FIXED = "fixed"
    _SEMANTIC = "semantic"


def set_nested_value(data: dict[str, Any], path: str, value: Any) -> None:
    """Set nested value in dictionary using dot notation.

    Args:
        data: Dictionary to modify
        path: Dot-separated path (e.g., "chroma_host")
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


# Default configuration file locations - Simplified to 3 locations as per issue #167
DEFAULT_CONFIG_LOCATIONS = [
    Path.home() / ".shard-md" / "config.yaml",  # Global user config
    Path.cwd() / "shard-md.yaml",  # Single local config (no .shard-md/ directory)
]

# Default YAML configuration template - Simplified flat structure
DEFAULT_CONFIG_YAML = """# Shard Markdown Configuration
chroma_host: localhost
chroma_port: 8000
chunk_size: 1000
overlap: 100
log_level: INFO
output_format: table
"""

# Environment variable mappings - Updated for flat structure
ENV_VAR_MAPPINGS = {
    "CHROMA_HOST": "chroma_host",
    "CHROMA_PORT": "chroma_port",
    "SHARD_MD_CHUNK_SIZE": "chunk_size",
    "SHARD_MD_CHUNK_OVERLAP": "overlap",
    "SHARD_MD_LOG_LEVEL": "log_level",
    "SHARD_MD_OUTPUT_FORMAT": "output_format",
}


class Settings(BaseModel):
    """Simplified, flat configuration for shard-markdown."""

    # ChromaDB - Essential connection settings only
    chroma_host: str = Field(default="localhost", description="ChromaDB server host")
    chroma_port: int = Field(
        default=8000, ge=1, le=65535, description="ChromaDB server port"
    )

    # Chunking - Essential options only
    chunk_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Default chunk size in characters",
    )
    overlap: int = Field(
        default=100,
        ge=0,
        le=1000,
        description="Overlap between chunks in characters",
    )

    # Logging - Simplified to essentials
    log_level: str = Field(default="INFO", description="Logging level")

    # CLI - Essential output option only
    output_format: str = Field(default="table", description="Output format for CLI")

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

    @field_validator("overlap")
    @classmethod
    def validate_overlap(cls, v: int, info: Any) -> int:
        """Validate overlap is less than chunk size."""
        if info.data and "chunk_size" in info.data and v >= info.data["chunk_size"]:
            raise ValueError("Overlap must be less than chunk size")
        return v

    model_config = ConfigDict()

    def get_chunking_params(self) -> "ChunkingParams":
        """Get chunking parameters from settings.

        Returns:
            ChunkingParams object for use with chunking engine
        """
        return ChunkingParams(
            chunk_size=self.chunk_size,
            overlap=self.overlap,
            method="structure",  # Default method
            respect_boundaries=True,
            max_tokens=None,
        )

    def get_chromadb_params(self) -> "ChromaDBParams":
        """Get ChromaDB parameters from settings.

        Returns:
            ChromaDBParams object for use with ChromaDB client
        """
        return ChromaDBParams(
            host=self.chroma_host,
            port=self.chroma_port,
            ssl=False,  # Default for now
            auth_token=None,  # Default for now
            timeout=30,  # Default timeout
        )


@dataclass
class ChunkingParams:
    """Simple data container for chunking parameters."""

    chunk_size: int
    overlap: int
    method: str = "structure"
    respect_boundaries: bool = True
    max_tokens: int | None = None


@dataclass
class ChromaDBParams:
    """Simple data container for ChromaDB parameters."""

    host: str
    port: int
    ssl: bool = False
    auth_token: str | None = None
    timeout: int = 30
