"""Input validation utilities."""

import fnmatch
from pathlib import Path

from .errors import FileSystemError, InputValidationError


def validate_input_paths(  # noqa: C901
    paths: list[str], recursive: bool = False, pattern: str = "*.md"
) -> list[Path]:
    """Validate input file paths and collect markdown files.

    Args:
        paths: List of file/directory path strings
        recursive: Whether to process directories recursively
        pattern: File pattern for filtering (e.g., "*.md", "**/*.txt")

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

            # Platform-specific readable check
            if not _is_path_readable(path):
                raise InputValidationError(
                    f"Path is not readable: {path}",
                    error_code=1001,
                    context={"path": str(path), "operation": "path_readable_check"},
                )

            if path.is_file():
                # Check if file matches pattern
                if _matches_pattern(path.name, pattern):
                    validated_paths.append(path)
                elif pattern == "*.md" and not path.suffix.lower() == ".md":
                    # Backward compatibility: if using default pattern,
                    # show specific error
                    raise InputValidationError(
                        f"File is not a markdown file: {path}",
                        error_code=1002,
                        context={"path": str(path), "suffix": path.suffix},
                    )

            elif path.is_dir():
                if recursive:
                    collected_files = _collect_files_from_directory(path, pattern)
                    if not collected_files:
                        raise InputValidationError(
                            f"No files matching pattern '{pattern}' found "
                            f"in directory: {path}",
                            error_code=1003,
                            context={
                                "path": str(path),
                                "recursive": True,
                                "pattern": pattern,
                            },
                        )
                    validated_paths.extend(collected_files)
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
            ) from e

    if not validated_paths:
        raise InputValidationError(
            f"No valid files matching pattern '{pattern}' found",
            error_code=1005,
            context={"input_paths": paths, "recursive": recursive, "pattern": pattern},
        )

    # Remove duplicates while preserving order
    seen = set()
    unique_paths = []
    for path in validated_paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)

    return unique_paths


def _is_path_readable(path: Path) -> bool:
    """Check if path is readable with platform-specific handling.

    Args:
        path: Path to check

    Returns:
        True if path is readable
    """
    try:
        if path.is_file():
            # Try to read a small amount to test readability
            with path.open("rb") as f:
                f.read(1)
            return True
        elif path.is_dir():
            # Try to list directory contents
            list(path.iterdir())
            return True
        return False
    except (OSError, PermissionError):
        return False


def _matches_pattern(filename: str, pattern: str) -> bool:
    """Check if filename matches the given pattern.

    Args:
        filename: Name of the file to check
        pattern: Pattern to match against

    Returns:
        True if filename matches pattern
    """
    return fnmatch.fnmatch(filename.lower(), pattern.lower())


def _collect_files_from_directory(directory: Path, pattern: str) -> list[Path]:
    """Collect files from directory matching pattern.

    Args:
        directory: Directory to search in
        pattern: File pattern to match

    Returns:
        List of matching file paths
    """
    collected_files = []

    try:
        # Handle glob-style patterns with **
        if "**" in pattern:
            # Use rglob for recursive patterns
            for file_path in directory.rglob("*"):
                if file_path.is_file() and _matches_pattern(
                    file_path.name, pattern.split("/")[-1]
                ):
                    collected_files.append(file_path)
        else:
            # Use glob for simple patterns
            for file_path in directory.glob("*"):
                if file_path.is_file() and _matches_pattern(file_path.name, pattern):
                    collected_files.append(file_path)

            # Also check subdirectories recursively
            for subdir in directory.glob("*"):
                if subdir.is_dir() and _is_path_readable(subdir):
                    try:
                        for file_path in subdir.rglob("*"):
                            if file_path.is_file() and _matches_pattern(
                                file_path.name, pattern
                            ):
                                collected_files.append(file_path)
                    except (OSError, PermissionError):
                        # Skip directories we can't access
                        continue

    except (OSError, PermissionError):
        # Return what we could collect
        pass

    return collected_files


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
            f"Collection name contains invalid characters: {sorted(invalid_chars)}",
            error_code=1022,
            context={"name": name, "invalid_chars": sorted(invalid_chars)},
        )
