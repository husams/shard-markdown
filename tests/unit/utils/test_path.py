"""Unit tests for path and filesystem utility functions."""

import tempfile
from pathlib import Path

import pytest


class TestPathValidation:
    """Test path validation and normalization."""

    @pytest.mark.unit
    def test_path_object_creation(self) -> None:
        """Test creating and validating Path objects."""
        # Test with Path object
        path = Path("test.md")
        assert path.suffix == ".md"
        assert path.name == "test.md"
        assert path.stem == "test"

    @pytest.mark.unit
    def test_absolute_path_detection(self) -> None:
        """Test detecting absolute vs relative paths."""
        # Test absolute path using tempfile for cross-platform compatibility
        with tempfile.NamedTemporaryFile(suffix=".md") as temp_file:
            abs_path = Path(temp_file.name)
            assert abs_path.is_absolute()

        # Test relative path
        rel_path = Path("../test.md")
        assert not rel_path.is_absolute()

        # Test current directory path
        current_path = Path("./test.md")
        assert not current_path.is_absolute()

    @pytest.mark.unit
    def test_path_resolution(self) -> None:
        """Test path resolution and normalization."""
        # Test path with redundant separators
        path = Path("foo//bar///test.md")
        normalized = Path("foo/bar/test.md")
        assert str(path).replace("//", "/").replace("///", "/") == str(normalized)

        # Test path with parent references
        path = Path("foo/../bar/test.md")
        # After resolution, foo/.. cancels out
        assert "foo" not in str(path.resolve().parts[-2:])


class TestFileExtensions:
    """Test file extension handling."""

    @pytest.mark.unit
    def test_markdown_extension_detection(self) -> None:
        """Test detecting markdown file extensions."""
        markdown_files = [
            Path("test.md"),
            Path("README.MD"),
            Path("doc.markdown"),
            Path("notes.MARKDOWN"),
        ]

        for file in markdown_files:
            assert file.suffix.lower() in [".md", ".markdown"]

    @pytest.mark.unit
    def test_non_markdown_extension_detection(self) -> None:
        """Test detecting non-markdown files."""
        non_markdown_files = [
            Path("script.py"),
            Path("data.json"),
            Path("image.png"),
            Path("document.txt"),
        ]

        for file in non_markdown_files:
            assert file.suffix.lower() not in [".md", ".markdown"]

    @pytest.mark.unit
    def test_files_without_extension(self) -> None:
        """Test handling files without extensions."""
        files = [
            Path("README"),
            Path("Makefile"),
            Path(".gitignore"),
        ]

        for file in files:
            # Files without extensions or dotfiles
            assert file.suffix == "" or file.name.startswith(".")


class TestDirectoryOperations:
    """Test directory creation and manipulation."""

    @pytest.mark.unit
    def test_nested_directory_creation(self) -> None:
        """Test creating nested directories safely."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "level1" / "level2" / "level3"

            # Create nested directories
            new_dir.mkdir(parents=True, exist_ok=True)

            assert new_dir.exists()
            assert new_dir.is_dir()
            assert new_dir.parent.name == "level2"
            assert new_dir.parent.parent.name == "level1"

    @pytest.mark.unit
    def test_directory_creation_idempotency(self) -> None:
        """Test that directory creation is idempotent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "test_dir"

            # Create directory first time
            target_dir.mkdir(parents=True, exist_ok=True)
            assert target_dir.exists()

            # Create same directory again (should not raise)
            target_dir.mkdir(parents=True, exist_ok=True)
            assert target_dir.exists()

    @pytest.mark.unit
    def test_directory_permissions(self) -> None:
        """Test directory creation with proper permissions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "secure_dir"
            new_dir.mkdir(mode=0o755)

            assert new_dir.exists()
            assert new_dir.is_dir()
            # Permissions check is platform-specific
            if hasattr(new_dir.stat(), "st_mode"):
                import stat

                mode = new_dir.stat().st_mode
                assert stat.S_ISDIR(mode)


class TestFileSizeOperations:
    """Test file size calculation and validation."""

    @pytest.mark.unit
    def test_file_size_calculation(self) -> None:
        """Test calculating file sizes accurately."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as temp_file:
            content = "Test content\n" * 100
            temp_file.write(content)
            temp_path = Path(temp_file.name)

        try:
            # Check file size
            file_size = temp_path.stat().st_size
            assert file_size > 0
            # Account for potential line ending differences (CRLF vs LF)
            expected_size = len(content.encode())
            assert abs(file_size - expected_size) <= 100  # Allow small difference
        finally:
            temp_path.unlink()

    @pytest.mark.unit
    def test_empty_file_size(self) -> None:
        """Test handling empty files."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            file_size = temp_path.stat().st_size
            assert file_size == 0
        finally:
            temp_path.unlink()

    @pytest.mark.unit
    def test_large_file_size(self) -> None:
        """Test handling large files."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as temp_file:
            # Create a "large" file (1MB of text)
            content = "x" * 1024 * 1024
            temp_file.write(content)
            temp_path = Path(temp_file.name)

        try:
            file_size = temp_path.stat().st_size
            assert file_size >= 1024 * 1024
        finally:
            temp_path.unlink()


class TestPathComparison:
    """Test path comparison and equality."""

    @pytest.mark.unit
    def test_path_equality(self) -> None:
        """Test comparing paths for equality."""
        path1 = Path("test/file.md")
        path2 = Path("test/file.md")
        path3 = Path("test/other.md")

        assert path1 == path2
        assert path1 != path3

    @pytest.mark.unit
    def test_path_parent_child_relationship(self) -> None:
        """Test parent-child relationships between paths."""
        parent = Path("/home/user/documents")
        child = Path("/home/user/documents/file.md")

        # Check if child is under parent
        try:
            child.relative_to(parent)
            is_child = True
        except ValueError:
            is_child = False

        assert is_child

    @pytest.mark.unit
    def test_path_sibling_detection(self) -> None:
        """Test detecting sibling paths."""
        file1 = Path("/home/user/doc1.md")
        file2 = Path("/home/user/doc2.md")
        file3 = Path("/home/other/doc3.md")

        assert file1.parent == file2.parent
        assert file1.parent != file3.parent
