"""Flat configuration with all defaults inline."""

import ipaddress
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
    """Single flat configuration class - no nesting."""

    # ChromaDB Configuration (prefixed with chroma_)
    chroma_host: str = Field(default="localhost", description="ChromaDB server host")
    chroma_port: int = Field(
        default=8000, ge=1, le=65535, description="ChromaDB server port"
    )
    chroma_ssl: bool = Field(default=False, description="Use SSL connection")
    chroma_timeout: int = Field(
        default=30, ge=1, description="Connection timeout in seconds"
    )
    chroma_auth_token: str | None = Field(
        default=None, description="Authentication token"
    )

    # Chunking Configuration (prefixed with chunk_)
    chunk_size: int = Field(
        default=1000, ge=100, le=10000, description="Default chunk size in characters"
    )
    chunk_overlap: int = Field(
        default=200, ge=0, le=1000, description="Default overlap between chunks"
    )
    chunk_method: str = Field(
        default="structure", description="Default chunking method"
    )
    chunk_respect_boundaries: bool = Field(
        default=True, description="Respect markdown structure boundaries"
    )
    chunk_max_tokens: int | None = Field(
        default=None, ge=1, description="Maximum tokens per chunk"
    )

    # Processing Configuration (prefixed with process_)
    process_batch_size: int = Field(
        default=10, ge=1, le=100, description="Number of documents to process in batch"
    )
    process_recursive: bool = Field(
        default=False, description="Process directories recursively by default"
    )
    process_pattern: str = Field(
        default="*.md", description="Default file pattern for filtering"
    )
    process_include_frontmatter: bool = Field(
        default=True, description="Extract YAML frontmatter as metadata"
    )
    process_include_path_metadata: bool = Field(
        default=True, description="Include file path information"
    )

    # Logging Configuration (prefixed with log_)
    log_level: str = Field(default="INFO", description="Default logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    log_file: Path | None = Field(default=None, description="Log file path")
    log_max_file_size: int = Field(
        default=10485760,
        description="Maximum log file size in bytes",  # 10MB
    )
    log_backup_count: int = Field(
        default=5, description="Number of backup log files to keep"
    )

    # Output Configuration
    output_format: str = Field(default="table", description="Default output format")

    # Custom user settings
    custom_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata to add to all chunks"
    )
    plugins: list[str] = Field(
        default_factory=list, description="List of plugin modules to load"
    )

    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap(cls, v: int, info: Any) -> int:
        """Ensure overlap < chunk_size."""
        if info.data and "chunk_size" in info.data and v >= info.data["chunk_size"]:
            raise ValueError("Overlap must be less than chunk size")
        return v

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
