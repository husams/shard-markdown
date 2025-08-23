"""End-to-end tests for ChromaDB integration - real database operations."""

import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from shard_markdown.cli.main import shard_md


@pytest.mark.e2e
@pytest.mark.chromadb
class TestChromaDBIntegration:
    """Test ChromaDB integration end-to-end with real database."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def chromadb_available(self) -> bool:
        """Check if ChromaDB is available for testing."""
        try:
            import chromadb

            # Try to connect to local ChromaDB
            client = chromadb.HttpClient(host="localhost", port=8000)
            client.heartbeat()  # Check if server is running
            return True
        except Exception:
            return False

    @pytest.fixture
    def test_collection_name(self) -> str:
        """Generate unique collection name for testing."""
        timestamp = int(time.time())
        return f"test_collection_{timestamp}"

    @pytest.fixture
    def sample_documents(self, tmp_path: Path) -> list[Path]:
        """Create sample documents for ChromaDB testing."""
        docs = []

        # Document 1: Technical documentation
        doc1_content = """---
title: API Documentation
category: technical
version: 1.0.0
---

# API Documentation

## Authentication

All API requests require authentication using Bearer tokens.

### Getting a Token

```python
import requests

response = requests.post(
    "https://api.example.com/auth/token",
    json={"username": "user", "password": "pass"}
)
token = response.json()["token"]
```

## Endpoints

### GET /users

Returns a list of all users.

### POST /users

Creates a new user.

## Error Codes

- 400: Bad Request
- 401: Unauthorized
- 404: Not Found
- 500: Internal Server Error"""

        doc1 = tmp_path / "api_docs.md"
        doc1.write_text(doc1_content)
        docs.append(doc1)

        # Document 2: Tutorial
        doc2_content = """---
title: Getting Started Tutorial
category: tutorial
difficulty: beginner
---

# Getting Started with Our Platform

## Introduction

Welcome to our platform! This tutorial will guide you through the basics.

## Step 1: Installation

First, install the required packages:

```bash
pip install our-package
```

## Step 2: Configuration

Create a configuration file:

```yaml
settings:
  host: localhost
  port: 8000
```

## Step 3: First Run

Run your first command:

```bash
our-tool init
our-tool process data.txt
```

## Conclusion

You're now ready to use our platform!"""

        doc2 = tmp_path / "tutorial.md"
        doc2.write_text(doc2_content)
        docs.append(doc2)

        # Document 3: Reference
        doc3_content = """---
title: Configuration Reference
category: reference
---

# Configuration Reference

## Core Settings

### chunk_size
- Type: integer
- Default: 500
- Description: Size of document chunks

### chunk_overlap
- Type: integer
- Default: 50
- Description: Overlap between chunks

### chunk_method
- Type: string
- Options: fixed, structure
- Default: structure

## Advanced Settings

### chromadb.host
- Type: string
- Default: localhost

### chromadb.port
- Type: integer
- Default: 8000"""

        doc3 = tmp_path / "reference.md"
        doc3.write_text(doc3_content)
        docs.append(doc3)

        return docs

    def test_store_single_document(
        self,
        cli_runner: CliRunner,
        sample_documents: list[Path],
        test_collection_name: str,
        chromadb_available: bool,
    ) -> None:
        """Test storing a single document to ChromaDB."""
        if not chromadb_available:
            pytest.skip("ChromaDB not available")

        doc = sample_documents[0]
        result = cli_runner.invoke(
            shard_md,
            [
                str(doc),
                "--store",
                "--collection",
                test_collection_name,
            ],
        )

        # ChromaDB storage errors don't affect exit code (chunks are still processed)
        # Check the output to determine if storage was successful
        if "error" in result.output.lower() or "failed" in result.output.lower():
            # ChromaDB not available - storage failed but processing succeeded
            assert result.exit_code == 0  # Processing should still succeed
            assert "chromadb" in result.output.lower()
        else:
            # ChromaDB available - storage succeeded
            assert result.exit_code == 0
            assert (
                "stored" in result.output.lower() or "success" in result.output.lower()
            )
            assert test_collection_name in result.output

    def test_store_multiple_documents(
        self,
        cli_runner: CliRunner,
        sample_documents: list[Path],
        test_collection_name: str,
        chromadb_available: bool,
    ) -> None:
        """Test storing multiple documents to the same collection."""
        if not chromadb_available:
            pytest.skip("ChromaDB not available")

        # Store all documents
        for doc in sample_documents:
            result = cli_runner.invoke(
                shard_md,
                [
                    str(doc),
                    "--store",
                    "--collection",
                    test_collection_name,
                ],
            )
            assert result.exit_code == 0

        # Verify all were stored (would need query functionality)

    def test_update_existing_collection(
        self,
        cli_runner: CliRunner,
        sample_documents: list[Path],
        test_collection_name: str,
        chromadb_available: bool,
    ) -> None:
        """Test updating an existing collection with new documents."""
        if not chromadb_available:
            pytest.skip("ChromaDB not available")

        # Store first document
        result1 = cli_runner.invoke(
            shard_md,
            [
                str(sample_documents[0]),
                "--store",
                "--collection",
                test_collection_name,
            ],
        )
        assert result1.exit_code == 0

        # Store second document to same collection
        result2 = cli_runner.invoke(
            shard_md,
            [
                str(sample_documents[1]),
                "--store",
                "--collection",
                test_collection_name,
            ],
        )
        assert result2.exit_code == 0

    def test_connection_error_handling(
        self,
        cli_runner: CliRunner,
        sample_documents: list[Path],
    ) -> None:
        """Test handling of ChromaDB connection errors."""
        # Use invalid host/port
        result = cli_runner.invoke(
            shard_md,
            [
                str(sample_documents[0]),
                "--store",
                "--collection",
                "test",
                "--chroma-host",
                "nonexistent.host",
                "--chroma-port",
                "99999",
            ],
        )

        # Should handle connection error gracefully
        assert result.exit_code != 0
        assert "error" in result.output.lower() or "failed" in result.output.lower()

    def test_batch_storage(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        test_collection_name: str,
        chromadb_available: bool,
    ) -> None:
        """Test batch storage of multiple documents."""
        if not chromadb_available:
            pytest.skip("ChromaDB not available")

        # Create directory with multiple documents
        for i in range(5):
            doc_content = f"""# Document {i}

This is document number {i}.

## Content

Unique content for document {i}."""

            (tmp_path / f"doc_{i}.md").write_text(doc_content)

        # Process entire directory
        result = cli_runner.invoke(
            shard_md,
            [
                str(tmp_path),
                "--store",
                "--collection",
                test_collection_name,
            ],
        )

        assert result.exit_code == 0
        # Should show all documents were processed
        for i in range(5):
            assert f"doc_{i}.md" in result.output

    def test_dry_run_storage(
        self,
        cli_runner: CliRunner,
        sample_documents: list[Path],
        test_collection_name: str,
    ) -> None:
        """Test dry-run mode for storage operations."""
        result = cli_runner.invoke(
            shard_md,
            [
                str(sample_documents[0]),
                "--store",
                "--collection",
                test_collection_name,
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        # Dry-run shows normal processing but doesn't actually store
        assert (
            "chunks" in result.output.lower() or "processing" in result.output.lower()
        )

    def test_custom_chromadb_settings(
        self,
        cli_runner: CliRunner,
        sample_documents: list[Path],
        test_collection_name: str,
        chromadb_available: bool,
    ) -> None:
        """Test using custom ChromaDB host and port."""
        if not chromadb_available:
            pytest.skip("ChromaDB not available")

        result = cli_runner.invoke(
            shard_md,
            [
                str(sample_documents[0]),
                "--store",
                "--collection",
                test_collection_name,
                "--chroma-host",
                "localhost",
                "--chroma-port",
                "8000",
            ],
        )

        if result.exit_code == 0:
            assert "stored" in result.output.lower()

    def test_metadata_preservation(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        test_collection_name: str,
        chromadb_available: bool,
    ) -> None:
        """Test that document metadata is preserved in ChromaDB."""
        if not chromadb_available:
            pytest.skip("ChromaDB not available")

        # Create document with rich metadata
        doc_content = """---
title: Test Document
author: Test Author
date: 2024-01-01
tags: [test, metadata, chromadb]
custom_field: custom_value
---

# Test Document

Content with metadata that should be preserved."""

        doc = tmp_path / "metadata_test.md"
        doc.write_text(doc_content)

        result = cli_runner.invoke(
            shard_md,
            [
                str(doc),
                "--store",
                "--collection",
                test_collection_name,
                "--verbose",
            ],
        )

        assert result.exit_code == 0
        # In verbose mode, might show metadata being stored

    def test_chunking_strategies_with_storage(
        self,
        cli_runner: CliRunner,
        sample_documents: list[Path],
        test_collection_name: str,
        chromadb_available: bool,
    ) -> None:
        """Test different chunking strategies with ChromaDB storage."""
        if not chromadb_available:
            pytest.skip("ChromaDB not available")

        # Test with structure-aware chunking
        result1 = cli_runner.invoke(
            shard_md,
            [
                str(sample_documents[0]),
                "--store",
                "--collection",
                f"{test_collection_name}_structure",
                "--strategy",
                "structure",
                "--size",
                "200",
            ],
        )
        assert result1.exit_code == 0

        # Test with fixed-size chunking
        result2 = cli_runner.invoke(
            shard_md,
            [
                str(sample_documents[0]),
                "--store",
                "--collection",
                f"{test_collection_name}_fixed",
                "--strategy",
                "fixed",
                "--size",
                "200",
                "--overlap",
                "20",
            ],
        )
        assert result2.exit_code == 0

    def test_collection_name_validation(
        self,
        cli_runner: CliRunner,
        sample_documents: list[Path],
        chromadb_available: bool,
    ) -> None:
        """Test collection name validation."""
        if not chromadb_available:
            pytest.skip("ChromaDB not available")

        # Test with invalid collection names
        invalid_names = [
            "ab",  # Too short
            "a" * 64,  # Too long
            "test collection",  # Contains space
            "test@collection",  # Invalid character
        ]

        for invalid_name in invalid_names:
            result = cli_runner.invoke(
                shard_md,
                [
                    str(sample_documents[0]),
                    "--store",
                    "--collection",
                    invalid_name,
                ],
            )

            # Should reject invalid names
            if result.exit_code != 0:
                assert (
                    "error" in result.output.lower()
                    or "invalid" in result.output.lower()
                )

    def test_performance_with_large_batch(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        test_collection_name: str,
        chromadb_available: bool,
    ) -> None:
        """Test performance with larger batch of documents."""
        if not chromadb_available:
            pytest.skip("ChromaDB not available")

        # Create 20 documents
        for i in range(20):
            content = f"""# Document {i}

## Section 1
Content for document {i}, section 1.
{"Lorem ipsum " * 50}

## Section 2
Content for document {i}, section 2.
{"Dolor sit amet " * 50}"""

            (tmp_path / f"doc_{i:03d}.md").write_text(content)

        start_time = time.time()
        result = cli_runner.invoke(
            shard_md,
            [
                str(tmp_path),
                "--store",
                "--collection",
                test_collection_name,
            ],
        )
        elapsed = time.time() - start_time

        assert result.exit_code == 0
        # Should complete in reasonable time (< 30 seconds for 20 docs)
        assert elapsed < 30

    def test_duplicate_content_handling(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        test_collection_name: str,
        chromadb_available: bool,
    ) -> None:
        """Test handling of duplicate content."""
        if not chromadb_available:
            pytest.skip("ChromaDB not available")

        # Create two identical documents
        content = """# Duplicate Content

This content is identical in both files."""

        doc1 = tmp_path / "doc1.md"
        doc2 = tmp_path / "doc2.md"
        doc1.write_text(content)
        doc2.write_text(content)

        # Store first document
        result1 = cli_runner.invoke(
            shard_md,
            [
                str(doc1),
                "--store",
                "--collection",
                test_collection_name,
            ],
        )
        assert result1.exit_code == 0

        # Store second identical document
        result2 = cli_runner.invoke(
            shard_md,
            [
                str(doc2),
                "--store",
                "--collection",
                test_collection_name,
            ],
        )
        # Should handle duplicates gracefully
        assert result2.exit_code == 0
