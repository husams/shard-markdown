"""Configuration package - flat and simple."""

from .loader import create_default_config, load_config, save_config
from .settings import Settings


__all__ = ["Settings", "load_config", "save_config", "create_default_config"]
