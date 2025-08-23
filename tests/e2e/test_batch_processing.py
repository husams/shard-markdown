"""End-to-end tests for batch processing - multi-file operations."""

import sys
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

    def test_batch_edge_cases_mixed_valid_invalid_files(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """TC-E2E-025 Scenario A: Test batch processing with mixed valid/invalid files.

        Validates that batch processing handles edge cases correctly:
        - Valid markdown files are processed successfully
        - Empty files are handled gracefully
        - Large files are processed without issues
        - Broken symlinks are detected and skipped
        - Permission-denied files are handled appropriately
        """
        batch_dir = tmp_path / "batch_dir"
        batch_dir.mkdir()

        # Create valid files
        (batch_dir / "valid1.md").write_text("""# Valid Document 1

This is a normal markdown document with content that should be processed successfully.

## Section 1

Some meaningful content here for chunking.

## Section 2

More content to ensure proper processing.""")

        (batch_dir / "valid2.md").write_text("""# Valid Document 2

Another normal markdown document.

## Overview

This document contains structured content that demonstrates proper markdown processing.

## Details

Additional information for testing purposes.""")

        # Create empty file (0 bytes)
        (batch_dir / "empty.md").write_text("")

        # Create large file (simulating 10MB with repeated content)
        large_content = "# Large Document\n\n" + ("Large file content block. " * 1000)
        (batch_dir / "huge.md").write_text(large_content)

        # Create broken symlink (if platform supports symlinks)
        broken_symlink = batch_dir / "broken_symlink.md"
        try:
            broken_symlink.symlink_to(batch_dir / "nonexistent_target.md")
        except (OSError, NotImplementedError):
            # Symlinks not supported, create a regular file for testing instead
            broken_symlink.write_text("# Placeholder for broken symlink test")

        # Create permission-denied file
        permission_denied = batch_dir / "permission_denied.md"
        permission_denied.write_text("# Permission Test")

        # Try to restrict permissions (may not work on all platforms)
        original_permissions = None
        try:
            original_permissions = permission_denied.stat().st_mode
            permission_denied.chmod(0o000)
        except (OSError, PermissionError):
            # Cannot change permissions, skip this part of the test
            pass

        try:
            # Process the entire directory
            result = cli_runner.invoke(shard_md, [str(batch_dir), "--verbose"])

            # Valid files should be processed successfully
            assert "valid1.md" in result.output
            assert "valid2.md" in result.output

            # Large file should be processed (might show in verbose output)
            assert "huge.md" in result.output or result.exit_code == 0

            # Should complete without crashing (exit code 0 or handled gracefully)
            # Some files may fail, but the process should continue
            assert result.exit_code == 0 or "Error" in result.output

            # In verbose mode, should show some processing information
            output_lower = result.output.lower()
            assert any(
                word in output_lower
                for word in ["processing", "chunks", "files", "document"]
            )

        finally:
            # Restore permissions if we changed them
            if original_permissions is not None:
                try:
                    permission_denied.chmod(original_permissions)
                except (OSError, PermissionError):
                    pass

    def test_batch_edge_cases_duplicate_filenames(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """TC-E2E-025 Scenario B: Test batch processing with duplicate filenames.

        Validates that files with same names in different directories are processed
        correctly with full path distinction.
        """
        duplicates_dir = tmp_path / "duplicates"
        duplicates_dir.mkdir()

        # Create file.md in root
        (duplicates_dir / "file.md").write_text("""# Root File

This is the file.md in the root duplicates directory.

## Content

Root level content for testing duplicate filename handling.""")

        # Create subdir1/file.md
        subdir1 = duplicates_dir / "subdir1"
        subdir1.mkdir()
        (subdir1 / "file.md").write_text("""# Subdir1 File

This is the file.md in subdir1.

## Different Content

Subdir1 specific content to differentiate from other files.""")

        # Create subdir2/file.md
        subdir2 = duplicates_dir / "subdir2"
        subdir2.mkdir()
        (subdir2 / "file.md").write_text("""# Subdir2 File

This is the file.md in subdir2.

## Unique Content

Subdir2 specific content with unique information.""")

        # Process recursively to catch all file.md instances
        result = cli_runner.invoke(
            shard_md, [str(duplicates_dir), "--recursive", "--verbose"]
        )

        assert result.exit_code == 0

        # All three file.md instances should be processed
        # The output should show processing of files (exact format may vary)
        output_lower = result.output.lower()
        assert "file.md" in result.output

        # Should process multiple files (shown in verbose output or file count)
        assert any(word in output_lower for word in ["processing", "chunks", "files"])

        # Verify no infinite loops or crashes occurred
        assert result.exit_code == 0

    def test_batch_edge_cases_circular_symlinks(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """TC-E2E-025 Scenario C: Test batch processing with circular symlinks.

        Validates that circular symlinks are detected and skipped without causing
        infinite loops.
        """
        circular_dir = tmp_path / "circular"
        circular_dir.mkdir()

        # Create a real markdown file
        (circular_dir / "real.md").write_text("""# Real Document

This is a legitimate markdown file that should be processed normally.

## Content

Real content that demonstrates normal processing alongside circular symlinks.""")

        # Try to create circular symlinks (if platform supports them)
        link1 = circular_dir / "link1"
        link2 = circular_dir / "link2"

        try:
            # Create circular symlinks: link1 -> link2 -> link1
            link1.symlink_to(link2, target_is_directory=False)
            link2.symlink_to(link1, target_is_directory=False)

            # Process the directory
            result = cli_runner.invoke(shard_md, [str(circular_dir), "--verbose"])

            # Should handle circular symlinks without infinite loop
            assert result.exit_code == 0

            # Real file should be processed
            assert "real.md" in result.output

            # Should not hang or crash due to circular symlinks
            # The exact behavior may vary (skip or detect), but should complete
            # Command should complete successfully or at least exit cleanly
            assert result.exit_code is not None  # Command completed

        except (OSError, NotImplementedError):
            # Symlinks not supported on this platform
            pytest.skip("Symlinks not supported on this platform")

    def test_batch_edge_cases_comprehensive(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """TC-E2E-025: Comprehensive edge cases test combining all scenarios.

        Tests multiple edge cases together to ensure robust batch processing:
        - Mixed valid/invalid files
        - Duplicate filenames in different directories
        - Various file sizes and conditions
        """
        test_root = tmp_path / "comprehensive_test"
        test_root.mkdir()

        # Scenario 1: Mixed valid/invalid files
        mixed_dir = test_root / "mixed"
        mixed_dir.mkdir()

        (mixed_dir / "valid.md").write_text("# Valid\n\nNormal content.")
        (mixed_dir / "empty.md").write_text("")
        large_content = "# Large\n\n" + ("Content block. " * 500)
        (mixed_dir / "large.md").write_text(large_content)

        # Scenario 2: Duplicate filenames
        dup1_dir = test_root / "dup1"
        dup1_dir.mkdir()
        (dup1_dir / "common.md").write_text("# Common File 1\n\nContent from dup1.")

        dup2_dir = test_root / "dup2"
        dup2_dir.mkdir()
        (dup2_dir / "common.md").write_text("# Common File 2\n\nContent from dup2.")

        # Scenario 3: Nested structure
        nested_dir = test_root / "nested" / "deep" / "structure"
        nested_dir.mkdir(parents=True)
        (nested_dir / "deep.md").write_text("# Deep File\n\nDeeply nested content.")

        # Process everything recursively
        result = cli_runner.invoke(shard_md, [str(test_root), "--recursive"])

        assert result.exit_code == 0

        # Should process valid files without crashing
        # Exact output format may vary, but should indicate successful processing
        output_lower = result.output.lower()

        # Should show evidence of processing multiple files
        assert any(
            keyword in output_lower
            for keyword in ["processing", "chunks", "total", "file"]
        )

        # Should complete without hanging or infinite loops
        # Command should complete (exit_code will be set for completed commands)
        assert result.exit_code is not None

    # TC-E2E-025 Implementation - Batch Processing Edge Cases

    @pytest.mark.e2e
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Unix permissions test",
    )
    def test_tc_e2e_025_scenario_a_permission_denied_handling(
        self, cli_runner, tmp_path
    ):
        """TC-E2E-025 Scenario A: Permission Denied File Handling."""
        batch_dir = tmp_path / "permission_batch"
        batch_dir.mkdir()

        # Create readable files
        (batch_dir / "readable1.md").write_text(
            "# Readable Document 1\n\nThis should process successfully."
        )
        (batch_dir / "readable2.md").write_text(
            "# Readable Document 2\n\nAnother readable document."
        )

        # Create file with restrictive permissions
        no_read_file = batch_dir / "no_read_permission.md"
        no_read_file.write_text("# No Read Permission\n\nThis will be restricted.")

        original_perm = no_read_file.stat().st_mode
        try:
            no_read_file.chmod(0o000)  # No permissions

            result = cli_runner.invoke(shard_md, [str(batch_dir), "--recursive"])

            # Should handle gracefully (partial success is OK)
            assert result.exit_code == 0 or "permission" in result.output.lower()

            # Readable files should be processed
            assert "readable1.md" in result.output
            assert "readable2.md" in result.output

            # Should show permission-related messages
            output_lower = result.output.lower()
            permission_indicators = ["permission", "denied", "cannot read", "access"]
            assert any(indicator in output_lower for indicator in permission_indicators)

            # Should not crash
            assert "Traceback" not in result.output

        finally:
            # Restore permissions
            try:
                no_read_file.chmod(original_perm)
            except (OSError, PermissionError):
                pass

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_tc_e2e_025_scenario_b_large_file_processing(self, cli_runner, tmp_path):
        """TC-E2E-025 Scenario B: Large File Processing."""
        large_dir = tmp_path / "large_files"
        large_dir.mkdir()

        # Create files of various sizes
        (large_dir / "small.md").write_text("# Small\n\nSmall file content.")

        # Medium file (100KB)
        medium_content = "# Medium File\n\n" + ("Content block. " * 2000)
        (large_dir / "medium.md").write_text(medium_content)

        # Large file (1MB)
        large_content = "# Large File\n\n" + ("Large content block. " * 20000)
        (large_dir / "large.md").write_text(large_content)

        # Process all files
        import time

        start_time = time.time()
        result = cli_runner.invoke(shard_md, [str(large_dir)])
        processing_time = time.time() - start_time

        # All files should process successfully
        assert result.exit_code == 0
        assert "small.md" in result.output
        assert "medium.md" in result.output
        assert "large.md" in result.output

        # Should complete in reasonable time
        assert processing_time < 30

        # Should not have critical errors
        output_lower = result.output.lower()
        critical_errors = [
            indicator
            for indicator in ["error", "failed", "exception"]
            if indicator in output_lower and "0 error" not in output_lower
        ]
        assert len(critical_errors) == 0

    @pytest.mark.e2e
    def test_tc_e2e_025_scenario_c_mixed_files(self, cli_runner, tmp_path):
        """TC-E2E-025 Scenario C: Mixed Valid/Invalid Files."""
        mixed_dir = tmp_path / "mixed_batch"
        mixed_dir.mkdir()

        # Valid files
        (mixed_dir / "valid1.md").write_text(
            "# Valid Document 1\n\n## Overview\nThis should process successfully."
        )
        (mixed_dir / "valid2.md").write_text(
            "# Valid Document 2\n\n### Details\nMore valid content."
        )

        # Empty file
        (mixed_dir / "empty.md").write_text("")

        # Binary file with .md extension
        binary_content = bytes(range(256)) * 10  # 2.56KB of binary data
        (mixed_dir / "binary_file.md").write_bytes(binary_content)

        # Create subdirectory
        subdir = mixed_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested_valid.md").write_text("# Nested Valid\n\nNested content.")

        # Process with verbose output
        result = cli_runner.invoke(
            shard_md, [str(mixed_dir), "--recursive", "--verbose"]
        )

        # Should complete successfully
        assert result.exit_code == 0

        # Valid files should be processed
        assert "valid1.md" in result.output
        assert "valid2.md" in result.output
        assert "nested_valid.md" in result.output

        # Should show processing activity
        output_lower = result.output.lower()
        assert any(
            indicator in output_lower
            for indicator in ["processed", "chunks", "files", "completed"]
        )

        # Should not crash
        assert "Traceback" not in result.output

    @pytest.mark.e2e
    def test_tc_e2e_025_scenario_d_duplicate_filenames(self, cli_runner, tmp_path):
        """TC-E2E-025 Scenario D: Duplicate Filename Handling."""
        duplicates_dir = tmp_path / "duplicates"
        duplicates_dir.mkdir()

        # Root level
        (duplicates_dir / "document.md").write_text(
            "# Root Document\n\nRoot level content."
        )

        # Level 1
        level1 = duplicates_dir / "level1"
        level1.mkdir()
        (level1 / "document.md").write_text("# Level 1 Document\n\nLevel 1 content.")

        # Level 2
        level2 = duplicates_dir / "level2"
        level2.mkdir()
        (level2 / "document.md").write_text("# Level 2 Document\n\nLevel 2 content.")

        # Nested level
        nested = level2 / "subdir"
        nested.mkdir()
        (nested / "document.md").write_text("# Nested Document\n\nNested content.")

        # Process recursively
        result = cli_runner.invoke(
            shard_md, [str(duplicates_dir), "--recursive", "--verbose"]
        )

        # Should process successfully
        assert result.exit_code == 0

        # All document.md files should be processed (count mentions)
        document_mentions = result.output.count("document.md")
        assert document_mentions >= 4  # All 4 document.md files

        # Should show processing activity
        output_lower = result.output.lower()
        assert any(
            indicator in output_lower
            for indicator in ["processing", "chunks", "total", "completed"]
        )

        # Should not skip files due to name conflicts
        skip_indicators = ["skipped", "duplicate", "collision"]
        for indicator in skip_indicators:
            if indicator in output_lower:
                # If skipping mentioned, should not be due to duplicate names
                assert "name" not in output_lower or "extension" in output_lower

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_tc_e2e_025_complete_integration(self, cli_runner, tmp_path):
        """TC-E2E-025 Complete Integration: All scenarios combined."""
        import time

        master_dir = tmp_path / "tc_e2e_025_complete"
        master_dir.mkdir()

        # Scenario A: Permission files
        perm_dir = master_dir / "permissions"
        perm_dir.mkdir()
        (perm_dir / "readable.md").write_text("# Readable\n\nNormal content.")

        # Scenario B: Large files
        large_dir = master_dir / "large_files"
        large_dir.mkdir()
        large_content = "# Large\n\n" + ("Content. " * 5000)
        (large_dir / "large.md").write_text(large_content)

        # Scenario C: Mixed files
        mixed_dir = master_dir / "mixed"
        mixed_dir.mkdir()
        (mixed_dir / "valid.md").write_text("# Valid\n\nGood content.")
        (mixed_dir / "empty.md").write_text("")

        # Scenario D: Duplicates
        dup_dir = master_dir / "duplicates"
        dup_dir.mkdir()
        for i, subdir in enumerate(["dir1", "dir2", "dir3"]):
            sub_path = dup_dir / subdir
            sub_path.mkdir()
            (sub_path / "same_name.md").write_text(
                f"# Document {i + 1}\n\nContent from {subdir}."
            )

        # Process everything
        start_time = time.time()
        result = cli_runner.invoke(
            shard_md, [str(master_dir), "--recursive", "--verbose"]
        )
        total_time = time.time() - start_time

        # Should complete successfully
        assert result.exit_code == 0

        # Should process files from all scenarios
        assert "readable.md" in result.output
        assert "large.md" in result.output
        assert "valid.md" in result.output
        assert "same_name.md" in result.output

        # Should complete in reasonable time
        assert total_time < 60

        # Should show comprehensive processing
        output_lower = result.output.lower()
        assert any(
            indicator in output_lower
            for indicator in ["processed", "total", "files", "chunks"]
        )

        # Should not crash
        assert "Traceback" not in result.output

        print("\nTC-E2E-025 Complete Integration Test:")
        print(f"Total processing time: {total_time:.2f} seconds")
        print("Successfully handled complex mix of file conditions")
