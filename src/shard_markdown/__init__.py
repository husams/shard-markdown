"""Shard Markdown - Intelligent document chunking for ChromaDB collections."""

__version__ = "0.1.0"
__author__ = "Shard Markdown Contributors"
__email__ = "shard-md@example.com"
__description__ = (
    "Intelligent markdown document chunking for ChromaDB collections"
)

from .core.models import DocumentChunk, MarkdownAST, ProcessingResult

__all__ = ["DocumentChunk", "MarkdownAST", "ProcessingResult", "__version__"]
