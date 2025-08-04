"""Validation rules for data processing."""

from typing import Any


def validate_data(input_data: dict[str, Any]) -> bool:
    """Validate input data structure."""
    if not isinstance(input_data, dict):
        return False
    return bool(input_data)


def check_format(data: Any) -> bool:
    """Check if data format is valid."""
    return data is not None
