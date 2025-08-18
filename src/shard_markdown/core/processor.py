"""Main document processing coordinator."""

import hashlib
import time
from pathlib import Path
from typing import Any

from ..config import ChunkingConfig
from ..utils.logging import get_logger
from .chunking.engine import ChunkingEngine
from .metadata import MetadataExtractor
from .models import BatchResult, ProcessingResult
from .parser import MarkdownParser


logger = get_logger(__name__)


class DocumentProcessor:
    """Main document processing coordinator."""

    def __init__(self, chunking_config: ChunkingConfig):
        """Initialize processor with configuration.

        Args:
            chunking_config: Configuration for chunking
        """
        self.chunking_config = chunking_config
        self.parser = MarkdownParser()
        self.chunker = ChunkingEngine(chunking_config)
        self.metadata_extractor = MetadataExtractor()

    def process_file(
        self,
        file_path: Path,
        collection_name: str,
        custom_metadata: dict[str, Any] | None = None,
        insert_to_chromadb: bool = False,
    ) -> ProcessingResult:
        """Process a single markdown file.

        Args:
            file_path: Path to markdown file
            collection_name: Target collection name
            custom_metadata: Additional metadata to include
            insert_to_chromadb: Whether to insert chunks to ChromaDB

        Returns:
            Processing result
        """
        start_time = time.time()

        try:
            # Validate file
            if not file_path.exists():
                error_msg = f"File not found: {file_path}"
                return ProcessingResult(
                    file_path=file_path,
                    success=False,
                    chunks_created=0,
                    processing_time=time.time() - start_time,
                    collection_name=collection_name,
                    error=error_msg,
                )

            if not file_path.is_file():
                error_msg = f"Path is not a file: {file_path}"
                return ProcessingResult(
                    file_path=file_path,
                    success=False,
                    chunks_created=0,
                    processing_time=time.time() - start_time,
                    collection_name=collection_name,
                    error=error_msg,
                )

            # Read and parse file
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                error_msg = f"Cannot decode file as UTF-8: {file_path}"
                return ProcessingResult(
                    file_path=file_path,
                    success=False,
                    chunks_created=0,
                    processing_time=time.time() - start_time,
                    collection_name=collection_name,
                    error=error_msg,
                )

            if not content.strip():
                logger.warning("File is empty: %s", file_path)
                return ProcessingResult(
                    file_path=file_path,
                    success=True,
                    chunks_created=0,
                    processing_time=time.time() - start_time,
                    collection_name=collection_name,
                )

            # Parse markdown
            ast = self.parser.parse(content)

            # Extract and merge metadata
            file_metadata = self.metadata_extractor.extract_file_metadata(file_path)
            if custom_metadata:
                file_metadata.update(custom_metadata)

            # Add metadata to AST
            ast.metadata.update(file_metadata)

            # Chunk document
            chunks = self.chunker.chunk_document(ast)

            # Add file-level metadata to chunks
            for chunk in chunks:
                chunk.metadata.update(file_metadata)
                # Add content hash for deduplication
                chunk.metadata["content_hash"] = hashlib.sha256(
                    chunk.content.encode("utf-8")
                ).hexdigest()

            processing_time = time.time() - start_time

            logger.info(
                "Successfully processed %s: %s chunks in %.2fs",
                file_path.name,
                len(chunks),
                processing_time,
            )

            return ProcessingResult(
                file_path=file_path,
                success=True,
                chunks_created=len(chunks),
                processing_time=processing_time,
                collection_name=collection_name,
            )

        except Exception as e:
            # Handle any unexpected errors
            error_msg = str(e)
            processing_time = time.time() - start_time

            logger.exception("Error processing file %s: %s", file_path, error_msg)

            return ProcessingResult(
                file_path=file_path,
                success=False,
                chunks_created=0,
                processing_time=processing_time,
                collection_name=collection_name,
                error=error_msg,
            )

    def process_batch(
        self,
        file_paths: list[Path],
        collection_name: str,
        custom_metadata: dict[str, Any] | None = None,
        insert_to_chromadb: bool = False,
    ) -> BatchResult:
        """Process multiple markdown files in batch.

        Args:
            file_paths: List of file paths to process
            collection_name: Target collection name
            custom_metadata: Additional metadata to include
            insert_to_chromadb: Whether to insert chunks to ChromaDB

        Returns:
            Batch processing result
        """
        return self.process_files(file_paths, collection_name, custom_metadata)

    def process_files(
        self,
        file_paths: list[Path],
        collection_name: str,
        custom_metadata: dict[str, Any] | None = None,
    ) -> BatchResult:
        """Process multiple markdown files.

        Args:
            file_paths: List of file paths to process
            collection_name: Target collection name
            custom_metadata: Additional metadata to include

        Returns:
            Batch processing result
        """
        start_time = time.time()
        results = []

        for file_path in file_paths:
            result = self.process_file(file_path, collection_name, custom_metadata)
            results.append(result)

        # Calculate summary statistics
        total_processing_time = time.time() - start_time
        successful_files = sum(1 for r in results if r.success)
        failed_files = len(results) - successful_files
        total_chunks = sum(r.chunks_created for r in results)

        return BatchResult(
            results=results,
            total_files=len(file_paths),
            successful_files=successful_files,
            failed_files=failed_files,
            total_chunks=total_chunks,
            total_processing_time=total_processing_time,
            collection_name=collection_name,
        )
