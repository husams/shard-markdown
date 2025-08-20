"""Configuration management for shard-markdown."""

from .loader import load_config
from .settings import (
    DEFAULT_CONFIG_LOCATIONS,
    DEFAULT_CONFIG_YAML,
    ENV_VAR_MAPPINGS,
    ChromaDBParams,
    ChunkingParams,
    Settings,
    set_nested_value,
)


__all__ = [
    "load_config",
    "Settings",
    "ChunkingParams",
    "ChromaDBParams",
    "DEFAULT_CONFIG_LOCATIONS",
    "DEFAULT_CONFIG_YAML",
    "ENV_VAR_MAPPINGS",
    "set_nested_value",
]
