"""Main document processing coordinator."""

import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ..config.settings import ProcessingConfig
from ..utils.errors import FileSystemError, ProcessingError
from ..utils.logging import get_logger
from .chunking.engine import ChunkingEngine
from .encoding import EncodingDetector
from .metadata import MetadataExtractor
from .models import BatchResult, ChunkingConfig, DocumentChunk, ProcessingResult
from .parser import MarkdownParser
from .validation import ContentValidator


logger = get_logger(__name__)


class DocumentProcessor:
    """Main document processing coordinator."""

    def __init__(
        self,
        chunking_config: ChunkingConfig,
        processing_config: ProcessingConfig | None = None,
    ) -> None:
        """Initialize processor with configuration.

        Args:
            chunking_config: Configuration for chunking
            processing_config: Configuration for file processing
        """
        self.chunking_config = chunking_config
        self.config = processing_config or ProcessingConfig()
        self.parser = MarkdownParser()
        self.chunker = ChunkingEngine(chunking_config)
        self.metadata_extractor = MetadataExtractor()

        # Initialize content validator if enabled
        self.validator = (
            ContentValidator(self.config.validation)
            if self.config.validation.enable_content_validation
            else None
        )

        # Initialize encoding detector if enabled
        self.encoding_detector = (
            EncodingDetector(self.config.encoding_detection)
            if self.config.enable_encoding_detection
            else None
        )

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
            # Early binary content detection before attempting to read as text
            if self.validator and file_path.exists():
                try:
                    # Quick binary detection check using first few bytes
                    with open(file_path, "rb") as f:
                        sample_bytes = f.read(1024)  # Read first 1KB

                    if self.validator.detect_binary_content(sample_bytes):
                        error_msg = (
                            "File appears to contain binary data "
                            "(unsupported content type)"
                        )
                        if self.config.strict_validation:
                            raise FileSystemError(error_msg, error_code=1209)
                        else:
                            # In graceful mode, binary files should fail
                            # (not succeed with 0 chunks)
                            return ProcessingResult(
                                file_path=file_path,
                                success=False,
                                error=error_msg,
                                chunks_created=0,
                                processing_time=time.time() - start_time,
                                collection_name=collection_name,
                            )
                except (OSError, PermissionError):
                    # If we can't read the file, continue with normal processing
                    pass

            # Read file content
            content = self._read_file(file_path)

            # If content is empty, always treat as failure (consistent behavior)
            if not content:
                error_msg = "File is empty or contains no processable content"
                if self.config.strict_validation:
                    raise FileSystemError(error_msg)
                else:
                    return ProcessingResult(
                        file_path=file_path,
                        success=False,
                        error=error_msg,
                        chunks_created=0,
                        processing_time=time.time() - start_time,
                        collection_name=collection_name,
                    )

            # Extract file metadata
            file_metadata = self.metadata_extractor.extract_file_metadata(file_path)

            # Parse document and extract document metadata
            document = self.parser.parse(content)
            doc_metadata = self.metadata_extractor.extract_document_metadata(document)

            # Chunk the document
            chunks = self.chunker.chunk_document(document)

            # Handle no chunks generated
            if not chunks:
                if self.config.strict_validation:
                    return ProcessingResult(
                        file_path=file_path,
                        success=False,
                        chunks_created=0,
                        processing_time=time.time() - start_time,
                        collection_name=collection_name,
                        error="No chunks generated from document",
                    )
                else:
                    # Graceful mode: success with 0 chunks
                    return ProcessingResult(
                        file_path=file_path,
                        success=True,
                        chunks_created=0,
                        processing_time=time.time() - start_time,
                        collection_name=collection_name,
                    )

            # Enhance chunks with metadata
            enhanced_chunks = self._enhance_chunks(
                chunks, file_metadata, doc_metadata, file_path
            )

            # Success result
            return ProcessingResult(
                file_path=file_path,
                success=True,
                chunks_created=len(enhanced_chunks),
                processing_time=time.time() - start_time,
                collection_name=collection_name,
            )

        except FileSystemError as e:
            # File system errors should be handled based on configuration
            if self.config.strict_validation:
                # In strict mode, re-raise the exception to be handled by caller
                return ProcessingResult(
                    file_path=file_path,
                    success=False,
                    chunks_created=0,
                    processing_time=time.time() - start_time,
                    collection_name=collection_name,
                    error=str(e),
                )
            else:
                # In graceful mode, handle different error types appropriately
                error_str = str(e).lower()
                if any(
                    keyword in error_str
                    for keyword in [
                        "corrupted encoding",
                        "binary data",
                        "unsupported content type",
                        "control characters",
                        "printable characters",
                    ]
                ):
                    # Binary/corrupted files should fail even in graceful mode
                    return ProcessingResult(
                        file_path=file_path,
                        success=False,
                        chunks_created=0,
                        processing_time=time.time() - start_time,
                        collection_name=collection_name,
                        error=str(e),
                    )
                else:
                    # Other file system errors: return success with 0 chunks
                    return ProcessingResult(
                        file_path=file_path,
                        success=True,
                        chunks_created=0,
                        processing_time=time.time() - start_time,
                        collection_name=collection_name,
                    )

        except Exception as e:
            return ProcessingResult(
                file_path=file_path,
                success=False,
                chunks_created=0,
                processing_time=time.time() - start_time,
                collection_name=collection_name,
                error=f"Processing failed: {e}",
            )

    def process_batch(
        self,
        file_paths: list[Path],
        collection_name: str | None = None,
        max_workers: int | None = None,
    ) -> BatchResult:
        """Process multiple documents concurrently.

        Args:
            file_paths: List of file paths to process
            collection_name: Target collection name
            max_workers: Maximum number of worker threads

        Returns:
            BatchResult with aggregated results
        """
        start_time = time.time()

        # Use default collection name if not provided
        collection_name = collection_name or "default"

        if not file_paths:
            return BatchResult(
                results=[],
                total_files=0,
                successful_files=0,
                failed_files=0,
                total_chunks=0,
                total_processing_time=0,
                collection_name=collection_name,
            )

        # Use configured max_workers if not specified
        max_workers = max_workers or self.config.max_workers

        results = []
        successful_files = 0
        failed_files = 0
        total_chunks = 0

        # Process files concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(
                    self.process_document, file_path, collection_name
                ): file_path
                for file_path in file_paths
            }

            # Collect results as they complete
            for future in as_completed(future_to_path):
                result = future.result()
                results.append(result)

                if result.success:
                    successful_files += 1
                    total_chunks += result.chunks_created
                else:
                    failed_files += 1

        total_processing_time = time.time() - start_time

        return BatchResult(
            results=results,
            total_files=len(file_paths),
            successful_files=successful_files,
            failed_files=failed_files,
            total_chunks=total_chunks,
            total_processing_time=total_processing_time,
            collection_name=collection_name,
        )

    def get_encoding_stats(self) -> dict[str, Any]:
        """Get encoding detection statistics if available.

        Returns:
            Dictionary with encoding detection statistics
        """
        if self.encoding_detector:
            return self.encoding_detector.get_stats()
        return {"encoding_detection": "disabled"}

    def _read_file(self, file_path: Path, encoding: str | None = None) -> str:
        """Read file content with advanced encoding detection and fallback.

        Args:
            file_path: Path to file
            encoding: Primary encoding to try (optional override)

        Returns:
            File content as string

        Raises:
            FileSystemError: If file cannot be read or is corrupted
        """
        try:
            # Check if file exists and is readable
            if not file_path.exists():
                if self.config.strict_validation:
                    raise FileSystemError(
                        f"File not found: {file_path}",
                        error_code=1201,
                        context={"file_path": str(file_path)},
                    )
                else:
                    logger.info(f"File not found (graceful mode): {file_path}")
                    return ""

            # Check permissions
            if not file_path.is_file():
                raise FileSystemError(
                    f"Path is not a file: {file_path}",
                    error_code=1204,
                    context={"file_path": str(file_path)},
                )

            # Check file size
            file_size = file_path.stat().st_size
            if file_size == 0:
                if self.config.strict_validation:
                    raise ProcessingError(
                        f"Empty file: {file_path}",
                        error_code=1205,
                        context={"file_path": str(file_path)},
                    )
                logger.info(f"Empty file: {file_path}")
                return ""  # Return empty string for empty files in graceful mode

            if file_size > self.config.max_file_size:
                raise ProcessingError(
                    f"File too large: {file_size} bytes "
                    f"(max: {self.config.max_file_size})",
                    error_code=1202,
                    context={"file_path": str(file_path), "file_size": file_size},
                )

            # Determine encodings to try - either with advanced detection or fallback
            if self.encoding_detector and not encoding:
                # Use advanced encoding detection
                content = self._read_with_detection(file_path)
            else:
                # Use traditional fallback method
                content = self._read_with_fallback(file_path, encoding)

            # Apply content validation after successful decoding
            if self.validator and content:
                validation_result = self.validator.validate_content(content, file_path)

                # Log warnings if any
                if validation_result.warnings:
                    for warning in validation_result.warnings:
                        logger.warning(
                            f"Content validation warning for {file_path}: {warning}"
                        )

                # Handle validation failure
                if not validation_result.is_valid:
                    if self.config.strict_validation:
                        raise FileSystemError(
                            f"Content validation failed: {validation_result.error}",
                            error_code=1208,
                            context={
                                "file_path": str(file_path),
                                "validation_error": validation_result.error,
                                "confidence": validation_result.confidence,
                            },
                        )
                    else:
                        # In graceful mode, binary/corrupted files should fail
                        # but other validation issues should return empty content
                        error_str = (
                            validation_result.error.lower()
                            if validation_result.error
                            else ""
                        )
                        if any(
                            keyword in error_str
                            for keyword in [
                                "binary data",
                                "control characters",
                                "printable characters",
                                "repeated bytes",
                                "encoded binary data",
                            ]
                        ):
                            # Binary content should fail even in graceful mode
                            raise FileSystemError(
                                f"Binary content detected: {validation_result.error}",
                                error_code=1209,
                                context={
                                    "file_path": str(file_path),
                                    "validation_error": validation_result.error,
                                    "confidence": validation_result.confidence,
                                },
                            )
                        else:
                            # Other validation issues: log warning and return
                            # empty content
                            logger.warning(
                                f"Content validation failed for {file_path} "
                                f"(graceful mode): {validation_result.error}"
                            )
                            return ""

            # Handle whitespace-only content
            if not content.strip():
                if self.config.skip_empty_files:
                    logger.info(f"Skipping whitespace-only file: {file_path}")
                    return ""
                else:
                    # In strict mode or when not skipping, handle as per validation mode
                    if self.config.strict_validation:
                        raise ProcessingError(
                            f"File contains only whitespace: {file_path}",
                            error_code=1207,
                            context={"file_path": str(file_path)},
                        )
                    else:
                        # In graceful mode without skipping, still return empty
                        logger.info(f"Whitespace-only file: {file_path}")
                        return ""

            return content

        except Exception as e:
            if isinstance(e, ProcessingError | FileSystemError):
                raise
            raise FileSystemError(
                f"Unexpected error reading {file_path}: {e}",
                error_code=1299,
                context={"file_path": str(file_path)},
            ) from e

    def _read_with_detection(self, file_path: Path) -> str:
        """Read file using advanced encoding detection.

        Args:
            file_path: Path to file to read

        Returns:
            File content as string

        Raises:
            FileSystemError: If file cannot be read
        """
        # Detect encoding with confidence scoring
        if self.encoding_detector is None:
            raise ValueError("Encoding detector not initialized")
        detection_result = self.encoding_detector.detect_encoding(file_path)

        logger.debug(
            f"Encoding detection for {file_path}: {detection_result.encoding} "
            f"(confidence: {detection_result.confidence:.2f})"
        )

        # Get fallback chain based on detection
        encoding_chain = self.encoding_detector.get_fallback_chain(detection_result)

        # Try encodings in order
        for encoding in encoding_chain:
            try:
                with open(file_path, encoding=encoding) as f:
                    content = f.read()

                # Validate content quality with detected encoding
                if self.encoding_detector.validate_content_encoding(content, encoding):
                    logger.debug(f"Successfully read {file_path} using {encoding}")
                    return content
                else:
                    logger.debug(
                        f"Content validation failed for {encoding}, trying next"
                    )
                    continue

            except PermissionError:
                raise FileSystemError(
                    f"Permission denied: {file_path}",
                    error_code=1206,
                    context={"file_path": str(file_path)},
                ) from None
            except UnicodeDecodeError:
                logger.debug(f"Unicode decode error with {encoding}, trying next")
                continue

        # All encodings failed
        raise FileSystemError(
            f"File {file_path} could not be decoded with any encoding",
            error_code=1203,
            context={
                "file_path": str(file_path),
                "encodings_tried": encoding_chain,
                "detection_result": {
                    "encoding": detection_result.encoding,
                    "confidence": detection_result.confidence,
                },
            },
        )

    def _read_with_fallback(self, file_path: Path, encoding: str | None = None) -> str:
        """Read file using traditional encoding fallback method.

        Args:
            file_path: Path to file to read
            encoding: Optional encoding override

        Returns:
            File content as string

        Raises:
            FileSystemError: If file cannot be read
        """
        # Determine encodings to try
        encoding = encoding or self.config.encoding
        encodings = [encoding]
        if self.config.encoding_fallback and self.config.encoding_fallback != encoding:
            encodings.append(self.config.encoding_fallback)

        # Read file content
        content = ""
        for enc in encodings:
            try:
                with open(file_path, encoding=enc) as f:
                    content = f.read()
                break  # Successfully read
            except PermissionError:
                raise FileSystemError(
                    f"Permission denied: {file_path}",
                    error_code=1206,
                    context={"file_path": str(file_path)},
                ) from None
            except UnicodeDecodeError:
                if enc == encodings[-1]:  # Last encoding failed
                    # Always raise FileSystemError for corrupted files, both modes
                    raise FileSystemError(
                        f"File {file_path} contains corrupted encoding",
                        error_code=1203,
                        context={
                            "file_path": str(file_path),
                            "encodings_tried": encodings,
                        },
                    ) from None
                continue

        # Validate content for corruption after reading with fallback encoding
        # (legacy check)
        if len(encodings) > 1 and self._is_content_corrupted(content):
            # Always raise FileSystemError for corrupted files, both modes
            raise FileSystemError(
                f"File {file_path} contains corrupted encoding",
                error_code=1203,
                context={
                    "file_path": str(file_path),
                    "reason": "corrupted_content_detected",
                },
            )

        return content

    def _is_content_corrupted(self, content: str) -> bool:
        """Check if content appears to be corrupted by fallback encoding.

        Args:
            content: Content to check

        Returns:
            True if content appears corrupted
        """
        if not content:
            return False

        # Count suspicious bytes that are common in corrupted UTF-8 decoded as latin-1
        suspicious_chars = 0
        suspicious_bytes = {
            "\xff",  # 0xFF - often appears in corrupted files
            "\xfe",  # 0xFE - often appears in corrupted files
            "\xfd",  # 0xFD - often appears in corrupted files
            "\x80",  # 0x80 - invalid UTF-8 start byte
            "\x81",  # 0x81 - invalid UTF-8 start byte
            "\x82",  # 0x82 - invalid UTF-8 start byte
            "\x83",  # 0x83 - invalid UTF-8 start byte
            "\x84",  # 0x84 - invalid UTF-8 start byte
            "\x85",  # 0x85 - invalid UTF-8 start byte
        }

        for char in content:
            if char in suspicious_bytes:
                suspicious_chars += 1

        # If more than 5% of characters are suspicious, likely corrupted
        if len(content) > 0 and (suspicious_chars / len(content)) > 0.05:
            return True

        # Check for specific patterns that indicate UTF-8 corruption in latin-1
        corruption_patterns = [
            "ÿþý",  # Common corruption pattern from 0xFF 0xFE 0xFD
            "â€™",  # UTF-8 right single quote corrupted in latin-1
            "â€œ",  # UTF-8 left double quote corrupted in latin-1
            "â€",  # UTF-8 right double quote corrupted in latin-1
        ]

        for pattern in corruption_patterns:
            if pattern in content:
                return True

        return False

    def _enhance_chunks(
        self,
        chunks: list[DocumentChunk],
        file_metadata: dict,
        doc_metadata: dict,
        file_path: Path,
    ) -> list[DocumentChunk]:
        """Enhance chunks with metadata and IDs.

        Args:
            chunks: Original chunks from chunking engine
            file_metadata: File-level metadata
            doc_metadata: Document-level metadata
            file_path: Original file path

        Returns:
            Enhanced chunks with metadata and unique IDs
        """
        enhanced_chunks = []

        for i, chunk in enumerate(chunks):
            # Generate unique chunk ID
            chunk_id = self._generate_chunk_id(file_path, i)

            # Merge chunk metadata with file and document metadata
            merged_metadata = chunk.metadata.copy()
            merged_metadata.update(file_metadata)
            merged_metadata.update(doc_metadata)

            # Enhance chunk metadata with positional information
            enhanced_metadata = self.metadata_extractor.enhance_chunk_metadata(
                merged_metadata, i, len(chunks)
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
        """Generate unique chunk ID.

        Args:
            file_path: Source file path
            chunk_index: Zero-based chunk index

        Returns:
            Unique chunk ID string
        """
        # Create hash from file path for consistency
        # MD5 is fine for non-cryptographic use (generating IDs)
        path_hash = hashlib.md5(
            str(file_path).encode(), usedforsecurity=False
        ).hexdigest()[:16]

        # Format: path_hash_index (zero-padded to 4 digits)
        return f"{path_hash}_{chunk_index:04d}"
