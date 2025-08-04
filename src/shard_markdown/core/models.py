"""Data models for document processing."""

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class MarkdownElement(BaseModel):
    """Represents a single markdown element in the AST."""

    type: str = Field(description="Element type (header, paragraph, code_block, etc.)")
    text: str = Field(description="Text content of the element")
    level: int | None = Field(default=None, description="Header level (for headers)")
    language: str | None = Field(default=None, description="Language (for code blocks)")
    items: list[str] | None = Field(default=None, description="List items (for lists)")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class MarkdownAST(BaseModel):
    """Abstract Syntax Tree representation of a markdown document."""

    elements: list[MarkdownElement] = Field(description="List of markdown elements")
    frontmatter: dict[str, Any] = Field(
        default_factory=dict, description="YAML frontmatter"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )

    @property
    def headers(self) -> list[MarkdownElement]:
        """Get all header elements."""
        if not self.elements:
            return []
        return [elem for elem in self.elements if elem.type == "header"]

    @property
    def code_blocks(self) -> list[MarkdownElement]:
        """Get all code block elements."""
        if not self.elements:
            return []
        return [elem for elem in self.elements if elem.type == "code_block"]


class DocumentChunk(BaseModel):
    """Represents a chunk of processed document content."""

    id: str | None = Field(default=None, description="Unique chunk identifier")
    content: str = Field(description="Chunk text content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    start_position: int = Field(
        default=0, description="Start position in original document"
    )
    end_position: int = Field(
        default=0, description="End position in original document"
    )

    @property
    def size(self) -> int:
        """Get chunk size in characters."""
        return len(self.content)

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to chunk."""
        self.metadata[key] = value


class ProcessingResult(BaseModel):
    """Result of processing a single document."""

    file_path: Path = Field(description="Path to processed file")
    success: bool = Field(description="Whether processing succeeded")
    chunks_created: int = Field(default=0, description="Number of chunks created")
    processing_time: float = Field(
        default=0.0, description="Processing time in seconds"
    )
    collection_name: str | None = Field(
        default=None, description="Target collection name"
    )
    error: str | None = Field(default=None, description="Error message if failed")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Processing timestamp"
    )

    @property
    def chunks_per_second(self) -> float:
        """Calculate chunks processed per second."""
        if self.processing_time > 0:
            return self.chunks_created / self.processing_time
        return 0.0


class BatchResult(BaseModel):
    """Result of processing multiple documents in batch."""

    results: list[ProcessingResult] = Field(description="Individual processing results")
    total_files: int = Field(description="Total number of files processed")
    successful_files: int = Field(description="Number of successfully processed files")
    failed_files: int = Field(description="Number of failed files")
    total_chunks: int = Field(description="Total chunks created")
    total_processing_time: float = Field(description="Total processing time")
    collection_name: str = Field(description="Target collection name")

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_files > 0:
            return (self.successful_files / self.total_files) * 100
        return 0.0

    @property
    def average_chunks_per_file(self) -> float:
        """Calculate average chunks per file."""
        if self.successful_files > 0:
            return self.total_chunks / self.successful_files
        return 0.0

    @property
    def processing_speed(self) -> float:
        """Calculate processing speed in files per second."""
        if self.total_processing_time > 0:
            return self.total_files / self.total_processing_time
        return 0.0


class ChunkingConfig(BaseModel):
    """Configuration for document chunking."""

    chunk_size: int = Field(
        default=1000, description="Maximum chunk size in characters"
    )
    overlap: int = Field(default=200, description="Overlap between chunks")
    method: str = Field(default="structure", description="Chunking method")
    respect_boundaries: bool = Field(
        default=True, description="Respect structure boundaries"
    )
    max_tokens: int | None = Field(default=None, description="Maximum tokens per chunk")


class InsertResult(BaseModel):
    """Result of inserting chunks into ChromaDB."""

    success: bool = Field(description="Whether insertion succeeded")
    chunks_inserted: int = Field(default=0, description="Number of chunks inserted")
    processing_time: float = Field(default=0.0, description="Insertion time in seconds")
    error: str | None = Field(default=None, description="Error message if failed")
    collection_name: str = Field(description="Target collection name")

    @property
    def insertion_rate(self) -> float:
        """Calculate insertion rate in chunks per second."""
        if self.processing_time > 0:
            return self.chunks_inserted / self.processing_time
        return 0.0
