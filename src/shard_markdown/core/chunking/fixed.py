"""Fixed-size chunking with character or token limits."""

from ...utils.logging import get_logger
from ..models import DocumentChunk, MarkdownAST
from .base import BaseChunker


logger = get_logger(__name__)


class FixedSizeChunker(BaseChunker):
    """Simple chunker that creates fixed-size chunks."""

    def chunk_document(self, ast: MarkdownAST) -> list[DocumentChunk]:
        """Chunk document into fixed-size pieces.

        Args:
            ast: Parsed markdown AST

        Returns:
            List of document chunks
        """
        if not ast.elements:
            return []

        # Convert AST back to text
        full_text = self._ast_to_text(ast)

        if not full_text.strip():
            return []

        chunks = []
        start = 0

        while start < len(full_text):
            # Calculate end position
            end = min(start + self.settings.chunk_size, len(full_text))

            # Try to find a good break point (word boundary)
            if end < len(full_text) and self.settings.chunk_respect_boundaries:
                # Look backwards for word boundary
                for i in range(
                    end, max(start + self.settings.chunk_size // 2, start), -1
                ):
                    if full_text[i] in " \n\t.!?":
                        end = i + 1
                        break

            # Extract chunk content
            chunk_content = full_text[start:end]

            if chunk_content.strip():
                chunk = self._create_chunk(
                    chunk_content, start, end, {"chunk_method": "fixed_size"}
                )
                chunks.append(chunk)

            # Move start position with overlap
            if start + self.settings.chunk_size >= len(full_text):
                break

            start = end - self.settings.chunk_overlap

            # Ensure we make progress
            if chunks and start <= chunks[-1].start_position:
                start = chunks[-1].end_position

        logger.info("Created %s chunks using fixed-size method", len(chunks))
        return chunks

    def _ast_to_text(self, ast: MarkdownAST) -> str:
        """Convert AST back to plain text.

        Args:
            ast: Markdown AST to convert

        Returns:
            Plain text representation
        """
        text_parts = []

        for element in ast.elements:
            if element.type == "header":
                level_prefix = "#" * (element.level or 1)
                text_parts.append(f"{level_prefix} {element.text}")
            elif element.type == "paragraph":
                text_parts.append(element.text)
            elif element.type == "code_block":
                lang = element.language or ""
                text_parts.append(f"```{lang}\n{element.text}\n```")
            elif element.type == "list":
                if element.items:
                    items = "\n".join(f"- {item}" for item in element.items)
                    text_parts.append(items)
                else:
                    text_parts.append(element.text)
            else:
                text_parts.append(element.text)

        return "\n\n".join(text_parts)

    def get_chunker_info(self) -> dict:
        """Get information about the fixed-size chunker configuration.

        Returns:
            Dictionary containing chunker configuration details
        """
        logger.debug("Retrieving fixed-size chunker configuration info")
        return {
            "chunker_type": "fixed_size",
            "chunk_size": self.settings.chunk_size,
            "overlap": self.settings.chunk_overlap,
            "respect_boundaries": self.settings.chunk_respect_boundaries,
        }
