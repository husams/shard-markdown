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

            # Never split code blocks
            if element.type == "code_block":
                # If adding this code block would exceed size, create current
                # chunk first
                if (
                    len(current_chunk) + len(element_text) > self.config.chunk_size
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
                len(current_chunk) + len(element_text) > self.config.chunk_size
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
        else:
            return f"{element.text}\n\n"

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
