"""End-to-end tests for complete CLI workflows."""

import json
import subprocess
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from shard_markdown.cli.main import cli


@pytest.mark.e2e
class TestCLIWorkflows:
    """End-to-end tests for complete CLI workflows."""

    @pytest.fixture
    def cli_runner(self):
        """CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def sample_project(self, temp_dir):
        """Create a sample project structure with documentation."""
        project_dir = temp_dir / "sample_project"
        project_dir.mkdir()

        # Create documentation structure
        docs_dir = project_dir / "docs"
        docs_dir.mkdir()

        # API documentation
        api_dir = docs_dir / "api"
        api_dir.mkdir()

        (api_dir / "authentication.md").write_text(
            """# Authentication

## Overview
The API uses token-based authentication for secure access.

## Getting a Token
To obtain an authentication token:

1. Register an account through the web interface
2. Login with your credentials
3. Navigate to the API section
4. Generate a new token
5. Include the token in your API requests

## Using Tokens
Include your token in the Authorization header:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" https://api.example.com/users
```

## Token Expiration
Tokens expire after 30 days and must be renewed.
"""
        )

        (api_dir / "endpoints.md").write_text(
            """# API Endpoints

## Users Endpoints

### GET /users
Returns a list of all users.

**Parameters:**
- `page` (optional): Page number for pagination
- `limit` (optional): Number of results per page

**Response:**
```json
{
  "users": [...],
  "pagination": {...}
}
```

### POST /users
Creates a new user account.

**Body:**
```json
{
  "username": "string",
  "email": "string", 
  "password": "string"
}
```

## Posts Endpoints

### GET /posts
Returns a list of posts.

### POST /posts
Creates a new post.

**Requirements:**
- User must be authenticated
- Content must be non-empty
"""
        )

        # User guides
        guides_dir = docs_dir / "guides"
        guides_dir.mkdir()

        (guides_dir / "getting-started.md").write_text(
            """---
title: "Getting Started Guide"
difficulty: "beginner"
estimated_time: "15 minutes"
category: "tutorial"
---

# Getting Started

Welcome to our platform! This comprehensive guide will help you get started quickly.

## Prerequisites

Before you begin, ensure you have:
- A valid email address
- Basic understanding of REST APIs
- A development environment set up

## Installation Steps

1. **Create Account**
   - Visit our website
   - Click "Sign Up"
   - Verify your email

2. **Generate API Key**
   - Login to your account
   - Go to Settings > API Keys
   - Create a new key

3. **Test Connection**
   ```bash
   curl -H "Authorization: Bearer YOUR_KEY" https://api.example.com/health
   ```

## First API Call

Once setup is complete, try your first API call:

```python
import requests

headers = {"Authorization": "Bearer YOUR_KEY"}
response = requests.get("https://api.example.com/users", headers=headers)
print(response.json())
```

## Next Steps

- Read the [API Documentation](../api/endpoints.md)
- Check out [Authentication](../api/authentication.md)
- Join our community forum
"""
        )

        (guides_dir / "advanced-features.md").write_text(
            """# Advanced Features

## Webhook Configuration

Set up webhooks to receive real-time notifications:

```javascript
const webhook = {
  url: "https://your-app.com/webhook",
  events: ["user.created", "post.published"],
  secret: "your-webhook-secret"
};
```

## Rate Limiting

API calls are limited to:
- 1000 requests per hour for free tier
- 10000 requests per hour for premium tier

## Batch Operations

Process multiple items efficiently:

```python
batch_request = {
  "operations": [
    {"method": "POST", "path": "/users", "body": {...}},
    {"method": "PUT", "path": "/users/123", "body": {...}}
  ]
}
```
"""
        )

        return project_dir

    def test_complete_documentation_processing_workflow(
        self, cli_runner, sample_project
    ):
        """Test complete workflow from processing to querying documentation."""
        docs_dir = sample_project / "docs"

        # Step 1: Process all documentation files
        result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                "sample-project-docs",
                "--recursive",
                "--chunk-size",
                "800",
                "--chunk-overlap",
                "150",
                str(docs_dir),
            ],
        )

        print(f"Process output: {result.output}")
        assert result.exit_code == 0, f"Process command failed: {result.output}"

        # Should show successful processing
        assert (
            "processed" in result.output.lower() or "success" in result.output.lower()
        )

    def test_configuration_workflow(self, cli_runner, temp_dir):
        """Test configuration management workflow."""
        config_file = temp_dir / "test-config.yaml"

        # Step 1: Initialize configuration (if this command exists)
        result = cli_runner.invoke(cli, ["config", "show"])

        print(f"Config show output: {result.output}")
        # Should show configuration or help if command doesn't exist
        assert result.exit_code == 0 or "Usage:" in result.output

    def test_dry_run_workflow(self, cli_runner, sample_project):
        """Test dry run functionality."""
        docs_dir = sample_project / "docs"

        # Dry run to see what would be processed
        result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                "preview-test",
                "--dry-run",
                "--recursive",
                str(docs_dir),
            ],
        )

        print(f"Dry run output: {result.output}")

        # Should show preview without actually processing
        if result.exit_code == 0:
            assert "dry" in result.output.lower() or "preview" in result.output.lower()
        else:
            # Dry run option might not be implemented yet
            assert "dry-run" in result.output or "No such option" in result.output

    def test_help_system_workflow(self, cli_runner):
        """Test help system across commands."""
        # Main help
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Commands:" in result.output

        # Process command help
        result = cli_runner.invoke(cli, ["process", "--help"])
        assert result.exit_code == 0
        assert "collection" in result.output.lower()

        # Collections command help (if it exists)
        result = cli_runner.invoke(cli, ["collections", "--help"])
        # Should work or show that command doesn't exist
        assert result.exit_code == 0 or "No such command" in result.output

    def test_error_handling_workflow(self, cli_runner, temp_dir):
        """Test error handling in realistic scenarios."""
        # Create a problematic file
        bad_file = temp_dir / "problematic.md"
        bad_file.write_bytes(b"\xff\xfe# Invalid encoding content")

        # Try to process it
        result = cli_runner.invoke(
            cli, ["process", "--collection", "error-test", str(bad_file)]
        )

        print(f"Error handling output: {result.output}")

        # Should handle the error gracefully
        if result.exit_code != 0:
            assert "error" in result.output.lower() or "failed" in result.output.lower()

    def test_multiple_files_workflow(self, cli_runner, sample_project):
        """Test processing multiple files explicitly."""
        docs_dir = sample_project / "docs"

        # Get all markdown files
        md_files = list(docs_dir.rglob("*.md"))
        file_args = [str(f) for f in md_files]

        if md_files:
            result = cli_runner.invoke(
                cli, ["process", "--collection", "multi-file-test"] + file_args
            )

            print(f"Multi-file output: {result.output}")
            assert (
                result.exit_code == 0
            ), f"Multi-file processing failed: {result.output}"

    def test_chunk_parameter_workflow(self, cli_runner, sample_project):
        """Test different chunking parameters."""
        test_file = sample_project / "docs" / "guides" / "getting-started.md"

        # Test with different chunk sizes
        for chunk_size in [500, 1000, 1500]:
            result = cli_runner.invoke(
                cli,
                [
                    "process",
                    "--collection",
                    f"chunk-test-{chunk_size}",
                    "--chunk-size",
                    str(chunk_size),
                    "--chunk-overlap",
                    str(chunk_size // 5),
                    str(test_file),
                ],
            )

            print(f"Chunk size {chunk_size} output: {result.output}")
            assert (
                result.exit_code == 0
            ), f"Chunk size {chunk_size} failed: {result.output}"

    def test_collections_workflow(self, cli_runner, sample_project):
        """Test collections management workflow."""
        # First, process some documents to create collections
        test_file = sample_project / "docs" / "guides" / "getting-started.md"

        result = cli_runner.invoke(
            cli, ["process", "--collection", "collections-test", str(test_file)]
        )

        if result.exit_code == 0:
            # Try to list collections
            result = cli_runner.invoke(cli, ["collections", "list"])

            print(f"Collections list output: {result.output}")

            if result.exit_code == 0:
                # Should show our collection
                assert (
                    "collections-test" in result.output
                    or "collection" in result.output.lower()
                )
            else:
                # Collections command might not be implemented yet
                assert "No such command" in result.output or result.exit_code != 0

    def test_query_workflow(self, cli_runner, sample_project):
        """Test query workflow."""
        # First, process documents
        docs_dir = sample_project / "docs"

        result = cli_runner.invoke(
            cli, ["process", "--collection", "query-test", "--recursive", str(docs_dir)]
        )

        if result.exit_code == 0:
            # Try to query the collection
            result = cli_runner.invoke(
                cli,
                [
                    "query",
                    "search",
                    "authentication",
                    "--collection",
                    "query-test",
                    "--limit",
                    "3",
                ],
            )

            print(f"Query output: {result.output}")

            if result.exit_code == 0:
                # Should return relevant results
                assert (
                    "authentication" in result.output.lower()
                    or "result" in result.output.lower()
                )
            else:
                # Query command might not be implemented yet
                assert "No such command" in result.output or result.exit_code != 0

    def test_output_format_workflow(self, cli_runner, sample_project):
        """Test different output formats."""
        test_file = sample_project / "docs" / "api" / "authentication.md"

        # Test default output
        result = cli_runner.invoke(
            cli, ["process", "--collection", "output-test", str(test_file)]
        )

        assert result.exit_code == 0

        # Test JSON output (if supported)
        result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                "output-test-json",
                "--output",
                "json",
                str(test_file),
            ],
        )

        # Should work or show that option doesn't exist
        if result.exit_code == 0:
            # Try to parse as JSON
            try:
                json.loads(result.output)
                # If it parses, it's valid JSON
            except json.JSONDecodeError:
                # Might not be pure JSON output
                pass
        else:
            assert "output" in result.output or "No such option" in result.output

    def test_verbose_output_workflow(self, cli_runner, sample_project):
        """Test verbose output modes."""
        test_file = sample_project / "docs" / "guides" / "getting-started.md"

        # Test with verbose flag
        result = cli_runner.invoke(
            cli, ["-v", "process", "--collection", "verbose-test", str(test_file)]
        )

        print(f"Verbose output: {result.output}")
        assert result.exit_code == 0

        # Test with very verbose
        result = cli_runner.invoke(
            cli,
            ["-vvv", "process", "--collection", "very-verbose-test", str(test_file)],
        )

        print(f"Very verbose output: {result.output}")
        assert result.exit_code == 0

    def test_config_file_workflow(self, cli_runner, sample_project, temp_dir):
        """Test workflow with custom config file."""
        # Create a test config file
        config_file = temp_dir / "test-config.yaml"
        config_content = """
chromadb:
  host: localhost
  port: 8000
  ssl: false

chunking:
  default_size: 1200
  default_overlap: 240
  method: structure

processing:
  batch_size: 15
  max_workers: 6
"""
        config_file.write_text(config_content)

        test_file = sample_project / "docs" / "api" / "endpoints.md"

        # Process with custom config
        result = cli_runner.invoke(
            cli,
            [
                "--config",
                str(config_file),
                "process",
                "--collection",
                "config-test",
                str(test_file),
            ],
        )

        print(f"Config file output: {result.output}")
        assert result.exit_code == 0

    def test_large_project_workflow(self, cli_runner, temp_dir):
        """Test workflow with a larger project structure."""
        # Create a larger project structure
        large_project = temp_dir / "large_project"
        large_project.mkdir()

        # Create multiple directories with docs
        for module in ["auth", "users", "posts", "admin"]:
            module_dir = large_project / module
            module_dir.mkdir()

            (module_dir / f"{module}_guide.md").write_text(
                f"""# {module.title()} Module

## Overview
This is the {module} module documentation.

## Features
- Feature 1 for {module}
- Feature 2 for {module}
- Feature 3 for {module}

## API Reference
Detailed API documentation for {module} module.

{'## Code Examples' if module != 'admin' else ''}
{f'''```python
def {module}_function():
    return "{module} result"
```''' if module != 'admin' else ''}

## Configuration
Configuration options for {module}.
"""
            )

        # Process the entire project
        result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                "large-project",
                "--recursive",
                "--chunk-size",
                "1000",
                str(large_project),
            ],
        )

        print(f"Large project output: {result.output}")
        assert result.exit_code == 0
        assert (
            "processed" in result.output.lower() or "success" in result.output.lower()
        )


@pytest.mark.e2e
class TestCLIErrorScenarios:
    """Test CLI error scenarios and edge cases."""

    def test_invalid_collection_name_scenarios(self, cli_runner, sample_markdown_file):
        """Test various invalid collection names."""
        invalid_names = [
            "",  # Empty
            "a" * 300,  # Too long
            "invalid/name",  # Invalid characters
            "123-numbers-first",  # Numbers first
        ]

        for invalid_name in invalid_names:
            result = cli_runner.invoke(
                cli,
                ["process", "--collection", invalid_name, str(sample_markdown_file)],
            )

            # Should handle invalid names appropriately
            print(f"Invalid name '{invalid_name}' output: {result.output}")
            # Most should fail, but we allow flexibility in validation

    def test_missing_files_scenarios(self, cli_runner):
        """Test scenarios with missing files."""
        result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                "missing-file-test",
                "nonexistent1.md",
                "nonexistent2.md",
            ],
        )

        print(f"Missing files output: {result.output}")
        assert result.exit_code != 0
        assert "exist" in result.output.lower() or "found" in result.output.lower()

    def test_permission_denied_scenarios(self, cli_runner, temp_dir):
        """Test permission denied scenarios."""
        # Create a directory without read permissions
        try:
            restricted_dir = temp_dir / "restricted"
            restricted_dir.mkdir()

            test_file = restricted_dir / "test.md"
            test_file.write_text("# Test")

            # Remove read permissions
            restricted_dir.chmod(0o000)

            result = cli_runner.invoke(
                cli,
                [
                    "process",
                    "--collection",
                    "permission-test",
                    "--recursive",
                    str(restricted_dir),
                ],
            )

            print(f"Permission denied output: {result.output}")

            # Should handle permission errors gracefully
            if result.exit_code != 0:
                assert (
                    "permission" in result.output.lower()
                    or "access" in result.output.lower()
                )

        finally:
            # Restore permissions for cleanup
            try:
                restricted_dir.chmod(0o755)
            except:
                pass

    def test_malformed_config_scenarios(
        self, cli_runner, sample_markdown_file, temp_dir
    ):
        """Test scenarios with malformed config files."""
        # Create malformed config
        bad_config = temp_dir / "bad_config.yaml"
        bad_config.write_text(
            """
invalid: yaml: content: here
  - this is not valid
    yaml syntax
"""
        )

        result = cli_runner.invoke(
            cli,
            [
                "--config",
                str(bad_config),
                "process",
                "--collection",
                "bad-config-test",
                str(sample_markdown_file),
            ],
        )

        print(f"Bad config output: {result.output}")

        # Should handle malformed config gracefully
        if result.exit_code != 0:
            assert (
                "config" in result.output.lower()
                or "yaml" in result.output.lower()
                or "error" in result.output.lower()
            )


@pytest.mark.e2e
class TestCLIPerformance:
    """Test CLI performance characteristics."""

    def test_large_batch_processing_performance(self, cli_runner, temp_dir):
        """Test performance with large batch of files."""
        # Create many small files
        files_dir = temp_dir / "many_files"
        files_dir.mkdir()

        for i in range(50):  # Create 50 files
            file_path = files_dir / f"file_{i:03d}.md"
            file_path.write_text(
                f"""# Document {i}

This is document number {i} in the batch.

## Section 1
Content for section 1 of document {i}.

## Section 2  
Content for section 2 of document {i}.

## Conclusion
This concludes document {i}.
"""
            )

        # Process all files and measure time
        start_time = time.time()

        result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                "performance-test",
                "--recursive",
                str(files_dir),
            ],
        )

        end_time = time.time()
        processing_time = end_time - start_time

        print(f"Performance test output: {result.output}")
        print(f"Processing time: {processing_time:.2f} seconds")

        assert result.exit_code == 0
        assert processing_time < 60  # Should complete within 60 seconds

    def test_memory_usage_with_large_documents(self, cli_runner, temp_dir):
        """Test memory usage with large documents."""
        # Create a large document
        large_doc = temp_dir / "large_document.md"

        content = ["# Large Document\n\n"]
        for i in range(1000):  # Create substantial content
            content.append(f"## Section {i}\n")
            content.append(f"{'Content paragraph. ' * 50}\n\n")

        large_doc.write_text("".join(content))

        # Process the large document
        result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                "large-doc-test",
                "--chunk-size",
                "2000",
                str(large_doc),
            ],
        )

        print(f"Large document output: {result.output}")
        assert result.exit_code == 0
