"""CLI display utilities."""

from typing import Any


def show_message(message: str, color: str = "white") -> None:
    """Display a message with optional color."""
    # Using format strings instead of f-strings as per requirements
    print("{}{}{}".format("[", color, "] " + message))


def format_output(data: Any) -> str:
    """Format data for display."""
    if data is None:
        return "No data"
    return str(data)
