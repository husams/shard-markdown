"""Main chunking engine that selects appropriate strategy."""

from ...config.settings import Settings
from ...utils.errors import ProcessingError
from ...utils.logging import get_logger
from ..models import DocumentChunk, MarkdownAST
from .fixed import FixedSizeChunker
from .paragraph import ParagraphChunker
from .section import SectionChunker
from .semantic import SemanticChunker
from .sentence import SentenceChunker
from .structure import StructureAwareChunker
from .token import TokenChunker


logger = get_logger(__name__)


class ChunkingEngine:
    """Main chunking engine with strategy selection."""

    def __init__(self, settings: Settings):
        """Initialize chunking engine with configuration.

        Args:
            settings: Configuration settings
        """
        self.settings = settings
        self.strategies = {
            "structure": StructureAwareChunker(settings),
            "fixed": FixedSizeChunker(settings),
            "token": TokenChunker(settings),
            "sentence": SentenceChunker(settings),
            "paragraph": ParagraphChunker(settings),
            "section": SectionChunker(settings),
            "semantic": SemanticChunker(settings),
        }

    def chunk_document(self, ast: MarkdownAST) -> list[DocumentChunk]:
        """Chunk document using configured strategy.

        Args:
            ast: Parsed markdown AST

        Returns:
            List of document chunks

        Raises:
            ProcessingError: If chunking fails
        """
        if not ast.elements:
            logger.warning("No elements in AST to chunk")
            return []

        strategy_name = self.settings.chunk_method
        if strategy_name not in self.strategies:
            raise ProcessingError(
                f"Unknown chunking strategy: {strategy_name}",
                error_code=1310,
                context={
                    "strategy": strategy_name,
                    "available_strategies": list(self.strategies.keys()),
                },
            )

        try:
            chunker = self.strategies[strategy_name]
            chunks = chunker.chunk_document(ast)

            # Validate chunks
            self._validate_chunks(chunks)

            # Add chunk IDs and additional metadata
            for i, chunk in enumerate(chunks):
                chunk.id = f"chunk_{i:04d}"
                chunk.add_metadata("chunk_index", i)
                chunk.add_metadata("total_chunks", len(chunks))

            logger.info("Successfully chunked document into %s chunks", len(chunks))
            return chunks

        except (AttributeError, ValueError, TypeError) as e:
            if isinstance(e, ProcessingError):
                raise

            raise ProcessingError(
                f"Chunking failed with strategy '{strategy_name}': {str(e)}",
                error_code=1311,
                context={"strategy": strategy_name, "ast_elements": len(ast.elements)},
                cause=e,
            ) from e

    def _validate_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Validate generated chunks.

        Args:
            chunks: List of chunks to validate

        Raises:
            ProcessingError: If validation fails
        """
        if not chunks:
            return

        # Check for empty chunks
        empty_chunks = [
            i for i, chunk in enumerate(chunks) if not chunk.content.strip()
        ]
        if empty_chunks:
            raise ProcessingError(
                f"Generated empty chunks at positions: {empty_chunks}",
                error_code=1312,
                context={"empty_chunk_indices": empty_chunks},
            )

        # Check for oversized chunks (allow some tolerance)
        max_allowed_size = self.settings.chunk_size * 1.5
        oversized_chunks = [
            i for i, chunk in enumerate(chunks) if len(chunk.content) > max_allowed_size
        ]

        if oversized_chunks:
            raise ProcessingError(
                f"Generated chunks exceed size limits at positions: {oversized_chunks}",
                error_code=1313,
                context={
                    "oversized_chunk_indices": oversized_chunks,
                    "max_allowed_size": max_allowed_size,
                    "configured_size": self.settings.chunk_size,
                },
            )

        logger.debug("Validated %s chunks successfully", len(chunks))
