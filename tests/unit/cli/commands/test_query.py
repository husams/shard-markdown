"""Tests for query command."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from shard_markdown.cli.commands.query import query
from shard_markdown.utils.errors import ChromaDBError


class TestQueryCommand:
    """Test cases for query command."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_client(self):
        """Create mock ChromaDB client."""
        with patch("shard_markdown.cli.commands.query.ChromaDBClient") as mock:
            client = Mock()
            client.connect.return_value = True
            client.list_collections.return_value = ["test_collection"]
            mock.return_value = client
            yield client

    @pytest.fixture
    def mock_operations(self):
        """Create mock ChromaDB operations."""
        with patch("shard_markdown.cli.commands.query.ChromaDBOperations") as mock:
            ops = Mock()
            mock.return_value = ops
            yield ops

    def test_query_no_collections(self, runner):
        """Test query with no collections."""
        with patch("shard_markdown.cli.commands.query.ChromaDBClient") as mock_client:
            client = Mock()
            client.connect.return_value = True
            client.list_collections.return_value = []
            mock_client.return_value = client

            result = runner.invoke(query, ["search query"])
            assert result.exit_code == 1
            assert "No collections found" in result.output

    def test_query_success(self, runner, mock_client, mock_operations):
        """Test successful query."""
        mock_operations.query_collection.return_value = {
            "collection_name": "test_collection",
            "query": "search query",
            "total_results": 2,
            "similarity_threshold": 0.0,
            "results": [
                {
                    "id": "doc1",
                    "content": "result 1",
                    "similarity_score": 0.9,
                    "metadata": {"title": "Doc 1"},
                },
                {
                    "id": "doc2",
                    "content": "result 2",
                    "similarity_score": 0.8,
                    "metadata": {"title": "Doc 2"},
                },
            ],
        }

        result = runner.invoke(
            query,
            ["search query", "--collection", "test_collection", "--limit", "5"],
        )

        assert result.exit_code == 0
        assert "Found 2 results" in result.output
        mock_operations.query_collection.assert_called_once()

    def test_query_no_results(self, runner, mock_client, mock_operations):
        """Test query with no results."""
        mock_operations.query_collection.return_value = {
            "collection_name": "test_collection",
            "query": "search query",
            "total_results": 0,
            "similarity_threshold": 0.0,
            "results": [],
        }

        result = runner.invoke(
            query,
            ["search query", "--collection", "test_collection"],
        )

        assert result.exit_code == 0
        assert "No results found" in result.output

    def test_query_with_threshold(self, runner, mock_client, mock_operations):
        """Test query with similarity threshold."""
        mock_operations.query_collection.return_value = {
            "collection_name": "test_collection",
            "query": "search query",
            "total_results": 1,
            "similarity_threshold": 0.7,
            "results": [
                {
                    "id": "doc1",
                    "content": "result 1",
                    "similarity_score": 0.85,
                    "metadata": {},
                },
            ],
        }

        result = runner.invoke(
            query,
            ["search query", "--collection", "test_collection", "--threshold", "0.7"],
        )

        assert result.exit_code == 0
        mock_operations.query_collection.assert_called_with(
            collection_name="test_collection",
            query_text="search query",
            limit=10,
            similarity_threshold=0.7,
            include_metadata=True,
        )

    def test_query_collection_not_found(self, runner, mock_client, mock_operations):
        """Test query with non-existent collection."""
        mock_client.list_collections.return_value = ["other_collection"]

        result = runner.invoke(
            query,
            ["search query", "--collection", "nonexistent"],
        )

        assert result.exit_code == 1
        assert "Collection 'nonexistent' not found" in result.output

    def test_query_chromadb_error(self, runner, mock_client, mock_operations):
        """Test query with ChromaDB error."""
        mock_operations.query_collection.side_effect = ChromaDBError(
            "Connection failed",
            error_code=1400,
        )

        result = runner.invoke(
            query,
            ["search query", "--collection", "test_collection"],
        )

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_query_json_output(self, runner, mock_client, mock_operations):
        """Test query with JSON output format."""
        mock_operations.query_collection.return_value = {
            "collection_name": "test_collection",
            "query": "search query",
            "total_results": 1,
            "similarity_threshold": 0.0,
            "results": [
                {
                    "id": "doc1",
                    "content": "result content",
                    "similarity_score": 0.95,
                    "metadata": {"key": "value"},
                },
            ],
        }

        result = runner.invoke(
            query,
            ["search query", "--collection", "test_collection", "--format", "json"],
        )

        assert result.exit_code == 0
        # JSON output should contain the result
        assert "doc1" in result.output
        assert "0.95" in result.output

    def test_query_multiple_collections(self, runner):
        """Test query prompts for collection selection."""
        with patch("shard_markdown.cli.commands.query.ChromaDBClient") as mock_client:
            client = Mock()
            client.connect.return_value = True
            client.list_collections.return_value = ["col1", "col2", "col3"]
            mock_client.return_value = client

            # Simulate user selecting first collection
            with patch("shard_markdown.cli.commands.query.click.prompt") as mock_prompt:
                mock_prompt.return_value = 1

                with patch(
                    "shard_markdown.cli.commands.query.ChromaDBOperations"
                ) as mock_ops_class:
                    ops = Mock()
                    ops.query_collection.return_value = {
                        "collection_name": "col1",
                        "query": "search",
                        "total_results": 0,
                        "results": [],
                    }
                    mock_ops_class.return_value = ops

                    result = runner.invoke(query, ["search"])

                    assert result.exit_code == 0
                    mock_prompt.assert_called_once()

    def test_query_connection_failed(self, runner):
        """Test query when connection fails."""
        with patch("shard_markdown.cli.commands.query.ChromaDBClient") as mock_client:
            client = Mock()
            client.connect.return_value = False
            mock_client.return_value = client

            result = runner.invoke(query, ["search query"])

            assert result.exit_code == 1
            assert "Failed to connect" in result.output
