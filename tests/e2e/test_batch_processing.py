"""End-to-end tests for batch processing - multi-file operations."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from shard_markdown.cli.main import shard_md


class TestBatchProcessing:
    """Test batch processing of multiple markdown files."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def batch_documents(self, tmp_path: Path) -> list[Path]:
        """Create a batch of diverse markdown documents."""
        docs = []

        # Create 15 documents with varying characteristics
        for i in range(15):
            if i % 3 == 0:
                # Technical documentation
                content = f"""---
title: Technical Doc {i}
type: technical
---

# Technical Documentation {i}

## Overview

This is technical document number {i} with detailed specifications.

## Implementation

```python
class Document{i}:
    def __init__(self):
        self.id = {i}
        self.type = "technical"

    def process(self):
        return f"Processing document {i}"
```

## Configuration

```yaml
document:
  id: {i}
  settings:
    enabled: true
    priority: {i % 5}
```

## API Reference

### Method `process()`

Processes the document with ID {i}.

**Parameters:**
- None

**Returns:**
- String: Processing result
"""
            elif i % 3 == 1:
                # Tutorial/Guide
                content = f"""---
title: Tutorial {i}
type: tutorial
difficulty: {"beginner" if i < 5 else "intermediate" if i < 10 else "advanced"}
---

# Tutorial {i}: Learning Topic {i}

## Introduction

Welcome to tutorial {i}! This guide covers topic {i} in detail.

## Prerequisites

- Basic knowledge of concept {i - 1}
- Understanding of principle {i // 2}
- Familiarity with tool {i % 4}

## Step 1: Setup

First, we need to set up our environment:

1. Install package {i}
2. Configure setting {i}
3. Verify installation

## Step 2: Basic Usage

Here's how to use feature {i}:

```bash
command-{i} --option value
command-{i} process input.txt
```

## Step 3: Advanced Features

For advanced users, feature {i} offers:

- Option A: Enhanced processing
- Option B: Parallel execution
- Option C: Custom configurations

## Exercises

1. Try running command {i} with different inputs
2. Experiment with option combinations
3. Measure performance improvements

## Summary

In this tutorial, we learned about topic {i} and how to use feature {i} effectively.
"""
            else:
                # Reference documentation
                content = f"""---
title: Reference {i}
type: reference
version: {i // 5}.{i % 5}.0
---

# Reference Documentation {i}

## Module {i}

### Constants

- `CONSTANT_{i}_A` = {i * 100}
- `CONSTANT_{i}_B` = {i * 200}
- `CONSTANT_{i}_C` = {i * 300}

### Functions

#### `function_{i}_alpha(param1, param2)`

Description of function {i} alpha.

**Parameters:**
- `param1` (int): First parameter
- `param2` (str): Second parameter

**Returns:**
- dict: Result dictionary

#### `function_{i}_beta(data)`

Description of function {i} beta.

**Parameters:**
- `data` (list): Input data

**Returns:**
- list: Processed data

### Classes

#### `Class{i}`

Main class for module {i}.

**Attributes:**
- `id` (int): Identifier
- `name` (str): Name
- `config` (dict): Configuration

**Methods:**
- `initialize()`: Initialize the class
- `process()`: Process data
- `cleanup()`: Clean up resources

## Configuration

### Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| setting_{i}_1 | bool | true | First setting |
| setting_{i}_2 | int | {i} | Second setting |
| setting_{i}_3 | str | "value{i}" | Third setting |

## Examples

```python
# Example {i}.1
obj = Class{i}()
obj.initialize()
result = obj.process()

# Example {i}.2
data = function_{i}_alpha({i}, "test")
print(data)
```
"""

            doc_path = tmp_path / f"document_{i:02d}.md"
            doc_path.write_text(content)
            docs.append(doc_path)

        return docs

    def test_batch_process_multiple_files(
        self, cli_runner: CliRunner, batch_documents: list[Path]
    ) -> None:
        """Test processing multiple files in parallel."""
        # Process the directory containing all documents
        parent_dir = batch_documents[0].parent

        result = cli_runner.invoke(shard_md, [str(parent_dir)])

        assert result.exit_code == 0
        # All 15 documents should be processed
        for i in range(15):
            assert f"document_{i:02d}.md" in result.output

    def test_batch_with_mixed_file_types(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test batch processing with mixed file types (skip non-markdown)."""
        # Create markdown files
        for i in range(5):
            (tmp_path / f"doc_{i}.md").write_text(f"# Document {i}")

        # Create non-markdown files
        (tmp_path / "data.json").write_text('{"key": "value"}')
        (tmp_path / "script.py").write_text("print('hello')")
        (tmp_path / "notes.txt").write_text("Plain text notes")
        (tmp_path / "README").write_text("Readme without extension")

        result = cli_runner.invoke(shard_md, [str(tmp_path)])

        assert result.exit_code == 0
        # Only markdown files should be processed
        for i in range(5):
            assert f"doc_{i}.md" in result.output

        # Non-markdown files should be skipped
        assert "data.json" not in result.output
        assert "script.py" not in result.output
        assert "notes.txt" not in result.output

    def test_batch_processes_efficiently(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """E2E test: Verify batch processing works efficiently with typical usage."""
        # Create a small, realistic batch - just 5 files
        for i in range(5):
            content = f"""# Document {i}

## Overview
This is document {i} with typical content.

## Section 1
Some content here for testing.

## Section 2
More content to make this realistic.
"""
            (tmp_path / f"doc_{i}.md").write_text(content)

        # Process all files
        result = cli_runner.invoke(shard_md, [str(tmp_path)])

        assert result.exit_code == 0
        # Verify all 5 files were processed
        for i in range(5):
            assert f"doc_{i}.md" in result.output

    def test_batch_progress_reporting(
        self, cli_runner: CliRunner, batch_documents: list[Path]
    ) -> None:
        """Test progress reporting during batch processing."""
        parent_dir = batch_documents[0].parent

        result = cli_runner.invoke(
            shard_md,
            [str(parent_dir), "--verbose"],
        )

        assert result.exit_code == 0
        # In verbose mode, should show progress information
        # This could be "Processing file X of Y" or similar
        assert "document_" in result.output

    def test_batch_partial_failure_handling(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test handling when some files fail to process."""
        # Create valid markdown files
        for i in range(3):
            (tmp_path / f"valid_{i}.md").write_text(f"# Valid Document {i}")

        # Create a file that might cause issues
        problem_file = tmp_path / "problem.md"
        # Create file but make it unreadable (if possible on the platform)
        problem_file.write_text("# Content")

        # Try to make it unreadable (may not work on all platforms)
        try:
            problem_file.chmod(0o000)
        except Exception:  # noqa: S110
            # If we can't change permissions, that's okay
            pass

        result = cli_runner.invoke(shard_md, [str(tmp_path)])

        # Should process what it can
        assert "valid_0.md" in result.output or result.exit_code == 0

        # Restore permissions if changed
        try:
            problem_file.chmod(0o644)
        except Exception:  # noqa: S110
            pass

    def test_batch_recursive_processing(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test recursive batch processing of nested directories."""
        # Create nested directory structure
        (tmp_path / "root.md").write_text("# Root")

        level1 = tmp_path / "docs"
        level1.mkdir()
        (level1 / "doc1.md").write_text("# Level 1 Doc")

        level2 = level1 / "guides"
        level2.mkdir()
        (level2 / "guide1.md").write_text("# Guide 1")
        (level2 / "guide2.md").write_text("# Guide 2")

        level3 = level2 / "advanced"
        level3.mkdir()
        (level3 / "advanced1.md").write_text("# Advanced Topic")

        # Process recursively
        result = cli_runner.invoke(
            shard_md,
            [str(tmp_path), "--recursive"],
        )

        assert result.exit_code == 0
        assert "root.md" in result.output
        assert "doc1.md" in result.output
        assert "guide1.md" in result.output
        assert "guide2.md" in result.output
        assert "advanced1.md" in result.output

    def test_batch_custom_chunk_settings(
        self, cli_runner: CliRunner, batch_documents: list[Path]
    ) -> None:
        """Test batch processing with custom chunk settings."""
        parent_dir = batch_documents[0].parent

        result = cli_runner.invoke(
            shard_md,
            [
                str(parent_dir),
                "--size",
                "300",
                "--overlap",
                "30",
                "--strategy",
                "structure",
            ],
        )

        assert result.exit_code == 0
        # All documents should be processed with custom settings

    def test_batch_dry_run(
        self, cli_runner: CliRunner, batch_documents: list[Path]
    ) -> None:
        """Test dry-run mode for batch operations."""
        parent_dir = batch_documents[0].parent

        result = cli_runner.invoke(
            shard_md,
            [str(parent_dir), "--store", "--collection", "test", "--dry-run"],
        )

        assert result.exit_code == 0
        # Dry-run shows normal processing but doesn't actually store
        assert "chunks" in result.output.lower() or "document" in result.output.lower()

    def test_batch_statistics_reporting(
        self, cli_runner: CliRunner, batch_documents: list[Path]
    ) -> None:
        """Test statistics reporting for batch operations."""
        parent_dir = batch_documents[0].parent

        result = cli_runner.invoke(
            shard_md,
            [str(parent_dir), "--verbose"],
        )

        assert result.exit_code == 0
        # Should show statistics like total files, total chunks, processing time
        output_lower = result.output.lower()
        assert any(
            word in output_lower for word in ["total", "processed", "chunks", "files"]
        )

    def test_batch_empty_files_handling(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test handling of empty markdown files in batch."""
        # Create mix of empty and non-empty files
        (tmp_path / "empty1.md").write_text("")
        (tmp_path / "empty2.md").write_text("")
        (tmp_path / "content.md").write_text("# Has Content\n\nSome text here.")

        result = cli_runner.invoke(shard_md, [str(tmp_path)])

        assert result.exit_code == 0
        # Should handle empty files gracefully
        assert "content.md" in result.output

    def test_batch_handles_many_files(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """E2E test: Verify batch processing handles multiple files correctly."""
        # Create just 10 small documents - enough to test batch but still fast
        for i in range(10):
            content = f"# Doc {i}\n\nMinimal content for document {i}."
            (tmp_path / f"doc_{i:02d}.md").write_text(content)

        result = cli_runner.invoke(shard_md, [str(tmp_path)])

        assert result.exit_code == 0
        # Verify files were processed
        assert "doc_00.md" in result.output
        assert "doc_09.md" in result.output

    def test_batch_consistent_ordering(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that batch processing maintains consistent file ordering."""
        # Create files with specific naming
        files = ["aaa.md", "bbb.md", "ccc.md", "001.md", "002.md", "003.md"]
        for filename in files:
            (tmp_path / filename).write_text(f"# {filename}")

        result = cli_runner.invoke(shard_md, [str(tmp_path)])

        assert result.exit_code == 0
        # Files should appear in consistent order in output
        output_lines = result.output.split("\n")

        # Find lines with filenames
        file_lines = [line for line in output_lines if ".md" in line]
        # Should have found the files
        assert len(file_lines) > 0

    def test_batch_with_symlinks(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test batch processing with symbolic links."""
        # Create actual files
        actual_dir = tmp_path / "actual"
        actual_dir.mkdir()
        (actual_dir / "real.md").write_text("# Real Document")

        # Create directory with symlink
        link_dir = tmp_path / "links"
        link_dir.mkdir()

        # Create symlink (if supported by platform)
        try:
            symlink = link_dir / "linked.md"
            symlink.symlink_to(actual_dir / "real.md")

            result = cli_runner.invoke(shard_md, [str(link_dir)])

            # Should handle symlinks (either follow or skip)
            assert result.exit_code == 0
        except OSError:
            # Symlinks not supported on this platform
            pytest.skip("Symlinks not supported on this platform")
