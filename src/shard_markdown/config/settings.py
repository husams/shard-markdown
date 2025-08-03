"""Configuration schema definitions using Pydantic."""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ChunkingMethod(str, Enum):
    """Available chunking methods."""

    STRUCTURE = "structure"
    _FIXED = "fixed"
    _SEMANTIC = "semantic"


class ChromaDBConfig(BaseModel):
    """ChromaDB connection configuration."""

    host: str = Field(default="localhost", description="ChromaDB server host")
    port: int = Field(default=8000,
        ge=1,
        le=65535,
        description="ChromaDB server port"
    )
    ssl: bool = Field(default=False, description="Use SSL connection")
    auth_token: Optional[str] = Field(default=None, description="Authentication token")
    timeout: int = Field(default=30,
        ge=1,
        description="Connection timeout in seconds"
    )

    @validator("host")
    def validate_host(cls, v: str) -> str:
        """Validate host is not empty."""
        if not v or not v.strip():
            raise ValueError("Host cannot be empty")
        return v.strip()


class ChunkingConfig(BaseModel):
    """Document chunking configuration."""

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
    max_tokens: Optional[int] = Field(
        default=None, ge=1, description="Maximum tokens per chunk"
    )

    @validator("default_overlap")
    def validate_overlap(cls, v: int, values: Dict[str, Any]) -> int:
        """Validate overlap is less than chunk size."""
        if "default_size" in values and v >= values["default_size"]:
            raise ValueError("Overlap must be less than chunk size")
        return v


class ProcessingConfig(BaseModel):
    """Document processing configuration."""

    batch_size: int = Field(
        default=10, ge=1, le=100, description="Number of documents to process in batch"
    )
    max_workers: int = Field(
        default=4, ge=1, le=16, description="Maximum worker threads"
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
    file_path: Optional[Path] = Field(default=None, description="Log file path")
    max_file_size: int = Field(
        default=10485760, description="Maximum log file size in bytes"  # 10MB
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
    custom_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata to add to all chunks"
    )
    plugins: List[str] = Field(
        default_factory=list, description="List of plugin modules to load"
    )

    class Config:
        """Pydantic configuration."""

        _env_prefix = "SHARD_MD_"
        _case_sensitive = False
