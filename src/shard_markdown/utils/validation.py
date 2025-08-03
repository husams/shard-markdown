"""Input validation utilities."""

import os
from pathlib import Path
from typing import List

from .errors import FileSystemError, InputValidationError


def validate_input_paths(paths: List[str], recursive: bool = False) -> List[Path]:
    """Validate input file paths and collect markdown files.

    Args:
        paths: List of file/directory path strings
        recursive: Whether to process directories recursively

    Returns:
        List of validated markdown file paths

    Raises:
        InputValidationError: If paths are invalid
        FileSystemError: If file system access fails
    """
    if not paths:
        raise InputValidationError(
            "No input paths provided", error_code=1000, context={"paths": paths}
        )

    validated_paths = []

    for path_str in paths:
        try:
            path = Path(path_str).resolve()

            if not path.exists():
                raise InputValidationError(
                    f"Path does not exist: {path}",
                    error_code=1001,
                    context={"path": str(path), "operation": "path_validation"},
                )

            if path.is_file():
                if not path.suffix.lower() == ".md":
                    raise InputValidationError(
                        f"File is not a markdown file: {path}",
                        error_code=1002,
                        context={"path": str(path), "suffix": path.suffix},
                    )
                validated_paths.append(path)

            elif path.is_dir():
                if recursive:
                    md_files = list(path.rglob("*.md"))
                    if not md_files:
                        raise InputValidationError(
                            f"No markdown files found in directory: {path}",
                            error_code=1003,
                            context={"path": str(path), "recursive": True},
                        )
                    validated_paths.extend(md_files)
                else:
                    raise InputValidationError(
                        f"Path is directory but recursive flag not set: {path}",
                        error_code=1004,
                        context={"path": str(path), "recursive": False},
                    )

        except OSError as e:
            raise FileSystemError(
                f"Cannot access path: {path_str}",
                error_code=1201,
                context={"path": path_str, "os_error": str(e)},
                cause=e,
            )

    if not validated_paths:
        raise InputValidationError(
            "No valid markdown files found",
            error_code=1005,
            context={"input_paths": paths, "recursive": recursive},
        )

    return validated_paths


def validate_chunk_parameters(chunk_size: int, chunk_overlap: int) -> None:
    """Validate chunking parameters.

    Args:
        chunk_size: Maximum chunk size
        chunk_overlap: Overlap between chunks

    Raises:
        InputValidationError: If parameters are invalid
    """
    if chunk_size <= 0:
        raise InputValidationError(
            "Chunk size must be positive",
            error_code=1010,
            context={"chunk_size": chunk_size},
        )

    if chunk_size < 100:
        raise InputValidationError(
            "Chunk size too small (minimum 100 characters)",
            error_code=1011,
            context={"chunk_size": chunk_size, "minimum": 100},
        )

    if chunk_size > 50000:
        raise InputValidationError(
            "Chunk size too large (maximum 50,000 characters)",
            error_code=1012,
            context={"chunk_size": chunk_size, "maximum": 50000},
        )

    if chunk_overlap < 0:
        raise InputValidationError(
            "Chunk overlap cannot be negative",
            error_code=1013,
            context={"chunk_overlap": chunk_overlap},
        )

    if chunk_overlap >= chunk_size:
        raise InputValidationError(
            "Chunk overlap must be smaller than chunk size",
            error_code=1014,
            context={"chunk_size": chunk_size, "chunk_overlap": chunk_overlap},
        )


def validate_collection_name(name: str) -> None:
    """Validate ChromaDB collection name.

    Args:
        name: Collection name to validate

    Raises:
        InputValidationError: If name is invalid
    """
    if not name or not name.strip():
        raise InputValidationError(
            "Collection name cannot be empty", error_code=1020, context={"name": name}
        )

    name = name.strip()

    if len(name) > 63:
        raise InputValidationError(
            f"Collection name too long: {name} (max 63 characters)",
            error_code=1021,
            context={"name": name, "length": len(name), "max_length": 63},
        )

    # Check for invalid characters (ChromaDB requirements)
    invalid_chars = set(name) - set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    )
    if invalid_chars:
        raise InputValidationError(
            f"Collection name contains invalid characters: \
    {sorted(invalid_chars)}",
            error_code=1022,
            context={"name": name, "invalid_chars": sorted(invalid_chars)},
        )
