"""Paragraph-based chunking strategy."""

from ..models import DocumentChunk, MarkdownAST
from .base import BaseChunker


class ParagraphChunker(BaseChunker):
    """Chunk documents by paragraphs."""

    def chunk_document(self, ast: MarkdownAST) -> list[DocumentChunk]:
        """Chunk document by paragraphs.

        Args:
            ast: Parsed markdown AST

        Returns:
            List of document chunks
        """
        content = ast.content
        if not content:
            return []

        # Split into paragraphs (double newline separated)
        paragraphs = self._split_paragraphs(content)
        if not paragraphs:
            return []

        chunks = []
        current_chunk: list[str] = []
        current_size = 0
        chunk_start = 0

        for paragraph in paragraphs:
            para_size = len(paragraph)

            # Check if adding this paragraph would exceed chunk size
            if current_size + para_size > self.settings.chunk_size and current_chunk:
                # Create chunk from accumulated paragraphs
                chunk_content = "\n\n".join(current_chunk)
                chunk_end = chunk_start + len(chunk_content)

                chunks.append(
                    self._create_chunk(
                        content=chunk_content,
                        start=chunk_start,
                        end=chunk_end,
                        metadata={"chunk_type": "paragraph"},
                    )
                )

                # Start new chunk with overlap
                if self.settings.chunk_overlap > 0:
                    # Include last paragraph(s) as overlap
                    overlap_paras = self._get_overlap_paragraphs(current_chunk)
                    current_chunk = overlap_paras + [paragraph]
                    current_size = sum(len(p) for p in current_chunk) + len("\n\n") * (
                        len(current_chunk) - 1
                    )
                    chunk_start = (
                        chunk_end
                        - sum(len(p) for p in overlap_paras)
                        - len("\n\n") * len(overlap_paras)
                    )
                else:
                    current_chunk = [paragraph]
                    current_size = para_size
                    chunk_start = chunk_end
            else:
                current_chunk.append(paragraph)
                current_size += para_size + (len("\n\n") if current_chunk else 0)

        # Add remaining paragraphs as final chunk
        if current_chunk:
            chunk_content = "\n\n".join(current_chunk)
            chunks.append(
                self._create_chunk(
                    content=chunk_content,
                    start=chunk_start,
                    end=chunk_start + len(chunk_content),
                    metadata={"chunk_type": "paragraph"},
                )
            )

        return chunks

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs.

        Args:
            text: Text to split

        Returns:
            List of paragraphs
        """
        # Split on double newlines or more
        paragraphs = text.split("\n\n")

        # Clean and filter paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        # Further split on single newlines if they look like separate paragraphs
        final_paragraphs = []
        for para in paragraphs:
            if "\n" in para:
                # Check if lines are short (likely list items or code)
                lines = para.split("\n")
                avg_line_length = sum(len(line) for line in lines) / len(lines)

                # If lines are reasonably long, treat as single paragraph
                if avg_line_length > 40:
                    final_paragraphs.append(para)
                else:
                    # Treat as separate paragraphs
                    final_paragraphs.extend(
                        [line.strip() for line in lines if line.strip()]
                    )
            else:
                final_paragraphs.append(para)

        return final_paragraphs

    def _get_overlap_paragraphs(self, paragraphs: list[str]) -> list[str]:
        """Get paragraphs for overlap.

        Args:
            paragraphs: Current chunk paragraphs

        Returns:
            Paragraphs to use as overlap
        """
        if not paragraphs:
            return []

        # Calculate how many paragraphs to include in overlap
        overlap_size = 0
        overlap_paras: list[str] = []

        # Work backwards from end of chunk
        for para in reversed(paragraphs):
            if overlap_size + len(para) <= self.settings.chunk_overlap:
                overlap_paras.insert(0, para)
                overlap_size += len(para) + len("\n\n")
            else:
                # If even one paragraph is too large, include it partially
                if not overlap_paras and self.settings.chunk_overlap > 0:
                    overlap_paras = [para[-self.settings.chunk_overlap :]]
                break

        return overlap_paras
