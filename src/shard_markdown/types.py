"""Type definitions for improved type safety across the codebase."""

from pathlib import Path
from typing import Any, Protocol, TypedDict, runtime_checkable


# Progress display protocols
@runtime_checkable
class ProgressProtocol(Protocol):
    """Protocol for progress display objects."""

    def add_task(
        self,
        description: str,
        start: bool = True,
        total: float | None = 100.0,
        completed: int = 0,
        visible: bool = True,
        **fields: Any,
    ) -> Any:
        """Add a new task to the progress display."""
        ...

    def update(
        self,
        task_id: Any,
        *,
        total: float | None = None,
        completed: float | None = None,
        advance: float | None = None,
        description: str | None = None,
        visible: bool | None = None,
        refresh: bool = False,
        **fields: Any,
    ) -> None:
        """Update progress for a task."""
        ...

    def start(self) -> None:
        """Start the progress display."""
        ...

    def stop(self) -> None:
        """Stop the progress display."""
        ...


# Configuration types
class ChromaDBConfigDict(TypedDict):
    """ChromaDB configuration dictionary."""

    host: str
    port: int
    default_size: int
    default_overlap: int


class ChunkingConfigDict(TypedDict):
    """Chunking configuration dictionary."""

    chunk_size: int
    overlap: int
    method: str
    respect_boundaries: bool


class AppConfigDict(TypedDict):
    """Application configuration dictionary."""

    chromadb: ChromaDBConfigDict
    chunking: ChunkingConfigDict


# ChromaDB related protocols
@runtime_checkable
class ChromaCollectionProtocol(Protocol):
    """Protocol for ChromaDB collection objects."""

    # Optional attributes for compatibility with mock objects
    name: str
    metadata: dict[str, Any]

    def add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Add documents to the collection."""
        ...

    def query(
        self,
        query_texts: list[str],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        """Query the collection."""
        ...

    def get(
        self,
        ids: list[str] | None = None,
        where: dict[str, Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get documents from the collection."""
        ...

    def count(self) -> int:
        """Get the count of documents in the collection."""
        ...

    def delete(self, ids: list[str] | None = None) -> None:
        """Delete documents from the collection."""
        ...


@runtime_checkable
class ChromaClientProtocol(Protocol):
    """Protocol for ChromaDB client objects."""

    def get_collection(self, name: str) -> ChromaCollectionProtocol:
        """Get an existing collection."""
        ...

    def create_collection(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> ChromaCollectionProtocol:
        """Create a new collection."""
        ...

    def get_or_create_collection(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> ChromaCollectionProtocol:
        """Get or create a collection."""
        ...

    def list_collections(self) -> list[Any]:
        """List all collections."""
        ...

    def delete_collection(self, name: str) -> None:
        """Delete a collection."""
        ...

    def heartbeat(self) -> int:
        """Check connection heartbeat."""
        ...


# Document processing types
ProcessorConfigType = dict[str, Any] | object
ConfigType = dict[str, Any] | object
MetadataDict = dict[str, Any]
QueryResult = dict[str, Any]
SearchResults = dict[str, Any]

# File path types
InputPathType = str | Path
PathList = list[Path]

# CLI result types
CLIResultType = dict[str, Any]
TableDisplayType = dict[str, Any]

# Validation result types
ValidationResult = tuple[bool, str | None]
