"""Configuration management for shard-markdown.

This module provides a simplified, flat configuration structure that replaces
the previous nested configuration model. All configuration options are now
accessible as direct attributes of the Settings class.
"""

from .settings import (
    # Backward compatibility aliases (deprecated)
    AppConfig,
    ChromaDBConfig,
    ChunkingConfig,
    ChunkingMethod,
    LoggingConfig,
    ProcessingConfig,
    Settings,
    create_default_config,
    load_config,
    save_config,
    set_nested_value,
)


__all__ = [
    # New simplified API
    "Settings",
    "ChunkingMethod",
    "load_config",
    "save_config",
    "create_default_config",
    "set_nested_value",
    # Backward compatibility (deprecated)
    "AppConfig",
    "ChromaDBConfig",
    "ChunkingConfig",
    "LoggingConfig",
    "ProcessingConfig",
]
