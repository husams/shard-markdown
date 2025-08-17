"""Tests for ChromaDB decorators."""

from unittest.mock import Mock

import pytest

from shard_markdown.chromadb.decorators import require_connection
from shard_markdown.utils.errors import ChromaDBError


class TestRequireConnectionDecorator:
    """Test the require_connection decorator."""

    def test_decorator_allows_valid_connection(self):
        """Test decorator allows execution when connection is valid."""
        # Create a mock client with valid connection
        mock_client = Mock()
        mock_client._connection_validated = True
        mock_client.client = Mock()

        # Create a mock object with the client
        mock_self = Mock()
        mock_self.client = mock_client

        @require_connection
        def test_method(self):
            return "success"

        # Should execute successfully
        result = test_method(mock_self)
        assert result == "success"

    def test_decorator_raises_error_when_not_validated(self):
        """Test decorator raises ChromaDBError when connection not validated."""
        # Create a mock client with invalid connection
        mock_client = Mock()
        mock_client._connection_validated = False
        mock_client.client = Mock()

        # Create a mock object with the client
        mock_self = Mock()
        mock_self.client = mock_client

        @require_connection
        def test_method(self):
            return "success"

        # Should raise ChromaDBError
        with pytest.raises(ChromaDBError) as exc_info:
            test_method(mock_self)

        assert exc_info.value.error_code == 1400
        assert "ChromaDB connection not established" in str(exc_info.value)

    def test_decorator_raises_error_when_client_none(self):
        """Test decorator raises ChromaDBError when client is None."""
        # Create a mock client with None client
        mock_client = Mock()
        mock_client._connection_validated = True
        mock_client.client = None

        # Create a mock object with the client
        mock_self = Mock()
        mock_self.client = mock_client

        @require_connection
        def test_method(self):
            return "success"

        # Should raise ChromaDBError
        with pytest.raises(ChromaDBError) as exc_info:
            test_method(mock_self)

        assert exc_info.value.error_code == 1400
        assert "ChromaDB connection not established" in str(exc_info.value)

    def test_decorator_preserves_context_in_error(self):
        """Test decorator preserves operation context in error."""
        # Create a mock client with invalid connection
        mock_client = Mock()
        mock_client._connection_validated = False
        mock_client.client = None

        # Create a mock object with the client
        mock_self = Mock()
        mock_self.client = mock_client

        @require_connection
        def query_collection(self, collection_name="test_collection"):
            return "success"

        # Should raise ChromaDBError with context
        with pytest.raises(ChromaDBError) as exc_info:
            query_collection(mock_self)

        assert exc_info.value.error_code == 1400
        assert exc_info.value.context["operation"] == "query_collection"

    def test_decorator_with_different_operation_names(self):
        """Test decorator works with different operation names."""
        mock_client = Mock()
        mock_client._connection_validated = False
        mock_client.client = None

        mock_self = Mock()
        mock_self.client = mock_client

        @require_connection
        def get_document(self):
            return "success"

        @require_connection
        def list_documents(self):
            return "success"

        @require_connection
        def delete_documents(self):
            return "success"

        # Test each operation gets proper context
        for method in [get_document, list_documents, delete_documents]:
            with pytest.raises(ChromaDBError) as exc_info:
                method(mock_self)

            assert exc_info.value.context["operation"] == method.__name__

    def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves original function metadata."""

        @require_connection
        def test_method(self):
            """Test method docstring."""
            return "success"

        assert test_method.__name__ == "test_method"
        assert test_method.__doc__ == "Test method docstring."
