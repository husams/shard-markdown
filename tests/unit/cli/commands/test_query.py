"""Simple tests for query command."""

import pytest
from click.testing import CliRunner

from shard_markdown.cli.commands.query import query


class TestQueryCommandSimple:
    """Simple test cases for query command."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    def test_query_search_requires_collection(self, runner):
        """Test that search command requires collection parameter."""
        result = runner.invoke(query, ["search", "test query"])
        assert result.exit_code == 2
        assert "Missing option '--collection'" in result.output

    def test_query_search_requires_query_text(self, runner):
        """Test that search command requires query text."""
        result = runner.invoke(query, ["search", "--collection", "test"])
        assert result.exit_code == 2
        assert "Missing argument" in result.output

    def test_query_search_help(self, runner):
        """Test that search command help works."""
        result = runner.invoke(query, ["search", "--help"])
        assert result.exit_code == 0
        assert "QUERY_TEXT" in result.output
        assert "--collection" in result.output

    def test_query_group_help(self, runner):
        """Test that query group help works."""
        result = runner.invoke(query, ["--help"])
        assert result.exit_code == 0
        assert "search" in result.output
