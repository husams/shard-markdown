"""Tests for query command."""

import json
from unittest.mock import Mock, patch

import pytest
import yaml
from click.testing import CliRunner

from shard_markdown.cli.main import cli
from shard_markdown.utils.errors import ChromaDBError


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


@patch("shard_markdown.cli.commands.query.create_chromadb_client")
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

        result = runner.invoke(
            cli, ["query", "search", "test", "-c", "test_collection"]
        )

        assert result.exit_code == 0
        assert "Searching for: 'test'" in result.output
        assert "Found 1 document(s)" in result.output
        assert "id1" in result.output

    def test_search_success_json(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test successful search with JSON output."""
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
            ["query", "search", "test", "-c", "test_collection", "--format", "json"],
        )

        assert result.exit_code == 0
        # Extract the JSON part from the output
        start = result.output.find("[")
        end = result.output.rfind("]") + 1
        json_output = result.output[start:end]
        output_data = json.loads(json_output)
        assert len(output_data) == 1
        assert output_data[0]["id"] == "id1"

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
            ["query", "search", "test", "-c", "test_collection", "--format", "yaml"],
        )

        assert result.exit_code == 0
        # Extract the YAML part from the output
        lines = result.output.splitlines()
        yaml_lines = []
        in_yaml = False
        for line in lines:
            # The YAML output starts with a list item
            if line.strip().startswith("-"):
                in_yaml = True
            if in_yaml:
                # The "Found" message indicates the end of the YAML output
                if line.startswith("Found "):
                    break
                yaml_lines.append(line)

        yaml_output = "\n".join(yaml_lines)
        output_data = yaml.safe_load(yaml_output)

        assert output_data is not None
        assert len(output_data) == 1
        assert output_data[0]["id"] == "id1"

    def test_search_no_results(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test search with no results found."""
        mock_create_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.query.return_value = {"ids": [[]]}

        result = runner.invoke(
            cli, ["query", "search", "test", "-c", "test_collection"]
        )

        assert result.exit_code == 0
        assert "No documents found" in result.output

    def test_search_collection_not_found(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test search in a non-existent collection."""
        mock_create_client.return_value = mock_chromadb_client
        mock_chromadb_client.get_collection.side_effect = ValueError(
            "Collection not found"
        )

        result = runner.invoke(
            cli, ["query", "search", "test", "-c", "test_collection"]
        )

        assert result.exit_code == 1
        assert "Collection 'test_collection' not found" in result.output

    def test_get_success_table(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test successful get with table output."""
        mock_create_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.get.return_value = {
            "ids": ["id1"],
            "documents": ["doc content"],
            "metadatas": [{"source": "test.md"}],
        }

        result = runner.invoke(
            cli, ["query", "get", "id1", "-c", "test_collection"]
        )

        assert result.exit_code == 0
        assert "Retrieving document 'id1'" in result.output
        assert "Document retrieved successfully" in result.output
        assert "doc content" in result.output

    def test_get_document_not_found(
        self, mock_create_client: Mock, runner: CliRunner, mock_chromadb_client: Mock
    ) -> None:
        """Test get for a non-existent document."""
        mock_create_client.return_value = mock_chromadb_client
        mock_collection = Mock()
        mock_chromadb_client.get_collection.return_value = mock_collection
        mock_collection.get.return_value = {"ids": []}

        result = runner.invoke(
            cli, ["query", "get", "id1", "-c", "test_collection"]
        )

        assert result.exit_code == 0
        assert "Document 'id1' not found" in result.output
