"""Tests for query command."""

import json
import os
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from shard_markdown.cli.main import cli


@pytest.fixture(autouse=True)
def force_mock_chromadb():
    """Force all tests to use mock ChromaDB."""
    old_value = os.environ.get("SHARD_MD_USE_MOCK_CHROMADB")
    os.environ["SHARD_MD_USE_MOCK_CHROMADB"] = "true"
    yield
    if old_value is None:
        os.environ.pop("SHARD_MD_USE_MOCK_CHROMADB", None)
    else:
        os.environ["SHARD_MD_USE_MOCK_CHROMADB"] = old_value


@pytest.fixture
def runner() -> CliRunner:
    """Fixture for a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_chromadb_client() -> Mock:
    """Fixture for a mocked ChromaDB client."""
    mock_client = Mock()
    mock_client.connect.return_value = True
    return mock_client


@patch("shard_markdown.chromadb.factory._create_mock_client")
class TestQueryCommand:
    """Test cases for the 'query' command."""

    def test_search_success_table(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test successful search with table output."""
        mock_create_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "distances": [[0.1]],
            "metadatas": [[{"source": "test.md"}]],
        }

        result = runner.invoke(cli, ["data", "search", "test", "-c", "test_collection"])

        assert result.exit_code == 0
        assert "Searching for: 'test'" in result.output
        assert "Search Results" in result.output

    def test_search_success_json(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test successful search with JSON output."""
        mock_create_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["doc1", "doc2"]],
            "distances": [[0.1, 0.2]],
            "metadatas": [[{"source": "test.md"}, {"source": "test2.md"}]],
        }

        result = runner.invoke(
            cli,
            ["data", "search", "test", "-c", "test_collection", "--format", "json"],
        )

        assert result.exit_code == 0
        assert "Searching for: 'test'" in result.output

        # Extract JSON from output (everything before the "Found X document(s)" line)
        output_lines = result.output.strip().split("\n")
        json_lines = []
        for line in output_lines:
            if line.startswith("Found"):
                break
            if not line.startswith("Searching for"):
                json_lines.append(line)

        if json_lines:
            json_text = "\n".join(json_lines)
            search_results = json.loads(json_text)
            assert len(search_results) == 2

    def test_search_success_yaml(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test successful search with YAML output."""
        mock_create_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "distances": [[0.1]],
            "metadatas": [[{"source": "test.md"}]],
        }

        result = runner.invoke(
            cli,
            ["data", "search", "test", "-c", "test_collection", "--format", "yaml"],
        )

        assert result.exit_code == 0
        assert "Searching for: 'test'" in result.output

    def test_search_no_results(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test search with no results."""
        mock_create_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "distances": [[]],
        }

        result = runner.invoke(cli, ["data", "search", "test", "-c", "test_collection"])

        assert result.exit_code == 0
        assert "No documents found" in result.output

    def test_get_success_table(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test successful document retrieval with table output."""
        mock_create_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.get.return_value = {
            "ids": ["doc1"],
            "documents": ["Document content"],
            "metadatas": [{"source": "test.md"}],
        }

        result = runner.invoke(
            cli, ["data", "similar", "doc1", "-c", "test_collection"]
        )

        assert result.exit_code == 0
        assert "Finding documents similar to 'doc1'" in result.output
        assert "Document: doc1" in result.output

    def test_get_document_not_found(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test retrieval of non-existent document."""
        mock_create_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}

        result = runner.invoke(
            cli, ["data", "similar", "nonexistent", "-c", "test_collection"]
        )

        assert result.exit_code == 0
        assert "Document 'nonexistent' not found" in result.output

    def test_search_collection_not_found(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test search with non-existent collection."""
        mock_create_client.return_value = mock_chromadb_client
        mock_chromadb_client.get_collection.side_effect = ValueError(
            "Collection not found"
        )

        result = runner.invoke(
            cli, ["data", "search", "test", "-c", "nonexistent_collection"]
        )

        assert result.exit_code == 1
        assert "Collection 'nonexistent_collection' not found" in result.output

    def test_get_collection_not_found(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test get with non-existent collection."""
        mock_create_client.return_value = mock_chromadb_client
        mock_chromadb_client.get_collection.side_effect = ValueError(
            "Collection not found"
        )

        result = runner.invoke(
            cli, ["data", "similar", "doc1", "-c", "nonexistent_collection"]
        )

        assert result.exit_code == 1
        assert "Collection 'nonexistent_collection' not found" in result.output

    def test_search_query_failure(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test search when query operation fails."""
        mock_create_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.query.side_effect = RuntimeError("Query failed")

        result = runner.invoke(cli, ["data", "search", "test", "-c", "test_collection"])

        assert result.exit_code == 1
        assert "Search failed" in result.output

    def test_get_operation_failure(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test get when operation fails."""
        mock_create_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.get.side_effect = RuntimeError("Get operation failed")

        result = runner.invoke(
            cli, ["data", "similar", "doc1", "-c", "test_collection"]
        )

        assert result.exit_code == 1
        assert "Failed to retrieve document" in result.output

    def test_search_with_similarity_threshold(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test search with similarity threshold."""
        mock_create_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["doc1", "doc2"]],
            "distances": [[0.1, 0.8]],  # Second doc should be filtered out
            "metadatas": [[{"source": "test.md"}, {"source": "test2.md"}]],
        }

        result = runner.invoke(
            cli,
            [
                "data",
                "search",
                "test",
                "-c",
                "test_collection",
                "--similarity-threshold",
                "0.5",
            ],
        )

        assert result.exit_code == 0
        assert "Search Results" in result.output

    def test_search_with_limit(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test search with result limit."""
        mock_create_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "distances": [[0.1]],
            "metadatas": [[{"source": "test.md"}]],
        }

        result = runner.invoke(
            cli, ["data", "search", "test", "-c", "test_collection", "--limit", "5"]
        )

        assert result.exit_code == 0
        # Verify that the limit was passed to the query
        mock_collection.query.assert_called_once()
        call_args = mock_collection.query.call_args
        assert call_args[1]["n_results"] == 5

    def test_get_with_json_format(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test document retrieval with JSON format."""
        mock_create_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.get.return_value = {
            "ids": ["doc1"],
            "documents": ["Document content"],
            "metadatas": [{"source": "test.md"}],
        }

        result = runner.invoke(
            cli,
            ["data", "similar", "doc1", "-c", "test_collection", "--format", "json"],
        )

        assert result.exit_code == 0
        assert "Document retrieved successfully" in result.output

    def test_connection_error(
        self, mock_create_client: Mock, runner: CliRunner
    ) -> None:
        """Test handling of connection errors."""
        failed_client = Mock()
        failed_client.connect.return_value = False
        mock_create_client.return_value = failed_client

        result = runner.invoke(cli, ["data", "search", "test", "-c", "test_collection"])

        assert result.exit_code == 1
        assert "Failed to connect to ChromaDB" in result.output
