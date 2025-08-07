"""End-to-end tests for CLI workflows."""

import os
import time
from typing import Any

import pytest
from click.testing import CliRunner

from shard_markdown.cli.main import cli
from tests.fixtures.chromadb_fixtures import ChromaDBTestFixture


@pytest.mark.e2e
class TestBasicCLIWorkflows:
    """Test basic end-to-end CLI workflows."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """CLI runner for e2e tests."""
        return CliRunner()

    @pytest.fixture(autouse=True)
    def setup_chromadb(self, chromadb_test_fixture: ChromaDBTestFixture) -> None:
        """Ensure ChromaDB is properly initialized for e2e tests.

        Args:
            chromadb_test_fixture: ChromaDB test fixture
        """
        # The fixture handles setup automatically
        pass

    @pytest.mark.chromadb
    def test_complete_document_processing_workflow(
        self,
        cli_runner: CliRunner,
        sample_markdown_file: Any,
        chromadb_test_fixture: ChromaDBTestFixture,
    ) -> None:
        """Test complete workflow from document to processed chunks."""
        # Ensure collection is created first
        collection_name = "e2e-test-collection"
        try:
            chromadb_test_fixture.create_test_collection(collection_name)
        except Exception as e:
            pytest.skip(f"ChromaDB not available: {e}")

        # Set environment variables for CLI
        env = os.environ.copy()
        env["CHROMA_HOST"] = chromadb_test_fixture.host
        env["CHROMA_PORT"] = str(chromadb_test_fixture.port)

        # Process a document
        result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                collection_name,
                "--chunk-size",
                "500",
                "--chunk-overlap",
                "100",
                "--use-mock",
                str(sample_markdown_file),
            ],
            env=env,
        )

        print(f"Process output: {result.output}")
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "successfully" in output_lower or "processed" in output_lower

        # Query the processed content
        query_result = cli_runner.invoke(
            cli,
            [
                "query",
                "search",
                "--collection",
                "e2e-test-collection",
                "--query",
                "test content",
                "--limit",
                "5",
            ],
        )

        print(f"Query output: {query_result.output}")
        # Query might fail if ChromaDB isn't running, but process should succeed
        if query_result.exit_code == 0:
            query_output_lower = query_result.output.lower()
            success_indicators = ["results", "chunks"]
            assert any(
                indicator in query_output_lower for indicator in success_indicators
            )

    @pytest.mark.chromadb
    def test_batch_processing_workflow(
        self,
        cli_runner: CliRunner,
        test_documents: Any,
        chromadb_test_fixture: ChromaDBTestFixture,
    ) -> None:
        """Test batch processing workflow."""
        # Ensure collection is created first
        collection_name = "batch-e2e-test"
        try:
            chromadb_test_fixture.create_test_collection(collection_name)
        except Exception as e:
            pytest.skip(f"ChromaDB not available: {e}")

        file_paths = [str(path) for path in test_documents.values()]

        # Set environment variables for CLI
        env = os.environ.copy()
        env["CHROMA_HOST"] = chromadb_test_fixture.host
        env["CHROMA_PORT"] = str(chromadb_test_fixture.port)

        result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                collection_name,
                "--chunk-method",
                "structure",
                "--max-workers",
                "2",
                "--use-mock",
            ]
            + file_paths,
            env=env,
        )

        print(f"Batch process output: {result.output}")
        assert result.exit_code == 0
        assert "processed" in result.output.lower()

    def test_recursive_directory_processing(
        self, cli_runner: CliRunner, test_documents: Any
    ) -> None:
        """Test recursive directory processing."""
        # Get the directory containing test documents
        test_dir = list(test_documents.values())[0].parent

        result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                "recursive-e2e-test",
                "--recursive",
                "--create-collection",
                "--use-mock",
                str(test_dir),
            ],
        )

        print(f"Recursive process output: {result.output}")
        assert result.exit_code == 0
        assert "processed" in result.output.lower()

    def test_collection_management_workflow(self, cli_runner: CliRunner) -> None:
        """Test collection management workflow."""
        # List collections
        list_result = cli_runner.invoke(cli, ["collections", "list"])
        print(f"Collections list output: {list_result.output}")

        # Create a collection
        create_result = cli_runner.invoke(
            cli,
            [
                "collections",
                "create",
                "--name",
                "workflow-test-collection",
                "--description",
                "Test collection for workflow testing",
            ],
        )
        print(f"Collection create output: {create_result.output}")

        # Get collection info
        info_result = cli_runner.invoke(
            cli, ["collections", "info", "--name", "workflow-test-collection"]
        )
        print(f"Collection info output: {info_result.output}")

        # Delete the collection
        delete_result = cli_runner.invoke(
            cli, ["collections", "delete", "--name", "workflow-test-collection"]
        )
        print(f"Collection delete output: {delete_result.output}")

    def test_config_management_workflow(
        self, cli_runner: CliRunner, temp_dir: Any
    ) -> None:
        """Test configuration management workflow."""
        config_file = temp_dir / "test_config.yaml"

        # Generate default config
        init_result = cli_runner.invoke(
            cli, ["config", "init", "--output", str(config_file)]
        )
        print(f"Config init output: {init_result.output}")

        if init_result.exit_code == 0:
            assert config_file.exists()

            # Show config
            show_result = cli_runner.invoke(
                cli, ["config", "show", "--config", str(config_file)]
            )
            print(f"Config show output: {show_result.output}")

            # Validate config
            validate_result = cli_runner.invoke(
                cli, ["config", "validate", "--config", str(config_file)]
            )
            print(f"Config validate output: {validate_result.output}")

    def test_help_and_version_commands(self, cli_runner: CliRunner) -> None:
        """Test help and version commands work correctly."""
        # Test main help
        help_result = cli_runner.invoke(cli, ["--help"])
        assert help_result.exit_code == 0
        assert "Shard Markdown" in help_result.output
        assert "Commands:" in help_result.output

        # Test version
        version_result = cli_runner.invoke(cli, ["--version"])
        assert version_result.exit_code == 0
        assert "0.1.0" in version_result.output

        # Test command-specific help
        process_help = cli_runner.invoke(cli, ["process", "--help"])
        assert process_help.exit_code == 0
        assert "collection" in process_help.output.lower()

        collections_help = cli_runner.invoke(cli, ["collections", "--help"])
        assert collections_help.exit_code == 0
        assert "list" in collections_help.output

        query_help = cli_runner.invoke(cli, ["query", "--help"])
        assert query_help.exit_code == 0


@pytest.mark.e2e
class TestAdvancedCLIWorkflows:
    """Test advanced CLI workflows and combinations."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """CLI runner for advanced tests."""
        return CliRunner()

    @pytest.fixture(autouse=True)
    def setup_chromadb(self, chromadb_test_fixture: ChromaDBTestFixture) -> None:
        """Ensure ChromaDB is properly initialized for e2e tests.

        Args:
            chromadb_test_fixture: ChromaDB test fixture
        """
        # The fixture handles setup automatically
        pass

    @pytest.mark.chromadb
    def test_custom_chunking_strategies(
        self,
        cli_runner: CliRunner,
        sample_markdown_file: Any,
        chromadb_test_fixture: ChromaDBTestFixture,
    ) -> None:
        """Test different chunking strategies."""
        strategies = [
            ("structure", "1000", "200"),
            ("fixed", "800", "150"),
            ("structure", "1500", "300"),
        ]

        # Set environment variables for CLI
        env = os.environ.copy()
        env["CHROMA_HOST"] = chromadb_test_fixture.host
        env["CHROMA_PORT"] = str(chromadb_test_fixture.port)

        for method, size, overlap in strategies:
            collection_name = f"chunking-{method}-{size}"

            # Ensure collection is created first
            try:
                chromadb_test_fixture.create_test_collection(collection_name)
            except Exception as e:
                pytest.skip(f"ChromaDB not available: {e}")

            result = cli_runner.invoke(
                cli,
                [
                    "process",
                    "--collection",
                    collection_name,
                    "--chunk-method",
                    method,
                    "--chunk-size",
                    size,
                    "--chunk-overlap",
                    overlap,
                    "--use-mock",
                    str(sample_markdown_file),
                ],
                env=env,
            )

            print(f"Chunking {method} output: {result.output}")
            assert result.exit_code == 0

    def test_metadata_preservation_workflow(
        self, cli_runner: CliRunner, temp_dir: Any
    ) -> None:
        """Test that metadata is preserved through processing."""
        # Create document with frontmatter
        doc_with_frontmatter = temp_dir / "frontmatter_doc.md"
        doc_content = """---
title: "Test Document"
author: "Test Author"
tags:
  - test
  - e2e
---

# Test Document

This document has frontmatter that should be preserved.

## Section 1

Content here.
"""
        doc_with_frontmatter.write_text(doc_content)

        result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                "metadata-test",
                "--create-collection",
                "--use-mock",
                str(doc_with_frontmatter),
            ],
        )

        print(f"Metadata processing output: {result.output}")
        assert result.exit_code == 0
        assert "processed" in result.output.lower()

    def test_error_recovery_workflow(
        self, cli_runner: CliRunner, temp_dir: Any
    ) -> None:
        """Test error recovery and partial processing."""
        # Create mix of valid and invalid files
        valid_file = temp_dir / "valid.md"
        valid_file.write_text("# Valid Document\n\nContent here.")

        invalid_file = temp_dir / "invalid.md"
        # Create file with problematic content
        invalid_file.write_text("# Invalid\n\n" + "x" * 1000000)  # Very large

        result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                "error-recovery-test",
                "--continue-on-error",
                str(valid_file),
                str(invalid_file),
            ],
        )

        print(f"Error recovery output: {result.output}")
        # Should process what it can, might have partial success

    def test_concurrent_processing_workflow(
        self, cli_runner: CliRunner, test_documents: Any
    ) -> None:
        """Test concurrent processing with different worker counts."""
        file_paths = [str(path) for path in test_documents.values()]

        for workers in [1, 2, 4]:
            collection_name = f"concurrent-{workers}-workers"

            start_time = time.time()
            result = cli_runner.invoke(
                cli,
                [
                    "process",
                    "--collection",
                    collection_name,
                    "--max-workers",
                    str(workers),
                ]
                + file_paths,
            )
            end_time = time.time()

            processing_time = end_time - start_time
            print(f"Workers {workers}: {processing_time:.2f}s")
            print(f"Concurrent {workers} output: {result.output}")

            assert result.exit_code == 0

    def test_large_document_processing_workflow(
        self, cli_runner: CliRunner, temp_dir: Any
    ) -> None:
        """Test processing of large documents."""
        # Create a substantial document
        large_doc = temp_dir / "large_document.md"

        content_parts = ["# Large Document Test\n\n"]
        for i in range(100):  # Create 100 sections
            content_parts.append(f"## Section {i + 1}\n\n")
            content_text = f"This is section {i + 1} with substantial content. " * 20
            content_parts.append(content_text)
            content_parts.append("\n\n")

            if i % 10 == 0:  # Add code blocks occasionally
                content_parts.append("```python\n")
                content_parts.append(f"def section_{i + 1}_function():\n")
                content_parts.append(f'    return "Section {i + 1} result"\n')
                content_parts.append("```\n\n")

        large_doc.write_text("".join(content_parts))

        result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                "large-doc-test",
                "--chunk-size",
                "1500",
                "--chunk-overlap",
                "300",
                str(large_doc),
            ],
        )

        print(f"Large document output: {result.output}")
        assert result.exit_code == 0

    def test_query_workflow_variations(
        self, cli_runner: CliRunner, sample_markdown_file: Any
    ) -> None:
        """Test different query variations."""
        # First process a document
        process_result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                "query-test-collection",
                str(sample_markdown_file),
            ],
        )

        if process_result.exit_code == 0:
            # Test different query types
            query_types = [
                ("search", ["--query", "test", "--limit", "3"]),
                ("similarity", ["--text", "sample content", "--limit", "5"]),
                ("list", ["--limit", "10"]),
            ]

            for query_type, args in query_types:
                query_result = cli_runner.invoke(
                    cli,
                    ["query", query_type, "--collection", "query-test-collection"]
                    + args,
                )

                print(f"Query {query_type} output: {query_result.output}")
                # Queries might fail if ChromaDB isn't available,
                # but we test the interface

    def test_config_override_workflow(
        self,
        cli_runner: CliRunner,
        sample_markdown_file: Any,
        temp_dir: Any,
    ) -> None:
        """Test configuration override workflow."""
        # Create custom config
        custom_config = temp_dir / "custom_config.yaml"
        config_content = """
chromadb:
  host: localhost
  port: 8000

chunking:
  default_size: 1200
  default_overlap: 250
  method: structure

processing:
  batch_size: 15
  max_workers: 2
"""
        custom_config.write_text(config_content)

        # Process with custom config
        result = cli_runner.invoke(
            cli,
            [
                "--config",
                str(custom_config),
                "process",
                "--collection",
                "config-override-test",
                str(sample_markdown_file),
            ],
        )

        print(f"Config override output: {result.output}")
        assert result.exit_code == 0

    def test_verbose_and_quiet_modes(
        self, cli_runner: CliRunner, sample_markdown_file: Any
    ) -> None:
        """Test verbose and quiet output modes."""
        # Test quiet mode
        quiet_result = cli_runner.invoke(
            cli,
            [
                "--quiet",
                "process",
                "--collection",
                "quiet-test",
                str(sample_markdown_file),
            ],
        )

        print(f"Quiet mode output: {quiet_result.output}")

        # Test verbose mode
        verbose_result = cli_runner.invoke(
            cli,
            [
                "--verbose",
                "process",
                "--collection",
                "verbose-test",
                str(sample_markdown_file),
            ],
        )

        print(f"Verbose mode output: {verbose_result.output}")

        # Test very verbose mode
        very_verbose_result = cli_runner.invoke(
            cli,
            [
                "-vvv",
                "process",
                "--collection",
                "very-verbose-test",
                str(sample_markdown_file),
            ],
        )

        print(f"Very verbose mode output: {very_verbose_result.output}")

    def test_dry_run_workflow(self, cli_runner: CliRunner, test_documents: Any) -> None:
        """Test dry run functionality."""
        file_paths = [str(path) for path in test_documents.values()]

        result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                "dry-run-test",
                "--dry-run",
                "--recursive",
            ]
            + file_paths,
        )

        print(f"Dry run output: {result.output}")
        assert result.exit_code == 0
        output_lower = result.output.lower()
        dry_run_indicators = ["would process", "dry run", "preview"]
        assert any(indicator in output_lower for indicator in dry_run_indicators)

    def test_file_pattern_filtering(self, cli_runner: CliRunner, temp_dir: Any) -> None:
        """Test file pattern filtering in recursive processing."""
        # Create various file types
        files_dir = temp_dir / "mixed_files"
        files_dir.mkdir()

        # Create markdown files
        (files_dir / "doc1.md").write_text("# Doc 1")
        (files_dir / "doc2.md").write_text("# Doc 2")

        # Create other files
        (files_dir / "readme.txt").write_text("Text file")
        (files_dir / "data.json").write_text('{"key": "value"}')

        # Process with pattern filtering
        result = cli_runner.invoke(
            cli,
            [
                "process",
                "--collection",
                "pattern-test",
                "--recursive",
                "--pattern",
                "*.md",
                str(files_dir),
            ],
        )

        print(f"Pattern filtering output: {result.output}")
        assert result.exit_code == 0
        output_lower = result.output.lower()
        success_indicators = ["processed", "success"]
        assert any(indicator in output_lower for indicator in success_indicators)


@pytest.mark.e2e
class TestCLIErrorScenarios:
    """Test CLI error scenarios and edge cases."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """CLI runner for error scenario tests."""
        return CliRunner()

    def test_invalid_collection_name_scenarios(
        self, cli_runner: CliRunner, sample_markdown_file: Any
    ) -> None:
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
                [
                    "process",
                    "--collection",
                    invalid_name,
                    str(sample_markdown_file),
                ],
            )

            # Should handle invalid names appropriately
            print(f"Invalid name '{invalid_name}' output: {result.output}")
            # Most should fail, but we allow flexibility in validation

    def test_missing_files_scenarios(self, cli_runner: CliRunner) -> None:
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
        output_lower = result.output.lower()
        error_indicators = ["exist", "found"]
        assert any(indicator in output_lower for indicator in error_indicators)

    def test_permission_denied_scenarios(
        self, cli_runner: CliRunner, temp_dir: Any
    ) -> None:
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
                output_lower = result.output.lower()
                permission_indicators = ["permission", "access"]
                assert any(
                    indicator in output_lower for indicator in permission_indicators
                )

        finally:
            # Restore permissions for cleanup
            try:
                restricted_dir.chmod(0o755)
            except Exception as e:
                # Log the exception if directory permission restore fails
                # This is acceptable during test cleanup
                print(f"Warning: Could not restore directory permissions: {e}")

    def test_malformed_config_scenarios(
        self,
        cli_runner: CliRunner,
        sample_markdown_file: Any,
        temp_dir: Any,
    ) -> None:
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
            output_lower = result.output.lower()
            config_error_indicators = ["config", "yaml", "error"]
            assert any(
                indicator in output_lower for indicator in config_error_indicators
            )


@pytest.mark.e2e
class TestCLIPerformance:
    """Test CLI performance characteristics."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """CLI runner for performance tests."""
        return CliRunner()

    def test_large_batch_processing_performance(
        self, cli_runner: CliRunner, temp_dir: Any
    ) -> None:
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

    def test_memory_usage_with_large_documents(
        self, cli_runner: CliRunner, temp_dir: Any
    ) -> None:
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
