"""Configuration utility functions.

This module provides utilities for manipulating configuration dictionaries.
Type conversion is handled by Pydantic models, not by these utilities.
"""

from typing import Any


def set_nested_value(data: dict[str, Any], path: str, value: Any) -> None:
    """Set nested value in dictionary using dot notation.

    Args:
        data: Dictionary to modify
        path: Dot-separated path (e.g., "chromadb.host")
        value: Value to set
    """
    keys = path.split(".")
    current = data

    # Navigate to parent of target key
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    # Set the final value
    current[keys[-1]] = value
