"""Sentence-based chunking strategy."""

import re

from ..models import DocumentChunk, MarkdownAST
from .base import BaseChunker


class SentenceChunker(BaseChunker):
    """Chunk documents by sentences."""

    def chunk_document(self, ast: MarkdownAST) -> list[DocumentChunk]:
        """Chunk document by sentences.

        Args:
            ast: Parsed markdown AST

        Returns:
            List of document chunks
        """
        content = ast.content
        if not content:
            return []

        # Split into sentences
        sentences = self._split_sentences(content)
        if not sentences:
            return []

        chunks = []
        current_chunk: list[str] = []
        current_size = 0
        chunk_start = 0

        for sentence in sentences:
            sentence_size = len(sentence)

            # Check if adding this sentence would exceed chunk size
            if (
                current_size + sentence_size > self.settings.chunk_size
                and current_chunk
            ):
                # Create chunk from accumulated sentences
                chunk_content = " ".join(current_chunk)
                chunk_end = chunk_start + len(chunk_content)

                chunks.append(
                    self._create_chunk(
                        content=chunk_content,
                        start=chunk_start,
                        end=chunk_end,
                        metadata={"chunk_type": "sentence"},
                    )
                )

                # Start new chunk with overlap
                if self.settings.chunk_overlap > 0:
                    # Include last few sentences as overlap
                    overlap_sentences = self._get_overlap_sentences(current_chunk)
                    current_chunk = overlap_sentences + [sentence]
                    current_size = sum(len(s) for s in current_chunk)
                    chunk_start = chunk_end - sum(len(s) for s in overlap_sentences)
                else:
                    current_chunk = [sentence]
                    current_size = sentence_size
                    chunk_start = chunk_end
            else:
                current_chunk.append(sentence)
                current_size += sentence_size

        # Add remaining sentences as final chunk
        if current_chunk:
            chunk_content = " ".join(current_chunk)
            chunks.append(
                self._create_chunk(
                    content=chunk_content,
                    start=chunk_start,
                    end=chunk_start + len(chunk_content),
                    metadata={"chunk_type": "sentence"},
                )
            )

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Simple sentence splitting - can be improved with NLP libraries
        sentence_endings = r"[.!?]+[\s\n]+"
        sentences = re.split(sentence_endings, text)

        # Clean and filter sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _get_overlap_sentences(self, sentences: list[str]) -> list[str]:
        """Get sentences for overlap.

        Args:
            sentences: Current chunk sentences

        Returns:
            Sentences to use as overlap
        """
        if not sentences:
            return []

        # Calculate how many sentences to include in overlap
        overlap_size = 0
        overlap_sentences: list[str] = []

        # Work backwards from end of chunk
        for sentence in reversed(sentences):
            if overlap_size + len(sentence) <= self.settings.chunk_overlap:
                overlap_sentences.insert(0, sentence)
                overlap_size += len(sentence)
            else:
                break

        return overlap_sentences
