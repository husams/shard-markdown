"""Main document processing coordinator."""

import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ..utils.errors import FileSystemError, ProcessingError
from ..utils.logging import get_logger
from .chunking.engine import ChunkingEngine
from .metadata import MetadataExtractor
from .models import BatchResult, ChunkingConfig, DocumentChunk, ProcessingResult
from .parser import MarkdownParser


logger = get_logger(__name__)


class DocumentProcessor:
    """Main document processing coordinator."""

    def __init__(self, chunking_config: ChunkingConfig) -> None:
        """Initialize processor with configuration.

        Args:
            chunking_config: Configuration for chunking
        """
        self.chunking_config = chunking_config
        self.parser = MarkdownParser()
        self.chunker = ChunkingEngine(chunking_config)
        self.metadata_extractor = MetadataExtractor()

    def process_document(
        self, file_path: Path, collection_name: str | None = None
    ) -> ProcessingResult:
        """Process single document through full pipeline.

        Args:
            file_path: Path to markdown file
            collection_name: Target collection name

        Returns:
            ProcessingResult with details
        """
        start_time = time.time()

        try:
            logger.info("Processing document: %s", file_path)

            # Read and validate file
            content = self._read_file(file_path)

            # Parse markdown
            ast = self.parser.parse(content)

            # Extract metadata
            file_metadata = self.metadata_extractor.extract_file_metadata(file_path)
            doc_metadata = self.metadata_extractor.extract_document_metadata(ast)

            # Chunk document
            chunks = self.chunker.chunk_document(ast)

            if not chunks:
                logger.warning("No chunks generated for %s", file_path)
                return ProcessingResult(
                    file_path=file_path,
                    success=False,
                    error="No chunks generated from document",
                    processing_time=time.time() - start_time,
                )

            # Enhance chunks with metadata
            enhanced_chunks = self._enhance_chunks(
                chunks, file_metadata, doc_metadata, file_path
            )

            processing_time = time.time() - start_time

            logger.info(
                f"Successfully processed {file_path}: "
                f"{len(enhanced_chunks)} chunks in {processing_time:.2f}s"
            )

            return ProcessingResult(
                file_path=file_path,
                success=True,
                chunks_created=len(enhanced_chunks),
                processing_time=processing_time,
                collection_name=collection_name,
            )

        except (OSError, ValueError, RuntimeError) as e:
            processing_time = time.time() - start_time
            error_msg = str(e)

            logger.error("Failed to process %s: %s", file_path, error_msg)

            return ProcessingResult(
                file_path=file_path,
                success=False,
                error=error_msg,
                processing_time=processing_time,
            )

    def process_batch(
        self, file_paths: list[Path], collection_name: str, max_workers: int = 4
    ) -> BatchResult:
        """Process multiple documents with concurrency.

        Args:
            file_paths: List of file paths to process
            collection_name: Target collection name
            max_workers: Maximum number of worker threads

        Returns:
            BatchResult with aggregated statistics
        """
        start_time = time.time()
        logger.info(
            "Starting batch processing of %d files with %d workers",
            len(file_paths),
            max_workers,
        )

        # Process files concurrently and collect results
        results = self._execute_concurrent_processing(
            file_paths, collection_name, max_workers
        )
        # Build batch result with statistics
        batch_stats = self._calculate_batch_statistics(
            results, file_paths, collection_name, start_time
        )
        logger.info(
            "Batch processing complete: %d/%d files, %d chunks, %.2fs",
            batch_stats.successful_files,
            batch_stats.total_files,
            batch_stats.total_chunks,
            batch_stats.total_processing_time,
        )

        return batch_stats

    def _execute_concurrent_processing(
        self, file_paths: list[Path], collection_name: str, max_workers: int
    ) -> list[ProcessingResult]:
        """Execute concurrent processing of files."""
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(self.process_document, path, collection_name): path
                for path in file_paths
            }

            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    results.append(future.result())
                except (OSError, ValueError, RuntimeError) as e:
                    logger.error("Unexpected error processing %s: %s", path, e)
                    results.append(
                        ProcessingResult(
                            file_path=path,
                            success=False,
                            error=f"Unexpected error: {str(e)}",
                        )
                    )
        return results

    def _calculate_batch_statistics(
        self,
        results: list[ProcessingResult],
        file_paths: list[Path],
        collection_name: str,
        start_time: float,
    ) -> BatchResult:
        """Calculate batch processing statistics."""
        processing_stats: dict[str, Any] = {
            "successful": [r for r in results if r.success],
            "failed": [r for r in results if not r.success],
            "total_time": time.time() - start_time,
        }
        total_chunks = sum(r.chunks_created for r in processing_stats["successful"])

        return BatchResult(
            results=results,
            total_files=len(file_paths),
            successful_files=len(processing_stats["successful"]),
            failed_files=len(processing_stats["failed"]),
            total_chunks=total_chunks,
            total_processing_time=processing_stats["total_time"],
            collection_name=collection_name,
        )

    def _read_file(self, file_path: Path) -> str:
        """Read file content with encoding detection.

        Args:
            file_path: Path to file

        Returns:
            File content as string

        Raises:
            FileSystemError: If file cannot be read
        """
        # Check file size (limit to 100MB)
        try:
            file_size = file_path.stat().st_size
            if file_size > 100 * 1024 * 1024:
                raise FileSystemError(
                    f"File too large: {file_path} ({file_size} bytes)",
                    error_code=1202,
                    context={"file_path": str(file_path), "file_size": file_size},
                )
        except OSError as e:
            raise FileSystemError(
                f"Cannot access file: {file_path}",
                error_code=1201,
                context={"file_path": str(file_path)},
                cause=e,
            )

        # Try multiple encodings
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                with open(file_path, encoding=encoding) as f:
                    content = f.read()

                # Validate content is not empty
                if not content.strip():
                    raise ProcessingError(
                        f"File is empty or contains only whitespace: {file_path}",
                        error_code=1301,
                        context={"file_path": str(file_path)},
                    )

                return content

            except UnicodeDecodeError:
                if encoding == encodings[-1]:  # Last encoding failed
                    raise FileSystemError(
                        f"Cannot decode file with any supported encoding: {file_path}",
                        error_code=1203,
                        context={
                            "file_path": str(file_path),
                            "encodings_tried": encodings,
                        },
                    )
                continue
            except OSError as e:
                raise FileSystemError(
                    f"Error reading file: {file_path}",
                    error_code=1206,
                    context={"file_path": str(file_path)},
                    cause=e,
                ) from e

        # This should never be reached, but mypy needs it
        raise FileSystemError(
            f"Failed to read file: {file_path}",
            error_code=1299,
            context={"file_path": str(file_path)},
        )

    def _enhance_chunks(
        self,
        chunks: list[DocumentChunk],
        file_metadata: dict,
        doc_metadata: dict,
        file_path: Path,
    ) -> list[DocumentChunk]:
        """Enhance chunks with comprehensive metadata.

        Args:
            chunks: List of document chunks
            file_metadata: File-level metadata
            doc_metadata: Document-level metadata
            file_path: Source file path

        Returns:
            List of enhanced chunks
        """
        enhanced_chunks = []

        for i, chunk in enumerate(chunks):
            # Generate unique chunk ID
            chunk_id = self._generate_chunk_id(file_path, i)

            # Combine all metadata
            enhanced_metadata = {
                **file_metadata,
                **doc_metadata,
                **chunk.metadata,
            }

            # Add chunk-specific metadata
            enhanced_metadata = self.metadata_extractor.enhance_chunk_metadata(
                enhanced_metadata,
                i,
                len(chunks),
                chunk.metadata.get("structural_context"),
            )

            # Create enhanced chunk
            enhanced_chunk = DocumentChunk(
                id=chunk_id,
                content=chunk.content,
                metadata=enhanced_metadata,
                start_position=chunk.start_position,
                end_position=chunk.end_position,
            )

            enhanced_chunks.append(enhanced_chunk)

        return enhanced_chunks

    def _generate_chunk_id(self, file_path: Path, chunk_index: int) -> str:
        """Generate unique chunk identifier.

        Args:
            file_path: Source file path
            chunk_index: Index of chunk in document

        Returns:
            Unique chunk ID
        """
        # Create hash from file path for uniqueness
        path_hash = hashlib.sha256(str(file_path).encode()).hexdigest()[:16]
        return f"{path_hash}_{chunk_index:04d}"
