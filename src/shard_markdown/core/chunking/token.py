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
            # Use chunk_size directly as character count
            # (settings.chunk_size is already in characters, not tokens)
            chunk_size_chars = self.settings.chunk_size

            # Get chunk content without overlap considerations first
            chunk_content = content[current_pos : current_pos + chunk_size_chars]

            if not chunk_content.strip():
                break

            # Try to break at word boundary
            if current_pos + chunk_size_chars < len(content):
                # Look for last space before limit
                last_space = chunk_content.rfind(" ")
                if last_space > 0:
                    chunk_content = chunk_content[:last_space]

            # Calculate actual positions
            chunk_start = current_pos
            chunk_end = current_pos + len(chunk_content)

            # Add overlap from previous chunk if available
            if overlap_content:
                chunk_content = overlap_content + chunk_content
                chunk_start = current_pos - len(overlap_content)

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
        """Estimate token count for text using improved heuristics.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Improved estimation based on GPT tokenization patterns:
        # 1. Split on whitespace and punctuation
        # 2. Count contractions as 2 tokens (e.g., "don't" = "do" + "n't")
        # 3. Count numbers and special characters more accurately

        # Count basic words
        words = re.findall(r"\b\w+\b", text)
        token_count = len(words)

        # Add tokens for punctuation (each punctuation is typically a token)
        punctuation = re.findall(r"[^\w\s]", text)
        token_count += len(punctuation)

        # Adjust for contractions (add extra token for each)
        contractions = re.findall(r"\b\w+'\w+\b", text)
        token_count += len(contractions)

        # Adjust for numbers (multi-digit numbers often split)
        numbers = re.findall(r"\b\d{4,}\b", text)
        for num in numbers:
            # Long numbers typically split every 3-4 digits
            token_count += len(num) // 3

        # Adjust for code patterns (if present)
        code_patterns = re.findall(r"[A-Z][a-z]+|[a-z]+_[a-z]+|::|->|=>", text)
        token_count += (
            len(code_patterns) // 2
        )  # These often tokenize as multiple tokens

        return token_count
