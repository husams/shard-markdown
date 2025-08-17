"""Filesystem utility functions."""

from pathlib import Path


def ensure_directory_exists(path: str | Path) -> None:
    """Ensure directory exists, creating it if necessary.

    This function replaces repeated mkdir(parents=True, exist_ok=True) calls
    throughout the codebase, providing a consistent interface for directory
    creation.

    Args:
        path: Directory path to ensure exists (string or Path object)
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
