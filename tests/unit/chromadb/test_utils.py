"""Tests for ChromaDB utility functions."""

import socket
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from shard_markdown.chromadb.utils import (
    check_socket_connectivity,
    prepare_include_list,
)
from shard_markdown.utils import ensure_directory_exists


class TestEnsureDirectoryExists:
    """Test the ensure_directory_exists utility function."""

    def test_creates_missing_directory(self):
        """Test that missing directories are created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use a non-existent subdirectory
            test_path = Path(temp_dir) / "new_dir" / "sub_dir"

            # Ensure it doesn't exist
            assert not test_path.exists()

            # Call the function
            ensure_directory_exists(test_path)

            # Verify directory was created
            assert test_path.exists()
            assert test_path.is_dir()

    def test_handles_existing_directory(self):
        """Test that existing directories are handled gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir)

            # Directory already exists
            assert test_path.exists()

            # This should work without error
            ensure_directory_exists(test_path)

            # Directory should still exist
            assert test_path.exists()
            assert test_path.is_dir()

    def test_accepts_string_path(self):
        """Test that string paths are handled correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path_str = str(Path(temp_dir) / "string_dir")

            # Ensure it doesn't exist
            assert not Path(test_path_str).exists()

            # Call with string path
            ensure_directory_exists(test_path_str)

            # Verify directory was created
            assert Path(test_path_str).exists()
            assert Path(test_path_str).is_dir()

    def test_creates_parent_directories(self):
        """Test that parent directories are created when needed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Deep nested path
            test_path = Path(temp_dir) / "parent" / "child" / "grandchild"

            # Ensure none of the path exists
            assert not test_path.parent.parent.exists()

            # Call the function
            ensure_directory_exists(test_path)

            # Verify all directories were created
            assert test_path.exists()
            assert test_path.is_dir()
            assert test_path.parent.exists()
            assert test_path.parent.parent.exists()

    def test_handles_permission_errors_gracefully(self):
        """Test that permission errors are handled appropriately."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "restricted"

            # Mock mkdir to raise a permission error
            with patch.object(
                Path, "mkdir", side_effect=PermissionError("Access denied")
            ):
                # This should raise the permission error
                try:
                    ensure_directory_exists(test_path)
                    raise AssertionError("Expected PermissionError to be raised")
                except PermissionError:
                    pass  # Expected behavior


class TestPrepareIncludeList:
    """Test the prepare_include_list utility function."""

    def test_default_base_items(self):
        """Test that default base items are used when none provided."""
        result = prepare_include_list(include_metadata=False)
        assert result == ["documents"]

    def test_custom_base_items(self):
        """Test that custom base items are used when provided."""
        custom_items = ["embeddings", "documents"]
        result = prepare_include_list(include_metadata=False, base_items=custom_items)
        assert result == ["embeddings", "documents"]

    def test_include_metadata_only(self):
        """Test including metadata without distances."""
        result = prepare_include_list(include_metadata=True)
        assert set(result) == {"documents", "metadatas"}

    def test_include_distances_only(self):
        """Test including distances without metadata."""
        result = prepare_include_list(include_metadata=False, include_distances=True)
        assert set(result) == {"documents", "distances"}

    def test_include_both_metadata_and_distances(self):
        """Test including both metadata and distances."""
        result = prepare_include_list(include_metadata=True, include_distances=True)
        assert set(result) == {"documents", "metadatas", "distances"}

    def test_preserve_base_items_order(self):
        """Test that base items order is preserved."""
        custom_items = ["embeddings", "documents", "ids"]
        result = prepare_include_list(
            include_metadata=True, include_distances=True, base_items=custom_items
        )
        # Should start with custom items in order
        assert result[:3] == ["embeddings", "documents", "ids"]
        # Should contain all expected items
        assert set(result) == {
            "embeddings",
            "documents",
            "ids",
            "distances",
            "metadatas",
        }

    def test_empty_base_items(self):
        """Test behavior with empty base items list."""
        result = prepare_include_list(include_metadata=True, base_items=[])
        assert set(result) == {"metadatas"}

    def test_duplicates_not_added(self):
        """Test that duplicates are not added when already in base items."""
        # Include metadatas in base items
        custom_items = ["documents", "metadatas"]
        result = prepare_include_list(include_metadata=True, base_items=custom_items)
        # Should not duplicate metadatas
        assert result.count("metadatas") == 1
        assert set(result) == {"documents", "metadatas"}


class TestCheckSocketConnectivity:
    """Test the check_socket_connectivity utility function."""

    def test_successful_connection(self):
        """Test successful socket connection."""
        with patch("socket.socket") as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.return_value = 0  # Success
            mock_socket_class.return_value = mock_socket

            result = check_socket_connectivity("localhost", 8000)

            assert result is True
            mock_socket.settimeout.assert_called_once_with(2.0)
            mock_socket.connect_ex.assert_called_once_with(("localhost", 8000))
            mock_socket.close.assert_called_once()

    def test_failed_connection(self):
        """Test failed socket connection."""
        with patch("socket.socket") as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.return_value = 1  # Connection refused
            mock_socket_class.return_value = mock_socket

            result = check_socket_connectivity("localhost", 8000)

            assert result is False
            mock_socket.close.assert_called_once()

    def test_connection_with_custom_timeout(self):
        """Test socket connection with custom timeout."""
        with patch("socket.socket") as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.return_value = 0
            mock_socket_class.return_value = mock_socket

            check_socket_connectivity("localhost", 8000, timeout=5.0)

            mock_socket.settimeout.assert_called_once_with(5.0)

    def test_socket_exception_handling(self):
        """Test that socket exceptions are handled gracefully."""
        with patch("socket.socket") as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.side_effect = OSError("Network error")
            mock_socket_class.return_value = mock_socket

            result = check_socket_connectivity("localhost", 8000)

            assert result is False
            mock_socket.close.assert_called_once()

    def test_timeout_exception_handling(self):
        """Test that timeout exceptions are handled gracefully."""
        with patch("socket.socket") as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.side_effect = TimeoutError("Connection timeout")
            mock_socket_class.return_value = mock_socket

            result = check_socket_connectivity("localhost", 8000)

            assert result is False
            mock_socket.close.assert_called_once()

    def test_gaierror_exception_handling(self):
        """Test that socket.gaierror exceptions are handled gracefully."""
        with patch("socket.socket") as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.side_effect = socket.gaierror(
                "Name resolution failed"
            )
            mock_socket_class.return_value = mock_socket

            result = check_socket_connectivity("invalid-host", 8000)

            assert result is False
            mock_socket.close.assert_called_once()

    def test_socket_creation_failure(self):
        """Test handling of socket creation failure."""
        with patch("socket.socket", side_effect=OSError("Socket creation failed")):
            result = check_socket_connectivity("localhost", 8000)
            assert result is False

    def test_socket_cleanup_on_exception(self):
        """Test that socket is properly closed even when exception occurs."""
        with patch("socket.socket") as mock_socket_class:
            mock_socket = Mock()
            mock_socket.settimeout.side_effect = OSError("Timeout setting failed")
            mock_socket_class.return_value = mock_socket

            result = check_socket_connectivity("localhost", 8000)

            assert result is False
            mock_socket.close.assert_called_once()
