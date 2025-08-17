"""Tests for query command."""

import json
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from shard_markdown.cli.main import cli


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


@patch("shard_markdown.cli.utils.get_connected_chromadb_client")
class TestQueryCommand:
    """Test cases for the 'query' command."""

    def test_search_success_table(
        self, mock_get_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test successful search with table output."""
        mock_get_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "distances": [[0.1]],
            "metadatas": [[{"source": "test.md"}]],
        }

        result = runner.invoke(
            cli, ["query", "search", "test", "-c", "test_collection"]
        )

        assert result.exit_code == 0
        assert "Searching for: 'test'" in result.output
        assert "Search Results" in result.output
        assert "Found 1 document(s)" in result.output

    def test_search_success_json(
        self, mock_get_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test successful search with JSON output."""
        mock_get_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "distances": [[0.1]],
            "metadatas": [[{"source": "test.md"}]],
        }

        result = runner.invoke(
            cli, ["query", "search", "test", "-c", "test_collection", "-f", "json"]
        )

        assert result.exit_code == 0
        assert "Searching for: 'test'" in result.output

        # Extract JSON from output
        output_lines = result.output.split("\n")
        json_start = -1
        for i, line in enumerate(output_lines):
            if line.startswith("["):
                json_start = i
                break

        assert json_start >= 0
        json_lines = []
        for i in range(json_start, len(output_lines)):
            if output_lines[i].startswith("Found"):
                break
            json_lines.append(output_lines[i])

        json_text = "\n".join(json_lines)
        data = json.loads(json_text)
        assert len(data) == 1
        assert data[0]["id"] == "id1"

    def test_search_success_yaml(
        self, mock_get_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test successful search with YAML output."""
        mock_get_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "distances": [[0.1]],
            "metadatas": [[{"source": "test.md"}]],
        }

        result = runner.invoke(
            cli, ["query", "search", "test", "-c", "test_collection", "-f", "yaml"]
        )

        assert result.exit_code == 0
        assert "Searching for: 'test'" in result.output
        # YAML output should be present
        assert "id1" in result.output

    def test_search_no_results(
        self, mock_get_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test search with no results."""
        mock_get_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "distances": [[]],
            "metadatas": [[]],
        }

        result = runner.invoke(
            cli, ["query", "search", "test", "-c", "test_collection"]
        )

        assert result.exit_code == 0
        assert "No documents found" in result.output

    def test_search_collection_not_found(
        self, mock_get_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test search with collection not found."""
        mock_get_client.return_value = mock_chromadb_client
        mock_chromadb_client.get_collection.side_effect = ValueError("Not found")

        result = runner.invoke(cli, ["query", "search", "test", "-c", "nonexistent"])

        assert result.exit_code == 1
        assert "Collection 'nonexistent' not found" in result.output

    def test_get_success_table(
        self, mock_get_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test successful document retrieval with table output."""
        mock_get_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.get.return_value = {
            "ids": ["id1"],
            "documents": ["document content"],
            "metadatas": [{"source": "test.md"}],
        }

        result = runner.invoke(cli, ["query", "get", "id1", "-c", "test_collection"])

        assert result.exit_code == 0
        assert "Retrieving document 'id1'" in result.output
        assert "Document: id1" in result.output
        assert "Content:" in result.output
        assert "document content" in result.output

    def test_get_document_not_found(
        self, mock_get_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test getting document that doesn't exist."""
        mock_get_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.get.return_value = {
            "ids": [],
            "documents": [],
            "metadatas": [],
        }

        result = runner.invoke(
            cli, ["query", "get", "nonexistent", "-c", "test_collection"]
        )

        assert result.exit_code == 0
        assert "Document 'nonexistent' not found" in result.output
