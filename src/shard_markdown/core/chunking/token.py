"""Token-based chunking strategy."""

import re

from ...config.settings import Settings
from ..models import DocumentChunk, MarkdownAST
from .base import BaseChunker


class TokenChunker(BaseChunker):
    """Chunk documents based on token count."""

    def __init__(self, settings: Settings) -> None:
        """Initialize token chunker.

        Args:
            settings: Configuration settings
        """
        super().__init__(settings)
        # Rough approximation: 1 token ≈ 4 characters (for English text)
        self.chars_per_token = 4

    def chunk_document(self, ast: MarkdownAST) -> list[DocumentChunk]:
        """Chunk document based on token count.

        Args:
            ast: Parsed markdown AST

        Returns:
            List of document chunks
        """
        content = ast.content
        if not content:
            return []

        chunks = []
        current_pos = 0
        overlap_content = ""

        while current_pos < len(content):
            # Calculate chunk size in characters based on token limit
            chunk_size_chars = self.settings.chunk_size * self.chars_per_token

            # Include overlap from previous chunk
            chunk_start = max(0, current_pos - len(overlap_content))
            chunk_content = (
                overlap_content + content[current_pos : current_pos + chunk_size_chars]
            )

            if not chunk_content.strip():
                break

            # Try to break at word boundary
            if current_pos + chunk_size_chars < len(content):
                # Look for last space before limit
                last_space = chunk_content.rfind(" ")
                if last_space > len(overlap_content):
                    chunk_content = chunk_content[:last_space]

            chunk_end = chunk_start + len(chunk_content) - len(overlap_content)

            chunks.append(
                self._create_chunk(
                    content=chunk_content,
                    start=chunk_start,
                    end=chunk_end,
                    metadata={"chunk_type": "token"},
                )
            )

            # Prepare overlap for next chunk
            overlap_content = self._get_overlap_content(chunk_content)
            current_pos = chunk_end

        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Simple estimation: split on whitespace and punctuation
        # This is a rough approximation
        words = re.findall(r"\b\w+\b|\S", text)
        return len(words)
