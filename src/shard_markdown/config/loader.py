"""Configuration loading and management.

This module provides backward compatibility by re-exporting functions from settings.py.
The actual loading logic has been consolidated into settings.py.
"""

from .settings import (
    create_default_config,
    load_config,
    save_config,
)


__all__ = [
    "create_default_config",
    "load_config",
    "save_config",
]
