"""Metadata extraction and enhancement for documents and chunks."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..utils.logging import get_logger
from .models import MarkdownAST

logger = get_logger(__name__)


class MetadataExtractor:
    """Extracts and enhances metadata for documents and chunks."""

    def extract_file_metadata(self, file_path: Path) -> Dict[str, Any]:
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

        except Exception as e:
            logger.warning(f"Failed to extract file metadata for {file_path}: {e}")
            return {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "extraction_error": str(e),
            }

    def extract_document_metadata(self, ast: MarkdownAST) -> Dict[str, Any]:
        """Extract document-level metadata from AST.

        Args:
            ast: Parsed markdown AST

        Returns:
            Dictionary of document metadata
        """
        metadata: Dict[str, Any] = {}

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
            languages = list(set(cb.language for cb in code_blocks if cb.language))
            metadata["code_languages"] = languages

        # Calculate estimated reading time (assuming 200 words per minute)
        total_text = " ".join(e.text for e in ast.elements if e.text)
        word_count = len(total_text.split())
        metadata["word_count"] = word_count
        metadata["estimated_reading_time_minutes"] = max(1, round(word_count / 200))

        return metadata

    def enhance_chunk_metadata(
        self,
        chunk_metadata: Dict[str, Any],
        chunk_index: int,
        total_chunks: int,
        structural_context: Optional[str] = None,
    ) -> Dict[str, Any]:
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
        enhanced["processed_at"] = datetime.utcnow().isoformat()
        enhanced["processor_version"] = "0.1.0"

        return enhanced

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
        except Exception as e:
            logger.warning(f"Failed to calculate hash for {file_path}: {e}")
            return f"error_{hash(str(file_path))}"

    def _extract_title(self, ast: MarkdownAST) -> Optional[str]:
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
