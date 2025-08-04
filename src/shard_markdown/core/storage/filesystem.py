"""Filesystem storage implementation."""

import json
import pathlib
from typing import Any


class FilesystemStorage:
    """File system storage handler."""

    def __init__(self, base_path: str) -> None:
        """Initialize filesystem storage."""
        self.base_path = pathlib.Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, data: dict[str, Any], filename: str) -> bool:
        """Save data to filesystem."""
        try:
            file_path = self.base_path / filename
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False

    def get_info(self) -> dict:
        """Return basic class information."""
        return {"type": self.__class__.__name__, "base_path": str(self.base_path)}
