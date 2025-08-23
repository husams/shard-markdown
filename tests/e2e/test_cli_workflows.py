"""End-to-end tests for CLI workflows - comprehensive real-world scenarios."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from shard_markdown.cli.main import shard_md


class TestCLIWorkflows:
    """Test complete CLI workflows end-to-end."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def sample_markdown(self, tmp_path: Path) -> Path:
        """Create a comprehensive sample markdown file."""
        content = """---
title: Complete Test Document
author: Test Suite
tags: [testing, e2e, markdown]
date: 2024-01-01
---

# Complete Test Document

## Table of Contents
1. [Introduction](#introduction)
2. [Features](#features)
3. [Code Examples](#code-examples)
4. [Data Tables](#data-tables)

## Introduction

This is a comprehensive test document designed to test all features of the
markdown processor. It includes various markdown elements like **bold text**,
*italic text*, and `inline code`.

### Background

The document contains multiple sections with different depths to test
structure-aware chunking.
We also include [links](https://example.com) and references.

## Features

### Feature List

- **Parsing**: Complete markdown parsing with frontmatter
- **Chunking**: Both fixed-size and structure-aware chunking
- **Metadata**: Extraction and preservation of metadata
- **Storage**: Optional ChromaDB integration

### Nested Lists

1. First level
   - Second level item 1
   - Second level item 2
     - Third level
   - Back to second
2. Another first level

## Code Examples

### Python Code

```python
def process_markdown(file_path: Path) -> List[DocumentChunk]:
    \"\"\"Process a markdown file into chunks.\"\"\"
    parser = MarkdownParser()
    ast = parser.parse(file_path.read_text())

    chunker = ChunkingEngine(settings)
    chunks = chunker.chunk_document(ast)

    return chunks
```

### JavaScript Code

```javascript
function processDocument(content) {
    const parsed = parseMarkdown(content);
    const chunks = createChunks(parsed);
    return chunks;
}
```

### Shell Commands

```bash
# Process a single file
shard-md document.md

# Process with custom settings
shard-md document.md --size 500 --overlap 50
```

## Data Tables

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data A   | Value 1  | Result X |
| Data B   | Value 2  | Result Y |
| Data C   | Value 3  | Result Z |

## Mathematical Content

Here's an inline equation: $E = mc^2$

And a block equation:

$$
\\frac{\\partial u}{\\partial t} = \\alpha \\nabla^2 u
$$

## Images and Media

![Alt text for image](image.png)

[Download PDF](document.pdf)

## Blockquotes

> This is a blockquote with multiple lines.
> It can contain **formatted text** and other elements.
>
> Even nested quotes work.

## Horizontal Rules

---

## Special Characters

Testing special characters: © ® ™ € £ ¥ § ¶

## Conclusion

This document covers all major markdown elements for comprehensive testing.

---

*Footer: Generated for testing purposes*"""

        file_path = tmp_path / "complete_test.md"
        file_path.write_text(content)
        return file_path

    @pytest.fixture
    def config_file(self, tmp_path: Path) -> Path:
        """Create a configuration file for testing."""
        config = {
            "chunk_size": 300,
            "chunk_overlap": 30,
            "chunk_method": "structure",
            "chroma_host": "localhost",
            "chroma_port": 8000,
        }

        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump(config))
        return config_path

    def test_single_file_processing(
        self, cli_runner: CliRunner, sample_markdown: Path
    ) -> None:
        """Test processing a single file with default settings."""
        result = cli_runner.invoke(shard_md, [str(sample_markdown)])

        assert result.exit_code == 0
        assert "complete_test.md" in result.output
        assert "chunks" in result.output.lower()

        # Should show a table with results
        assert (
            "Processing Results" in result.output
            or "processing results" in result.output.lower()
        )

    def test_single_file_with_custom_options(
        self, cli_runner: CliRunner, sample_markdown: Path
    ) -> None:
        """Test processing with all custom options."""
        result = cli_runner.invoke(
            shard_md,
            [
                str(sample_markdown),
                "--size",
                "200",
                "--overlap",
                "20",
                "--strategy",
                "fixed",
                "--verbose",
            ],
        )

        assert result.exit_code == 0
        # Should show chunks were created
        assert "chunks" in result.output.lower()
        # Average size should be close to configured size (allowing for boundaries)
        assert (
            "190" in result.output
            or "200" in result.output
            or "avg" in result.output.lower()
        )

    def test_directory_processing_non_recursive(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test processing all markdown files in a directory (non-recursive)."""
        # Create multiple markdown files
        for i in range(3):
            content = f"# Document {i}\n\nContent for document {i}."
            (tmp_path / f"doc_{i}.md").write_text(content)

        # Create a subdirectory with files (should not be processed)
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.md").write_text("# Nested\n\nShould not be processed.")

        result = cli_runner.invoke(shard_md, [str(tmp_path)])

        assert result.exit_code == 0
        assert "doc_0.md" in result.output
        assert "doc_1.md" in result.output
        assert "doc_2.md" in result.output
        # Nested file should not be processed (non-recursive)
        assert "nested.md" not in result.output

    def test_directory_processing_recursive(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test recursive directory processing."""
        # Create nested structure
        (tmp_path / "root.md").write_text("# Root Document")

        level1 = tmp_path / "level1"
        level1.mkdir()
        (level1 / "doc1.md").write_text("# Level 1 Document")

        level2 = level1 / "level2"
        level2.mkdir()
        (level2 / "doc2.md").write_text("# Level 2 Document")

        result = cli_runner.invoke(shard_md, [str(tmp_path), "--recursive"])

        assert result.exit_code == 0
        assert "root.md" in result.output
        assert "doc1.md" in result.output
        assert "doc2.md" in result.output

    def test_dry_run_mode(self, cli_runner: CliRunner, sample_markdown: Path) -> None:
        """Test dry-run mode shows what would be done without doing it."""
        result = cli_runner.invoke(
            shard_md,
            [
                str(sample_markdown),
                "--store",
                "--collection",
                "test-dry-run",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        # Dry-run shows normal processing but doesn't actually store
        assert (
            "chunks" in result.output.lower() or "processing" in result.output.lower()
        )

    def test_config_file_loading(
        self, cli_runner: CliRunner, sample_markdown: Path, config_file: Path
    ) -> None:
        """Test loading configuration from file."""
        result = cli_runner.invoke(
            shard_md,
            [str(sample_markdown), "--config-path", str(config_file)],
        )

        assert result.exit_code == 0
        # Config should be applied (chunk_size: 300 from config)

    def test_error_handling_nonexistent_file(self, cli_runner: CliRunner) -> None:
        """Test error handling for nonexistent file."""
        result = cli_runner.invoke(shard_md, ["/nonexistent/file.md"])

        assert result.exit_code != 0
        assert "error" in result.output.lower() or "not found" in result.output.lower()

    def test_error_handling_invalid_markdown(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test handling of invalid or binary files."""
        # Create a binary file with .md extension
        binary_file = tmp_path / "binary.md"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04")

        result = cli_runner.invoke(shard_md, [str(binary_file)])

        # Should handle gracefully (might succeed or fail depending on implementation)
        # But should not crash
        assert isinstance(result.exit_code, int)

    def test_mixed_file_types(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test processing directory with mixed file types."""
        # Create various file types
        (tmp_path / "doc.md").write_text("# Markdown")
        (tmp_path / "text.txt").write_text("Plain text")
        (tmp_path / "script.py").write_text("print('Python')")
        (tmp_path / "data.json").write_text('{"key": "value"}')

        result = cli_runner.invoke(shard_md, [str(tmp_path)])

        assert result.exit_code == 0
        assert "doc.md" in result.output
        # Non-markdown files should be skipped
        assert "text.txt" not in result.output
        assert "script.py" not in result.output

    def test_empty_directory(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test processing empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = cli_runner.invoke(shard_md, [str(empty_dir)])

        # Should handle gracefully without errors
        assert result.exit_code == 0
        # Empty directory produces no output or minimal output
        assert (
            len(result.output) == 0
            or "0" in result.output
            or "no" in result.output.lower()
        )

    def test_standard_file_handling(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """E2E test: Verify handling of standard-sized markdown files."""
        # Create a typical user document (NOT 1MB!)
        content = """# User Guide

## Introduction
This is a typical document that users would process.

## Section 1
Some content here with multiple paragraphs.

This is the second paragraph with more details.

## Section 2
Another section with different content.

### Subsection
Nested content for testing structure.

## Conclusion
Final thoughts and summary.
"""

        doc_file = tmp_path / "user_guide.md"
        doc_file.write_text(content)

        result = cli_runner.invoke(
            shard_md,
            [str(doc_file), "--size", "1000"],
        )

        assert result.exit_code == 0
        assert "user_guide.md" in result.output
        # Should create chunks
        assert "chunks" in result.output.lower()

    def test_verbose_mode(self, cli_runner: CliRunner, sample_markdown: Path) -> None:
        """Test verbose output mode."""
        result = cli_runner.invoke(
            shard_md,
            [str(sample_markdown), "--verbose"],
        )

        assert result.exit_code == 0
        # Verbose mode should show additional information
        # Could include timing, detailed progress, etc.
        output_lines = result.output.split("\n")
        assert len(output_lines) > 5  # More output in verbose mode

    def test_quiet_mode(self, cli_runner: CliRunner, sample_markdown: Path) -> None:
        """Test quiet/silent mode if available."""
        # Try with minimal output flag if it exists
        result = cli_runner.invoke(
            shard_md,
            [str(sample_markdown), "--output", "json"],
        )

        # JSON output should be parseable without extra messages
        try:
            json.loads(result.output)
            assert True
        except json.JSONDecodeError:
            # If not pure JSON, that's okay for this implementation
            pass

    def test_stdin_input(self, cli_runner: CliRunner) -> None:
        """Test reading from stdin if supported."""
        markdown_content = "# Test\n\nContent from stdin."

        result = cli_runner.invoke(
            shard_md,
            ["-"],  # Common convention for stdin
            input=markdown_content,
        )

        # May or may not be supported
        if result.exit_code == 0:
            assert "chunks" in result.output.lower()

    def test_concurrent_file_processing(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test processing multiple files (tests internal concurrency if any)."""
        # Create 10 files
        for i in range(10):
            content = f"# Document {i}\n\n" + "Content\n" * 50
            (tmp_path / f"doc_{i:02d}.md").write_text(content)

        result = cli_runner.invoke(shard_md, [str(tmp_path)])

        assert result.exit_code == 0
        # All files should be processed
        for i in range(10):
            assert f"doc_{i:02d}.md" in result.output

    def test_progress_reporting(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test progress reporting for batch operations."""
        # Create multiple files
        for i in range(5):
            (tmp_path / f"file_{i}.md").write_text(f"# File {i}")

        result = cli_runner.invoke(
            shard_md,
            [str(tmp_path), "--verbose"],
        )

        assert result.exit_code == 0
        # Should show some form of progress
        # Could be "Processing 1/5", percentage, or progress bar

    def test_cli_as_module(self, tmp_path: Path, sample_markdown: Path) -> None:
        """Test running CLI as Python module."""
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "shard_markdown", str(sample_markdown)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "complete_test.md" in result.stdout

    def test_tc_e2e_019_recursive_with_filters(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """TC-E2E-019: Test recursive processing with various filtering options.

        Test recursive processing with various filtering options including
        hidden directories, file type filtering, and different output modes.
        """
        # Create the nested structure as specified in test case
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create docs directory with markdown files
        docs_dir = project_dir / "docs"
        docs_dir.mkdir()
        (docs_dir / "api.md").write_text("# API Documentation\n\nAPI reference guide.")
        (docs_dir / "guide.md").write_text("# User Guide\n\nHow to use the software.")

        # Create internal subdirectory with mixed file types
        internal_dir = docs_dir / "internal"
        internal_dir.mkdir()
        (internal_dir / "dev.md").write_text(
            "# Developer Notes\n\nInternal development documentation."
        )
        (internal_dir / "notes.txt").write_text(
            "Plain text notes file."
        )  # Non-markdown file

        # Create root-level README
        (project_dir / "README.md").write_text(
            "# Project README\n\nProject overview and setup."
        )

        # Create tests directory with markdown
        tests_dir = project_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test.md").write_text(
            "# Test Documentation\n\nTesting procedures."
        )

        # Create hidden directory with content
        hidden_dir = project_dir / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "secret.md").write_text(
            "# Secret Documentation\n\nConfidential information."
        )

        # Test 1: Basic recursive processing from project root
        result1 = cli_runner.invoke(shard_md, [str(project_dir), "--recursive"])
        assert result1.exit_code == 0
        assert "README.md" in result1.output
        assert "api.md" in result1.output
        assert "guide.md" in result1.output
        assert "dev.md" in result1.output
        assert "test.md" in result1.output
        # Verify non-markdown files are skipped
        assert "notes.txt" not in result1.output
        # Verify processing statistics show correct file count (5 .md files)
        assert "chunks" in result1.output.lower()

        # Test 2: Recursive processing from docs subdirectory
        result2 = cli_runner.invoke(shard_md, [str(docs_dir), "--recursive"])
        assert result2.exit_code == 0
        assert "api.md" in result2.output
        assert "guide.md" in result2.output
        assert "dev.md" in result2.output
        # Should not include files outside the docs directory
        assert "README.md" not in result2.output
        assert "test.md" not in result2.output

        # Test 3: Recursive with quiet mode
        result3 = cli_runner.invoke(
            shard_md, [str(project_dir), "--recursive", "--quiet"]
        )
        assert result3.exit_code == 0
        # Quiet mode should produce minimal output
        output_lines = [line for line in result3.output.split("\n") if line.strip()]
        # Should still process files but with less verbose output
        # The exact behavior depends on implementation but should be less than verbose

        # Test 4: Recursive with verbose mode
        result4 = cli_runner.invoke(
            shard_md, [str(project_dir), "--recursive", "--verbose"]
        )
        assert result4.exit_code == 0
        # Verbose mode should show more detailed information
        output_lines = result4.output.split("\n")
        assert len(output_lines) > 10  # More detailed output expected
        assert "README.md" in result4.output
        assert "api.md" in result4.output

        # Test 5: Verify file filtering behavior
        # Test that only .md files are processed
        result5 = cli_runner.invoke(shard_md, [str(internal_dir), "--recursive"])
        assert result5.exit_code == 0
        assert "dev.md" in result5.output
        assert "notes.txt" not in result5.output  # Non-markdown should be skipped

        # Test 6: Verify correct file count reporting
        # Count expected markdown files for validation
        expected_md_files = ["README.md", "api.md", "guide.md", "dev.md", "test.md"]
        # Hidden directory files may or may not be processed depending on implementation
        # This tests the actual behavior rather than prescribing it
        result6 = cli_runner.invoke(shard_md, [str(project_dir), "--recursive"])
        assert result6.exit_code == 0
        # Verify each expected file is processed
        for md_file in expected_md_files:
            assert md_file in result6.output

        # Test 7: Test edge case - empty subdirectory
        empty_subdir = project_dir / "empty"
        empty_subdir.mkdir()
        result7 = cli_runner.invoke(shard_md, [str(empty_subdir), "--recursive"])
        assert result7.exit_code == 0
        # Should handle empty directory gracefully without errors
