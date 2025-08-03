"""Main chunking engine that selects appropriate strategy."""

from typing import List

from ...utils.errors import ProcessingError
from ...utils.logging import get_logger
from ..models import ChunkingConfig, DocumentChunk, MarkdownAST
from .base import BaseChunker
from .fixed import FixedSizeChunker
from .structure import StructureAwareChunker

logger = get_logger(__name__)


class ChunkingEngine:
    """Main chunking engine with strategy selection."""

    def __init__(self, config: ChunkingConfig):
        """Initialize chunking engine with configuration.

        Args:
            config: Chunking configuration
        """
        self.config = config
        self.strategies = {
            "structure": StructureAwareChunker(config),
            "fixed": FixedSizeChunker(config),
        }

    def chunk_document(self, ast: MarkdownAST) -> List[DocumentChunk]:
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

        strategy_name = self.config.method
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

            logger.info(f"Successfully chunked document into {len(chunks)} chunks")
            return chunks

        except Exception as e:
            if isinstance(e, ProcessingError):
                raise

            raise ProcessingError(
                f"Chunking failed with strategy '{strategy_name}': {str(e)}",
                error_code=1311,
                context={"strategy": strategy_name, "ast_elements": len(ast.elements)},
                cause=e,
            )

    def _validate_chunks(self, chunks: List[DocumentChunk]) -> None:
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
        max_allowed_size = self.config.chunk_size * 1.5
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
                    "configured_size": self.config.chunk_size,
                },
            )

        logger.debug(f"Validated {len(chunks)} chunks successfully")
