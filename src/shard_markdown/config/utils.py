"""Shared configuration utilities."""

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


def parse_config_value(value: str) -> Any:
    """Parse configuration value to appropriate type.

    Args:
        value: String value to parse

    Returns:
        Converted value (str, int, float, bool, or None)
    """
    # Handle boolean values
    if value.lower() in ("true", "1", "yes", "on"):
        return True
    elif value.lower() in ("false", "0", "no", "off"):
        return False

    # Handle None/null values
    elif value.lower() in ("null", "none", ""):
        return None

    # Try to convert to integer
    try:
        return int(value)
    except ValueError:
        pass

    # Try to convert to float
    try:
        return float(value)
    except ValueError:
        pass

    # Return as string
    return value
