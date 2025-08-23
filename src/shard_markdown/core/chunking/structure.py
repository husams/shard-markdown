"""Structure-aware chunking that respects markdown hierarchy."""

from ...utils.logging import get_logger
from ..models import DocumentChunk, MarkdownAST, MarkdownElement
from .base import BaseChunker


logger = get_logger(__name__)


class StructureAwareChunker(BaseChunker):
    """Intelligent chunking that respects markdown structure."""

    def chunk_document(self, ast: MarkdownAST) -> list[DocumentChunk]:
        """Chunk document while respecting structure boundaries.

        Args:
            ast: Parsed markdown AST

        Returns:
            List of document chunks
        """
        if not ast.elements:
            return []

        chunks = []
        current_chunk = ""
        current_start = 0
        current_context: list[str] = []

        for element in ast.elements:
            element_text = self._element_to_text(element)

            # For very large elements that exceed chunk size on their own,
            # we may need to split them
            if len(element_text) > self.settings.chunk_size * 1.2:
                # If we have content, save it first
                if current_chunk.strip():
                    chunk = self._create_chunk(
                        current_chunk,
                        current_start,
                        current_start + len(current_chunk),
                        {"structural_context": " > ".join(current_context)},
                    )
                    chunks.append(chunk)
                    current_start = chunk.end_position
                    current_chunk = ""

                # Split the large element into smaller chunks
                element_chunks = self._split_large_element(element_text)
                for i, elem_chunk in enumerate(element_chunks):
                    chunk = self._create_chunk(
                        elem_chunk,
                        current_start,
                        current_start + len(elem_chunk),
                        {
                            "structural_context": " > ".join(current_context),
                            "split_element": True,
                            "split_part": i + 1,
                            "split_total": len(element_chunks),
                        },
                    )
                    chunks.append(chunk)
                    current_start = chunk.end_position

                # Continue with empty current_chunk
                current_chunk = ""

            # Never split code blocks if they fit within tolerance
            elif element.type == "code_block":
                # If adding this code block would exceed size, create current
                # chunk first
                if (
                    len(current_chunk) + len(element_text) > self.settings.chunk_size
                    and current_chunk.strip()
                ):
                    chunk = self._create_chunk(
                        current_chunk,
                        current_start,
                        current_start + len(current_chunk),
                        {"structural_context": " > ".join(current_context)},
                    )
                    chunks.append(chunk)

                    # Start new chunk with overlap
                    overlap_content = self._get_overlap_content(current_chunk)
                    current_chunk = overlap_content
                    current_start = chunk.end_position - len(overlap_content)

                current_chunk += element_text

            # Check if adding this element exceeds chunk size
            elif (
                len(current_chunk) + len(element_text) > self.settings.chunk_size
                and current_chunk.strip()
            ):
                # Create chunk with current content
                chunk = self._create_chunk(
                    current_chunk,
                    current_start,
                    current_start + len(current_chunk),
                    {"structural_context": " > ".join(current_context)},
                )
                chunks.append(chunk)

                # Start new chunk with overlap
                overlap_content = self._get_overlap_content(current_chunk)
                current_chunk = overlap_content + element_text
                current_start = chunk.end_position - len(overlap_content)
            else:
                current_chunk += element_text

            # Update structural context for headers
            if element.type == "header":
                self._update_context(current_context, element)

        # Add final chunk if content remains
        if current_chunk.strip():
            chunk = self._create_chunk(
                current_chunk,
                current_start,
                current_start + len(current_chunk),
                {"structural_context": " > ".join(current_context)},
            )
            chunks.append(chunk)

        logger.info("Created %s chunks using structure-aware method", len(chunks))
        return chunks

    def _element_to_text(self, element: MarkdownElement) -> str:
        """Convert AST element to text representation.

        Args:
            element: MarkdownElement to convert

        Returns:
            Text representation of element
        """
        if element.type == "header":
            header_prefix = "#" * (element.level or 1)
            return f"{header_prefix} {element.text}\n\n"
        elif element.type == "paragraph":
            return f"{element.text}\n\n"
        elif element.type == "code_block":
            lang = element.language or ""
            return f"```{lang}\n{element.text}\n```\n\n"
        elif element.type == "list":
            if element.items:
                items = "\n".join(f"- {item}" for item in element.items)
                return f"{items}\n\n"
            else:
                return f"{element.text}\n\n"
        elif element.type == "list_item":
            return f"- {element.text}\n"
        else:
            return f"{element.text}\n\n"

    def _split_large_element(self, text: str) -> list[str]:
        """Split a large element into smaller chunks.

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        chunks = []
        chunk_size = self.settings.chunk_size
        overlap_size = self.settings.chunk_overlap

        # Handle empty text
        if not text or not text.strip():
            return []

        # Split by sentences or paragraphs if possible
        lines = text.split("\n")
        current_chunk = ""

        for line in lines:
            # Calculate if adding this line would exceed chunk size
            line_length = len(line) + (1 if current_chunk else 0)  # +1 for newline

            if len(current_chunk) + line_length <= chunk_size:
                if current_chunk:
                    current_chunk += "\n"
                current_chunk += line
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    # Add overlap from end of previous chunk
                    if overlap_size > 0 and len(current_chunk) > overlap_size:
                        # Get last complete sentences/words for overlap
                        overlap_text = self._get_semantic_overlap(
                            current_chunk, overlap_size
                        )
                        current_chunk = (
                            overlap_text + "\n" + line if overlap_text else line
                        )
                    else:
                        current_chunk = line
                else:
                    # Single line too long, split intelligently
                    if len(line) > chunk_size:
                        # Try to split at sentence boundaries first
                        line_chunks = self._split_long_line(
                            line, chunk_size, overlap_size
                        )
                        chunks.extend(line_chunks[:-1])  # Add all but last
                        current_chunk = line_chunks[-1] if line_chunks else ""
                    else:
                        current_chunk = line

        if current_chunk and current_chunk.strip():
            chunks.append(current_chunk)

        return chunks

    def _get_semantic_overlap(self, text: str, target_size: int) -> str:
        """Get semantic overlap content, preferring complete sentences.

        Args:
            text: Text to extract overlap from
            target_size: Target overlap size

        Returns:
            Overlap text
        """
        if len(text) <= target_size:
            return text

        # Try to find last sentence boundary
        overlap_text = text[-target_size:]

        # Look for sentence boundary
        for delimiter in [". ", "! ", "? ", "\n"]:
            idx = overlap_text.find(delimiter)
            if idx != -1:
                return overlap_text[idx + len(delimiter) :]

        # Fall back to word boundary
        space_idx = overlap_text.find(" ")
        if space_idx != -1:
            return overlap_text[space_idx + 1 :]

        return overlap_text

    def _split_long_line(
        self, line: str, chunk_size: int, overlap_size: int
    ) -> list[str]:
        """Split a long line intelligently at sentence or word boundaries.

        Args:
            line: Line to split
            chunk_size: Maximum chunk size
            overlap_size: Overlap size between chunks

        Returns:
            List of line chunks
        """
        chunks = []

        # Try to split by sentences first
        sentence_delimiters = [". ", "! ", "? ", "; "]

        while len(line) > chunk_size:
            # Find best split point
            split_point = chunk_size

            # Look for sentence boundary
            for delimiter in sentence_delimiters:
                idx = line[:chunk_size].rfind(delimiter)
                if idx != -1:
                    split_point = idx + len(delimiter)
                    break
            else:
                # No sentence boundary, try word boundary
                space_idx = line[:chunk_size].rfind(" ")
                if space_idx != -1:
                    split_point = space_idx

            chunks.append(line[:split_point])

            # Add overlap for next chunk
            if overlap_size > 0 and split_point > overlap_size:
                overlap_start = max(0, split_point - overlap_size)
                # Try to start overlap at word boundary
                space_idx = line[overlap_start:split_point].find(" ")
                if space_idx != -1:
                    overlap_start = overlap_start + space_idx + 1
                line = line[overlap_start:]
            else:
                line = line[split_point:].lstrip()

        if line:
            chunks.append(line)

        return chunks

    def _update_context(
        self, context: list[str], header_element: MarkdownElement
    ) -> None:
        """Update hierarchical context based on header level.

        Args:
            context: Current context list (modified in place)
            header_element: Header element to add to context
        """
        level = header_element.level or 1
        header_text = header_element.text

        # Truncate context to appropriate level
        context[:] = context[: level - 1]

        # Add current header
        if len(context) >= level:
            context[level - 1] = header_text
        else:
            # Extend context with empty strings if needed
            context.extend([""] * (level - len(context) - 1))
            context.append(header_text)
