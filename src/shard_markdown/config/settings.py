"""Configuration schema definitions using Pydantic."""

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from ..core.encoding import EncodingDetectorConfig
from ..core.validation import ValidationConfig


if TYPE_CHECKING:
    from ..core.models import ChunkingConfig as CoreChunkingConfig


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
        """Validate host is not empty."""
        if not v or not v.strip():
            raise ValueError("Host cannot be empty")
        return v.strip()


class ChunkingConfig(BaseModel):
    """Document chunking configuration."""

    default_size: int = Field(
        default=1000,
        ge=50,  # Reduced minimum for better flexibility
        le=50000,  # Increased maximum for large documents
        description="Default chunk size in characters",
    )
    default_overlap: int = Field(
        default=200,
        ge=0,
        le=5000,  # Increased maximum overlap
        description="Default overlap between chunks",
    )
    method: ChunkingMethod = Field(
        default=ChunkingMethod.STRUCTURE, description="Default chunking method"
    )
    respect_boundaries: bool = Field(
        default=True, description="Respect markdown structure boundaries"
    )
    max_tokens: int | None = Field(
        default=None, ge=1, le=100000, description="Maximum tokens per chunk"
    )

    @field_validator("default_overlap")
    @classmethod
    def validate_overlap(cls, v: int, info: Any) -> int:
        """Validate overlap is less than chunk size."""
        if info.data and "default_size" in info.data:
            default_size = info.data["default_size"]
            if v >= default_size:
                raise ValueError(
                    f"Overlap ({v}) must be less than chunk size ({default_size})"
                )
            # Warn if overlap is more than 50% of chunk size
            if v > default_size * 0.5:
                import warnings

                warnings.warn(
                    f"Large overlap ({v}) is more than 50% of chunk size "
                    f"({default_size}). This may cause excessive duplication.",
                    UserWarning,
                    stacklevel=2,
                )
        return v

    def to_core_config(self) -> "CoreChunkingConfig":
        """Convert to core ChunkingConfig model.

        Returns:
            CoreChunkingConfig instance with mapped fields
        """
        from ..core.models import ChunkingConfig as CoreChunkingConfig

        return CoreChunkingConfig(
            chunk_size=self.default_size,
            overlap=self.default_overlap,
            method=self.method.value,
            respect_boundaries=self.respect_boundaries,
            max_tokens=self.max_tokens,
        )


class ProcessingConfig(BaseModel):
    """Document processing configuration."""

    batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of documents to process in batch",
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
    # File handling configuration
    max_file_size: int = Field(
        default=10_000_000,  # 10MB default
        ge=1,
        description="Maximum file size in bytes",
    )
    skip_empty_files: bool = Field(
        default=True, description="Skip empty or whitespace-only files"
    )
    strict_validation: bool = Field(
        default=False, description="Use strict validation for file processing"
    )
    encoding: str = Field(default="utf-8", description="Default file encoding")
    encoding_fallback: str = Field(
        default="latin-1", description="Fallback encoding when default fails"
    )
    # Advanced encoding detection
    enable_encoding_detection: bool = Field(
        default=True, description="Enable advanced encoding detection"
    )
    encoding_detection: EncodingDetectorConfig = Field(
        default_factory=EncodingDetectorConfig,
        description="Advanced encoding detection configuration",
    )
    # Content validation configuration
    validation: ValidationConfig = Field(
        default_factory=ValidationConfig,
        description="Content validation configuration",
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

    class Config:
        """Pydantic configuration."""

        _env_prefix = "SHARD_MD_"
        _case_sensitive = False
