"""Base chunker interface."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ..models import ChunkingConfig, DocumentChunk, MarkdownAST


class BaseChunker(ABC):
    """Base class for document chunkers."""

    def __init__(self, config: ChunkingConfig) -> None:
        """Initialize chunker with configuration.

        Args:
            config: Chunking configuration
        """
        self.config = config

    @abstractmethod
    def chunk_document(self, ast: MarkdownAST) -> List[DocumentChunk]:
        """Chunk document into smaller pieces.

        Args:
            ast: Parsed markdown AST

        Returns:
            List of document chunks
        """
        pass

    def _create_chunk(
        self, content: str, start: int, end: int, metadata: Optional[Dict] = None
    ) -> DocumentChunk:
        """Create a document chunk with standard metadata.

        Args:
            content: Chunk content
            start: Start position in original document
            end: End position in original document
            metadata: Additional metadata

        Returns:
            DocumentChunk instance
        """
        chunk_metadata = {
            "chunk_method": self.config.method,
            "chunk_size_config": self.config.chunk_size,
            "overlap_config": self.config.overlap,
            **(metadata or {}),
        }

        return DocumentChunk(
            content=content.strip(),
            metadata=chunk_metadata,
            start_position=start,
            end_position=end,
        )

    def _get_overlap_content(self, content: str) -> str:
        """Get overlap content from end of current chunk.

        Args:
            content: Current chunk content

        Returns:
            Overlap content for next chunk
        """
        if len(content) <= self.config.overlap:
            return content

        # Try to find sentence boundary for natural overlap
        overlap_start = len(content) - self.config.overlap

        # Look for sentence endings
        for i in range(overlap_start, len(content)):
            if content[i] in ".!?":
                next_char_idx = i + 1
                if next_char_idx < len(content) and content[next_char_idx] in " \n":
                    return content[next_char_idx:].lstrip()

        # Fallback to character-based overlap
        return content[-self.config.overlap :]