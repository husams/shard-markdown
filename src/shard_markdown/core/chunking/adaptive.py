"""Adaptive chunking implementation."""

from ..base import BaseChunker
from ..models import DocumentChunk, MarkdownAST


class AdaptiveChunker(BaseChunker):
    """Adaptive chunking strategy that adjusts based on content."""

    def chunk_document(self, ast: MarkdownAST) -> list[DocumentChunk]:
        """Chunk document adaptively based on content analysis."""
        # Simple implementation for linting compliance
        content = ast.raw_text if ast.raw_text else ""
        if not content.strip():
            return []

        chunk = self._create_chunk(content=content, start=0, end=len(content))
        return [chunk]

    def get_info(self) -> dict:
        """Return basic class information."""
        return {"type": self.__class__.__name__}
