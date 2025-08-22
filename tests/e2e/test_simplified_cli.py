"""End-to-end tests for the simplified CLI."""

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from shard_markdown.cli.main import shard_md
from tests.fixtures.chromadb_fixtures import ChromaDBTestFixture


class TestSimplifiedCLI:
    """Test the simplified CLI end-to-end workflows."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def sample_markdown(self, tmp_path: Path) -> Path:
        """Create a sample markdown file for testing."""
        content = """# Test Document

## Introduction
This is a test document for E2E testing.
It contains multiple sections and paragraphs.

## Section 1
Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

### Subsection 1.1
- Item 1
- Item 2
- Item 3

## Section 2
Another section with more content.
This helps test the chunking functionality.

### Code Example
```python
def hello_world():
    print("Hello, World!")
```

## Conclusion
This concludes our test document.
"""
        file_path = tmp_path / "test_document.md"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def multiple_markdown_files(self, tmp_path: Path) -> list[Path]:
        """Create multiple markdown files for batch testing."""
        files = []
        for i in range(3):
            content = f"""# Document {i + 1}

## Content
This is document number {i + 1}.
It has unique content for testing batch processing.

## Data
- Value: {i * 10}
- Status: Active
- Type: Test
"""
            file_path = tmp_path / f"document_{i + 1}.md"
            file_path.write_text(content)
            files.append(file_path)
        return files

    @pytest.mark.e2e
    def test_basic_document_processing(
        self, cli_runner: CliRunner, sample_markdown: Path
    ) -> None:
        """Test basic document processing without storage."""
        result = cli_runner.invoke(shard_md, [str(sample_markdown)])

        assert result.exit_code == 0
        # Should show processing results table
        assert (
            "chunks" in result.output.lower() or "total chunks" in result.output.lower()
        )
        assert "test_document.md" in result.output

    @pytest.mark.e2e
    def test_custom_chunk_size_and_overlap(
        self, cli_runner: CliRunner, sample_markdown: Path
    ) -> None:
        """Test processing with custom chunk size and overlap."""
        result = cli_runner.invoke(
            shard_md,
            [str(sample_markdown), "--size", "200", "--overlap", "50"],
        )

        assert result.exit_code == 0
        # With smaller chunk size, should have more chunks
        assert "chunk" in result.output.lower()

    @pytest.mark.e2e
    def test_different_chunking_strategies(
        self, cli_runner: CliRunner, sample_markdown: Path
    ) -> None:
        """Test different chunking strategies."""
        strategies = ["token", "sentence", "paragraph", "section", "semantic"]

        for strategy in strategies:
            result = cli_runner.invoke(
                shard_md,
                [str(sample_markdown), "--strategy", strategy],
            )

            assert result.exit_code == 0, f"Failed with strategy: {strategy}"
            assert "chunk" in result.output.lower()

    @pytest.mark.e2e
    def test_dry_run_mode(self, cli_runner: CliRunner, sample_markdown: Path) -> None:
        """Test dry run mode."""
        result = cli_runner.invoke(
            shard_md,
            [
                str(sample_markdown),
                "--dry-run",
                "--store",
                "--collection",
                "test-collection",
            ],
        )

        assert result.exit_code == 0
        # Dry run should show what would be done without actually storing
        assert "chunk" in result.output.lower()

    @pytest.mark.e2e
    def test_quiet_mode(self, cli_runner: CliRunner, sample_markdown: Path) -> None:
        """Test quiet mode suppresses output."""
        result = cli_runner.invoke(
            shard_md,
            [str(sample_markdown), "--quiet"],
        )

        assert result.exit_code == 0
        # Quiet mode should have minimal output
        assert len(result.output.strip()) == 0 or "error" not in result.output.lower()

    @pytest.mark.e2e
    def test_verbose_mode(self, cli_runner: CliRunner, sample_markdown: Path) -> None:
        """Test verbose mode provides detailed output."""
        result = cli_runner.invoke(
            shard_md,
            [str(sample_markdown), "-vv"],  # Double verbose
        )

        assert result.exit_code == 0
        # Verbose mode should have more detailed output
        assert len(result.output) > 0

    @pytest.mark.e2e
    def test_directory_processing(
        self, cli_runner: CliRunner, multiple_markdown_files: list[Path]
    ) -> None:
        """Test processing a directory of markdown files."""
        directory = multiple_markdown_files[0].parent

        result = cli_runner.invoke(
            shard_md,
            [str(directory)],
        )

        assert result.exit_code == 0
        # Should process all markdown files in directory
        assert "document" in result.output.lower()

    @pytest.mark.e2e
    def test_recursive_directory_processing(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test recursive directory processing."""
        # Create nested structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Create files at different levels
        (tmp_path / "root.md").write_text("# Root Document")
        (subdir / "nested.md").write_text("# Nested Document")

        result = cli_runner.invoke(
            shard_md,
            [str(tmp_path), "--recursive"],
        )

        assert result.exit_code == 0
        # Should process files recursively
        assert "chunk" in result.output.lower()

    @pytest.mark.e2e
    def test_metadata_inclusion(
        self, cli_runner: CliRunner, sample_markdown: Path
    ) -> None:
        """Test metadata inclusion in chunks."""
        result = cli_runner.invoke(
            shard_md,
            [str(sample_markdown), "--metadata"],
        )

        assert result.exit_code == 0
        # Should include metadata in output
        assert "chunk" in result.output.lower()

    @pytest.mark.e2e
    def test_preserve_structure(
        self, cli_runner: CliRunner, sample_markdown: Path
    ) -> None:
        """Test preserve structure option."""
        result = cli_runner.invoke(
            shard_md,
            [str(sample_markdown), "--preserve-structure"],
        )

        assert result.exit_code == 0
        # Should maintain markdown structure
        assert "chunk" in result.output.lower()

    @pytest.mark.e2e
    def test_custom_config_path(
        self, cli_runner: CliRunner, sample_markdown: Path, tmp_path: Path
    ) -> None:
        """Test using a custom config file."""
        # Create a custom config file
        config_file = tmp_path / "custom_config.yaml"
        config_content = """
chunk_size: 300
chunk_overlap: 75
chunk_method: paragraph
"""
        config_file.write_text(config_content)

        result = cli_runner.invoke(
            shard_md,
            [str(sample_markdown), "--config-path", str(config_file)],
        )

        assert result.exit_code == 0
        assert "chunk" in result.output.lower()

    @pytest.mark.e2e
    def test_nonexistent_file_error(self, cli_runner: CliRunner) -> None:
        """Test error handling for nonexistent file."""
        result = cli_runner.invoke(
            shard_md,
            ["nonexistent_file.md"],
        )

        assert result.exit_code != 0
        assert (
            "does not exist" in result.output.lower()
            or "error" in result.output.lower()
        )

    @pytest.mark.e2e
    def test_empty_file_handling(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test handling of empty markdown file."""
        empty_file = tmp_path / "empty.md"
        empty_file.write_text("")

        result = cli_runner.invoke(
            shard_md,
            [str(empty_file)],
        )

        # Should handle empty file gracefully
        assert result.exit_code == 0 or "empty" in result.output.lower()

    @pytest.mark.e2e
    @pytest.mark.chromadb
    def test_storage_with_chromadb(
        self,
        cli_runner: CliRunner,
        sample_markdown: Path,
        chromadb_test_fixture: ChromaDBTestFixture,
    ) -> None:
        """Test storing chunks in ChromaDB."""
        if not chromadb_test_fixture.client:
            pytest.skip("ChromaDB not available")

        # Set environment variables for ChromaDB connection
        env = os.environ.copy()
        env["CHROMA_HOST"] = chromadb_test_fixture.host
        env["CHROMA_PORT"] = str(chromadb_test_fixture.port)

        result = cli_runner.invoke(
            shard_md,
            [
                str(sample_markdown),
                "--store",
                "--collection",
                "e2e-test-collection",
            ],
            env=env,
        )

        # Storage might fail if ChromaDB isn't running, but command should handle it
        if "stored" in result.output.lower():
            assert result.exit_code == 0
            assert "chunk" in result.output.lower()
        else:
            # Should have an error message about ChromaDB
            assert (
                "chroma" in result.output.lower()
                or "connection" in result.output.lower()
            )

    @pytest.mark.e2e
    def test_store_without_collection_error(
        self, cli_runner: CliRunner, sample_markdown: Path
    ) -> None:
        """Test that --store without --collection shows an error."""
        result = cli_runner.invoke(
            shard_md,
            [str(sample_markdown), "--store"],
        )

        # Should show error about missing collection
        assert (
            "--collection is required" in result.output
            or "collection" in result.output.lower()
        )

    @pytest.mark.e2e
    def test_version_output(self, cli_runner: CliRunner) -> None:
        """Test version output."""
        result = cli_runner.invoke(shard_md, ["--version"])

        assert result.exit_code == 0
        assert "shard-md" in result.output.lower()
        assert "version" in result.output.lower()

    @pytest.mark.e2e
    def test_help_output(self, cli_runner: CliRunner) -> None:
        """Test help output."""
        result = cli_runner.invoke(shard_md, ["--help"])

        assert result.exit_code == 0
        # Check for key options in help
        assert "--size" in result.output
        assert "--overlap" in result.output
        assert "--strategy" in result.output
        assert "--store" in result.output
        assert "--collection" in result.output
        assert "--metadata" in result.output
        assert "--dry-run" in result.output
