"""Shared test fixtures and configuration."""

import logging
import os
import socket
import tempfile
import time
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest


# Constants for testing
DEFAULT_PORT = 8000


@pytest.fixture
def mock_chromadb_client() -> Mock:
    """Create a mock ChromaDB client for testing."""
    # Create a mock client with all the required methods
    mock_client = Mock()
    mock_client.connect.return_value = True
    mock_client._connection_validated = True
    mock_client.client = Mock()

    # Mock collection
    mock_collection = Mock()
    mock_collection.add.return_value = None
    mock_collection.query.return_value = {
        "ids": [["doc1", "doc2"]],
        "documents": [["Document 1 content", "Document 2 content"]],
        "metadatas": [[{"source": "test1.md"}, {"source": "test2.md"}]],
        "distances": [[0.1, 0.2]],
    }
    mock_collection.get.return_value = {
        "ids": ["doc1"],
        "documents": ["Document content"],
        "metadatas": [{"source": "test.md"}],
    }
    mock_collection.count.return_value = 10
    mock_collection.delete.return_value = None

    # Mock client methods
    mock_client.client.get_collection.return_value = mock_collection
    mock_client.client.create_collection.return_value = mock_collection
    mock_client.client.get_or_create_collection.return_value = mock_collection
    mock_client.client.list_collections.return_value = [mock_collection]
    mock_client.client.delete_collection.return_value = None
    mock_client.client.heartbeat.return_value = 1

    # Mock client-level methods
    mock_client.get_collection.return_value = mock_collection
    mock_client.get_or_create_collection.return_value = mock_collection
    mock_client.list_collections.return_value = [
        {"name": "test_collection", "metadata": {}, "count": 10}
    ]
    mock_client.delete_collection.return_value = True

    # Mock bulk_insert
    mock_client.bulk_insert.return_value = Mock(
        success=True, chunks_inserted=5, processing_time=0.1, collection_name="test"
    )

    return mock_client


@pytest.fixture
def sample_markdown_content() -> str:
    """Sample markdown content for testing."""
    return """# Main Title

This is the introduction paragraph with some content.

## First Section

This section contains important information about the topic.

### Subsection 1.1

Details about the first subsection.

## Second Section

More content in the second section.

### Subsection 2.1

Information about subsection 2.1.

### Subsection 2.2

Details for subsection 2.2.

## Conclusion

Final thoughts and summary.
"""


@pytest.fixture
def sample_markdown_file(tmp_path: Path, sample_markdown_content: str) -> Path:
    """Create a temporary markdown file for testing."""
    md_file = tmp_path / "test_document.md"
    md_file.write_text(sample_markdown_content, encoding="utf-8")
    return md_file


@pytest.fixture
def multiple_markdown_files(tmp_path: Path) -> list[Path]:
    """Create multiple temporary markdown files for testing."""
    files = []

    contents = [
        "# Document 1\n\nContent of document 1.\n\n## Section A\n\nMore content.",
        "# Document 2\n\nContent of document 2.\n\n## Section B\n\nAdditional info.",
        "# Document 3\n\nContent of document 3.\n\n## Section C\n\nFinal details.",
    ]

    for i, content in enumerate(contents, 1):
        md_file = tmp_path / f"document_{i}.md"
        md_file.write_text(content, encoding="utf-8")
        files.append(md_file)

    return files


@pytest.fixture
def sample_config_dict() -> dict[str, Any]:
    """Sample configuration dictionary for testing."""
    return {
        "chromadb": {
            "host": "localhost",
            "port": 8000,
            "default_size": 1000,
            "default_overlap": 200,
        },
        "chunking": {
            "chunk_size": 1000,
            "overlap": 200,
            "method": "structure",
            "respect_boundaries": True,
        },
    }


@pytest.fixture
def temp_config_file(tmp_path: Path, sample_config_dict: dict[str, Any]) -> Path:
    """Create a temporary configuration file for testing."""
    import yaml

    config_file = tmp_path / "test_config.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(sample_config_dict, f)
    return config_file


@pytest.fixture
def mock_document_chunk() -> Mock:
    """Create a mock document chunk for testing."""
    chunk = Mock()
    chunk.id = "chunk_1"
    chunk.content = "This is sample chunk content for testing purposes."
    chunk.metadata = {
        "source": "test.md",
        "chunk_index": 0,
        "section": "Introduction",
        "created_at": datetime.now().isoformat(),
    }
    chunk.embedding = [0.1, 0.2, 0.3] * 128  # 384-dimensional mock embedding
    return chunk


@pytest.fixture
def mock_processing_result() -> Mock:
    """Create a mock processing result for testing."""
    result = Mock()
    result.success = True
    result.file_path = Path("test.md")
    result.chunks_created = 5
    result.processing_time = 0.5
    result.metadata = {"total_size": 1024, "encoding": "utf-8"}
    result.error = None
    return result


@pytest.fixture
def mock_insert_result() -> Mock:
    """Create a mock insert result for testing."""
    result = Mock()
    result.success = True
    result.chunks_inserted = 5
    result.processing_time = 0.1
    result.collection_name = "test_collection"
    result.error = None
    return result


@pytest.fixture
def temp_directory() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def nested_markdown_structure(tmp_path: Path) -> Path:
    """Create a nested directory structure with markdown files."""
    # Create nested directories
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    api_dir = docs_dir / "api"
    api_dir.mkdir()

    guides_dir = docs_dir / "guides"
    guides_dir.mkdir()

    # Create markdown files
    (docs_dir / "README.md").write_text("# Main Documentation\n\nOverview content.")
    (docs_dir / "intro.md").write_text("# Introduction\n\nIntroductory content.")

    (api_dir / "endpoints.md").write_text("# API Endpoints\n\nAPI documentation.")
    (api_dir / "auth.md").write_text("# Authentication\n\nAuth details.")

    (guides_dir / "quickstart.md").write_text("# Quick Start\n\nGetting started.")
    (guides_dir / "advanced.md").write_text("# Advanced Topics\n\nAdvanced content.")

    return docs_dir


def wait_for_chromadb(host: str, port: int, timeout: int = 30) -> bool:
    """Wait for ChromaDB to be available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                if result == 0:
                    return True
        except Exception as e:
            # Log the exception instead of silently passing
            logging.debug(f"Connection attempt failed: {e}")
        time.sleep(1)
    return False


@pytest.fixture(scope="session")
def real_chromadb_client():
    """Create a real ChromaDB client if available (for integration tests)."""
    try:
        # Check if we should use a real ChromaDB instance
        if os.environ.get("CHROMADB_TEST_URL"):
            from urllib.parse import urlparse

            import chromadb

            url = os.environ.get("CHROMADB_TEST_URL")
            parsed = urlparse(url)
            hostname = parsed.hostname
            host = hostname if hostname is not None else "localhost"
            port = int(os.environ.get("CHROMA_PORT", str(DEFAULT_PORT)))

            if wait_for_chromadb(host, port, timeout=60):
                return chromadb.HttpClient(host=host, port=port)
    except ImportError:
        pass

    # Return None if ChromaDB is not available
    return None


@pytest.fixture
def mock_progress() -> Mock:
    """Create a mock progress object for testing."""
    progress = Mock()
    progress.add_task.return_value = "task_1"
    progress.update.return_value = None
    progress.start.return_value = None
    progress.stop.return_value = None
    return progress


class MockChromaDBClientAdapter:
    """Adapter to make MockChromaDBClient compatible with ChromaClientProtocol."""

    def __init__(self, mock_client: Mock) -> None:
        """Initialize the adapter with a mock client."""
        self._mock = mock_client

    def get_collection(self, name: str) -> Any:
        """Get collection."""
        return self._mock.get_collection(name)

    def create_collection(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> Any:
        """Create collection."""
        return self._mock.create_collection(name, metadata=metadata)

    def get_or_create_collection(
        self, name: str, metadata: dict[str, Any] | None = None
    ) -> Any:
        """Get or create collection."""
        return self._mock.get_or_create_collection(name, metadata=metadata)

    def list_collections(self) -> list[Any]:
        """List collections."""
        collections = self._mock.list_collections()
        return collections

    def delete_collection(self, name: str) -> None:
        """Delete collection."""
        self._mock.delete_collection(name)

    def heartbeat(self) -> int:
        """Heartbeat."""
        return self._mock.heartbeat()


class MockCollection:
    """Mock collection that implements ChromaCollectionProtocol."""

    def __init__(self) -> None:
        """Initialize the mock collection."""
        self.name = "test_collection"
        self.metadata = {"test": "metadata"}
        self._documents: dict[str, str] = {}
        self._metadatas: dict[str, dict[str, Any]] = {}

    def add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Add documents."""
        for i, doc_id in enumerate(ids):
            self._documents[doc_id] = documents[i]
            if metadatas and i < len(metadatas):
                self._metadatas[doc_id] = metadatas[i]

    def query(
        self,
        query_texts: list[str],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        """Query documents."""
        return {
            "ids": [["doc1", "doc2"]],
            "documents": [["Document 1", "Document 2"]],
            "metadatas": [[{"source": "test1.md"}, {"source": "test2.md"}]],
            "distances": [[0.1, 0.2]],
        }

    def get(
        self,
        ids: list[str] | None = None,
        where: dict[str, Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get documents."""
        if ids:
            return {
                "ids": ids,
                "documents": [self._documents.get(id_, "") for id_ in ids],
                "metadatas": [self._metadatas.get(id_, {}) for id_ in ids],
            }
        return {
            "ids": list(self._documents.keys()),
            "documents": list(self._documents.values()),
            "metadatas": list(self._metadatas.values()),
        }

    def count(self) -> int:
        """Get document count."""
        return len(self._documents)

    def delete(self, ids: list[str] | None = None) -> None:
        """Delete documents."""
        if ids:
            for doc_id in ids:
                self._documents.pop(doc_id, None)
                self._metadatas.pop(doc_id, None)


class MockChromaDBClient:
    """Mock ChromaDB client that implements ChromaDBClientProtocol."""

    def __init__(self) -> None:
        """Initialize the mock ChromaDB client."""
        self._connection_validated = True
        self.client = MockChromaDBClientAdapter(Mock())
        self._collections: dict[str, MockCollection] = {}

    def connect(self) -> bool:
        """Connect to database."""
        return True

    def get_collection(self, name: str) -> MockCollection:
        """Get collection."""
        if name not in self._collections:
            raise ValueError(f"Collection {name} does not exist")
        return self._collections[name]

    def get_or_create_collection(
        self,
        name: str,
        create_if_missing: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> MockCollection:
        """Get or create collection."""
        if name not in self._collections:
            self._collections[name] = MockCollection()
        return self._collections[name]

    def bulk_insert(self, collection: Any, chunks: list[Any]) -> Any:
        """Bulk insert."""
        return Mock(
            success=True,
            chunks_inserted=len(chunks),
            processing_time=0.1,
            collection_name="test",
        )

    def list_collections(self) -> list[dict[str, Any]]:
        """List collections."""
        return [
            {
                "name": name,
                "metadata": collection.metadata,
                "count": collection.count(),
            }
            for name, collection in self._collections.items()
        ]

    def delete_collection(self, name: str) -> bool:
        """Delete collection."""
        if name in self._collections:
            del self._collections[name]
            return True
        return False
