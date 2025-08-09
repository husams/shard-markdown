"""Metadata extraction and enhancement for documents and chunks."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..utils.logging import get_logger
from .models import MarkdownAST


logger = get_logger(__name__)


class MetadataExtractor:
    """Extracts and enhances metadata for documents and chunks."""

    def extract_file_metadata(self, file_path: Path) -> dict[str, Any]:
        """Extract file-level metadata.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary of file metadata
        """
        try:
            stat = file_path.stat()

            # Calculate file hash
            file_hash = self._calculate_file_hash(file_path)

            metadata = {
                "file_path": str(file_path.absolute()),
                "file_name": file_path.name,
                "file_stem": file_path.stem,
                "file_suffix": file_path.suffix,
                "file_size": stat.st_size,
                "file_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "file_created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "file_hash": file_hash,
                "file_hash_algorithm": "sha256",
            }

            # Add parent directory information
            metadata["parent_directory"] = str(file_path.parent)
            metadata["relative_path"] = (
                str(file_path.relative_to(Path.cwd()))
                if file_path.is_relative_to(Path.cwd())
                else str(file_path)
            )

            return metadata

        except (OSError, ValueError) as e:
            logger.warning("Failed to extract file metadata for %s: %s", file_path, e)
            return {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "extraction_error": str(e),
            }

    def extract_document_metadata(self, ast: MarkdownAST) -> dict[str, Any]:
        """Extract document-level metadata from AST.

        Args:
            ast: Parsed markdown AST

        Returns:
            Dictionary of document metadata
        """
        metadata: dict[str, Any] = {}

        # Extract frontmatter metadata
        if ast.frontmatter:
            metadata.update(ast.frontmatter)

        # Extract title if not in frontmatter
        if "title" not in metadata:
            title = self._extract_title(ast)
            if title:
                metadata["title"] = title

        # Document structure statistics
        metadata.update(
            {
                "total_elements": len(ast.elements),
                "header_count": len([e for e in ast.elements if e.type == "header"]),
                "paragraph_count": len(
                    [e for e in ast.elements if e.type == "paragraph"]
                ),
                "code_block_count": len(
                    [e for e in ast.elements if e.type == "code_block"]
                ),
                "list_count": len([e for e in ast.elements if e.type == "list"]),
            }
        )

        # Extract header hierarchy
        headers = [e for e in ast.elements if e.type == "header"]
        if headers:
            header_levels = [h.level for h in headers if h.level is not None]
            if header_levels:
                metadata["header_levels"] = list(set(header_levels))
                metadata["max_header_level"] = max(header_levels)
                metadata["min_header_level"] = min(header_levels)
                metadata["table_of_contents"] = [
                    {"level": h.level, "text": h.text}
                    for h in headers
                    if h.level is not None
                ]

        # Extract code languages
        code_blocks = [e for e in ast.elements if e.type == "code_block" and e.language]
        if code_blocks:
            languages = list({cb.language for cb in code_blocks if cb.language})
            metadata["code_languages"] = languages

        # Calculate estimated reading time (assuming 200 words per minute)
        total_text = " ".join(e.text for e in ast.elements if e.text)
        word_count = len(total_text.split())
        metadata["word_count"] = word_count
        metadata["estimated_reading_time_minutes"] = max(1, round(word_count / 200))

        return metadata

    def enhance_chunk_metadata(
        self,
        chunk_metadata: dict[str, Any],
        chunk_index: int,
        total_chunks: int,
        structural_context: str | None = None,
    ) -> dict[str, Any]:
        """Enhance chunk metadata with additional information.

        Args:
            chunk_metadata: Base chunk metadata
            chunk_index: Index of chunk in document
            total_chunks: Total number of chunks in document
            structural_context: Structural context string

        Returns:
            Enhanced metadata dictionary
        """
        enhanced = chunk_metadata.copy()

        # Add chunk positioning information
        enhanced.update(
            {
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "is_first_chunk": chunk_index == 0,
                "is_last_chunk": chunk_index == total_chunks - 1,
                "chunk_position_percent": round(
                    (chunk_index / max(total_chunks - 1, 1)) * 100, 2
                ),
            }
        )

        # Add structural context
        if structural_context:
            enhanced["structural_context"] = structural_context
            enhanced["context_depth"] = len(structural_context.split(" > "))

        # Add processing timestamp
        enhanced["processed_at"] = datetime.now(UTC).isoformat()
        enhanced["processor_version"] = "0.1.0"

        return enhanced

    def sanitize_metadata_for_chromadb(
        self, metadata: dict[str, Any] | Any
    ) -> dict[str, Any] | Any:
        """Sanitize metadata for ChromaDB compatibility.

        ChromaDB only accepts primitive types (str, int, float, bool, None) for
        metadata. This method converts complex types to compatible formats:
        - Lists are converted to comma-separated strings
        - Dictionaries are converted to JSON strings
        - Nested structures are handled recursively
        - Primitive types are left unchanged

        Args:
            metadata: Raw metadata dictionary or other value

        Returns:
            Sanitized metadata dictionary compatible with ChromaDB
        """
        if not isinstance(metadata, dict):
            return metadata

        sanitized = {}

        for key, value in metadata.items():
            sanitized_value = self._sanitize_metadata_value(value)
            sanitized[key] = sanitized_value

        return sanitized

    def _sanitize_metadata_value(self, value: Any) -> str | int | float | bool | None:
        """Sanitize a single metadata value for ChromaDB compatibility.

        Args:
            value: Value to sanitize

        Returns:
            Sanitized value compatible with ChromaDB
        """
        # Handle None
        if value is None:
            return None

        # Handle primitive types (already compatible)
        if isinstance(value, str | int | float | bool):
            return value

        # Handle lists - convert to comma-separated string
        if isinstance(value, list):
            if not value:  # Empty list
                return ""

            # Handle list of primitives
            try:
                # Convert each element to string, handling nested structures
                str_elements = []
                for item in value:
                    if isinstance(item, str | int | float | bool):
                        str_elements.append(str(item))
                    elif isinstance(item, dict):
                        # Convert nested dict to JSON
                        str_elements.append(json.dumps(item, separators=(",", ":")))
                    elif isinstance(item, list):
                        # Convert nested list to JSON
                        str_elements.append(json.dumps(item, separators=(",", ":")))
                    else:
                        str_elements.append(str(item))

                return ",".join(str_elements)
            except (TypeError, ValueError) as e:
                logger.warning("Failed to convert list to string: %s", e)
                return str(value)

        # Handle dictionaries - convert to JSON string
        if isinstance(value, dict):
            try:
                return json.dumps(value, separators=(",", ":"))
            except (TypeError, ValueError) as e:
                logger.warning("Failed to convert dict to JSON: %s", e)
                return str(value)

        # Handle other types - convert to string
        return str(value)

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file content.

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal hash string
        """
        try:
            hash_obj = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except OSError as e:
            logger.warning("Failed to calculate hash for %s: %s", file_path, e)
            return f"error_{hash(str(file_path))}"

    def _extract_title(self, ast: MarkdownAST) -> str | None:
        """Extract document title from first level-1 header.

        Args:
            ast: Markdown AST

        Returns:
            Document title or None
        """
        for element in ast.elements:
            if element.type == "header" and element.level == 1:
                return element.text
        return None
