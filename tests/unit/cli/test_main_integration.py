"""Integration tests for CLI using real components instead of mocks."""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from shard_markdown.cli.main import shard_md


class TestMainCLIIntegration:
    """Integration tests for CLI with real components."""

    @pytest.fixture
    def cli_runner(self):
        """Click CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def sample_markdown_content(self):
        """Sample markdown content for testing."""
        return """# Test Document

This is a test document for CLI integration testing.

## Section 1

This section contains some important information that should be chunked properly.

- Item 1: Description of first item
- Item 2: Description of second item
- Item 3: Description of third item

## Section 2

Another section with different content.

```python
def example_function():
    return "This is a code block"
```

## Section 3

Final section with concluding remarks.

This document demonstrates real chunking behavior without mocks."""

    @pytest.fixture
    def temp_markdown_file(self, sample_markdown_content):
        """Create a temporary markdown file with real content."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as tmp_file:
            tmp_file.write(sample_markdown_content)
            tmp_path = Path(tmp_file.name)

        yield tmp_path

        # Cleanup
        tmp_path.unlink(missing_ok=True)

    @pytest.mark.unit
    def test_basic_processing_real_components(self, cli_runner, temp_markdown_file):
        """Test basic file processing with real parser and chunker."""
        result = cli_runner.invoke(shard_md, [str(temp_markdown_file)])

        assert result.exit_code == 0
        assert "Total chunks:" in result.output
        # Verify real chunking occurred
        assert (
            "Successfully processed" in result.output
            or "chunks" in result.output.lower()
        )

    @pytest.mark.unit
    def test_processing_with_structure_strategy(self, cli_runner, temp_markdown_file):
        """Test processing with structure strategy using real components."""
        result = cli_runner.invoke(
            shard_md,
            [str(temp_markdown_file), "--strategy", "structure", "--size", "200"],
        )

        assert result.exit_code == 0
        # The output should mention chunks were created
        assert "chunk" in result.output.lower()

    @pytest.mark.unit
    def test_processing_with_fixed_strategy(self, cli_runner, temp_markdown_file):
        """Test processing with fixed strategy using real components."""
        result = cli_runner.invoke(
            shard_md,
            [
                str(temp_markdown_file),
                "--strategy",
                "fixed",
                "--size",
                "100",
                "--overlap",
                "20",
            ],
        )

        assert result.exit_code == 0
        # Should create multiple chunks with this small size
        assert "chunk" in result.output.lower()

    @pytest.mark.unit
    def test_output_format(self, cli_runner, temp_markdown_file):
        """Test output format with real components."""
        result = cli_runner.invoke(shard_md, [str(temp_markdown_file)])

        assert result.exit_code == 0
        # Should show processing results table
        assert (
            "processing results" in result.output.lower()
            or "total chunks" in result.output.lower()
        )

    @pytest.mark.unit
    def test_verbose_output(self, cli_runner, temp_markdown_file):
        """Test verbose output with real components."""
        result = cli_runner.invoke(shard_md, [str(temp_markdown_file), "--verbose"])

        assert result.exit_code == 0
        # Verbose should show more details
        output_lines = result.output.split("\n")
        assert len(output_lines) > 3  # More output in verbose mode

    @pytest.mark.unit
    def test_nonexistent_file_real(self, cli_runner):
        """Test handling of non-existent file."""
        result = cli_runner.invoke(shard_md, ["nonexistent_file.md"])

        assert result.exit_code != 0
        assert (
            "not found" in result.output.lower()
            or "does not exist" in result.output.lower()
        )

    @pytest.mark.unit
    def test_empty_file_handling(self, cli_runner):
        """Test processing empty file with real components."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as tmp_file:
            tmp_file.write("")  # Empty file
            tmp_path = Path(tmp_file.name)

        try:
            result = cli_runner.invoke(shard_md, [str(tmp_path)])

            # Should handle empty file gracefully
            assert result.exit_code == 0 or "empty" in result.output.lower()
        finally:
            tmp_path.unlink(missing_ok=True)

    @pytest.mark.unit
    def test_single_file_processing(self, cli_runner, sample_markdown_content):
        """Test processing a single file with real components."""
        # Create a temporary file with more content
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as tmp_file:
            tmp_file.write(f"# Main Document\n\n{sample_markdown_content}")
            tmp_path = Path(tmp_file.name)

        try:
            result = cli_runner.invoke(shard_md, [str(tmp_path)])

            assert result.exit_code == 0
            # Should process the file successfully
            assert (
                "chunks" in result.output.lower()
                or "processed" in result.output.lower()
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    @pytest.mark.unit
    def test_help_and_version_commands(self, cli_runner):
        """Test help and version commands (no mocking needed)."""
        # Test help
        help_result = cli_runner.invoke(shard_md, ["--help"])
        assert help_result.exit_code == 0
        assert "chunk markdown documents" in help_result.output.lower()

        # Test version
        version_result = cli_runner.invoke(shard_md, ["--version"])
        assert version_result.exit_code == 0
        assert "shard-md" in version_result.output.lower()


class TestCLIArgumentValidation:
    """Test CLI argument parsing and validation only."""

    @pytest.fixture
    def cli_runner(self):
        """Click CLI test runner."""
        return CliRunner()

    @pytest.mark.unit
    def test_very_small_chunk_size(self, cli_runner):
        """Test very small chunk size handling."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            tmp_path = Path(f.name)
            f.write(b"# Test Document\n\n" + b"Word " * 100)  # Add content

        try:
            result = cli_runner.invoke(
                shard_md,
                [str(tmp_path), "--size", "10"],  # Very small size
            )

            # Should either work with many chunks or warn about small size
            assert result.exit_code == 0
            # Should create multiple chunks with such a small size
            assert "chunks" in result.output.lower()
        finally:
            tmp_path.unlink(missing_ok=True)

    @pytest.mark.unit
    def test_invalid_strategy(self, cli_runner):
        """Test invalid chunking strategy."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            tmp_path = Path(f.name)
            f.write(b"# Test")

        try:
            result = cli_runner.invoke(
                shard_md, [str(tmp_path), "--strategy", "invalid_strategy"]
            )

            # Should reject invalid strategy
            assert result.exit_code != 0
        finally:
            tmp_path.unlink(missing_ok=True)

    @pytest.mark.unit
    def test_large_overlap_handling(self, cli_runner):
        """Test handling of overlap larger than chunk size."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            tmp_path = Path(f.name)
            f.write(b"# Test\n\n" + b"Content " * 50)  # Add more content

        try:
            # Test overlap larger than chunk size - should still work but may warn
            result = cli_runner.invoke(
                shard_md, [str(tmp_path), "--size", "100", "--overlap", "200"]
            )

            # CLI should handle this gracefully (either work or error clearly)
            assert result.exit_code == 0 or "error" in result.output.lower()
        finally:
            tmp_path.unlink(missing_ok=True)
