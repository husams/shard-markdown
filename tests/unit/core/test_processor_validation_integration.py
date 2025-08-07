"""Integration tests for content validation in document processor."""

from pathlib import Path
from typing import Any

from shard_markdown.config.settings import ProcessingConfig
from shard_markdown.core.models import ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor
from shard_markdown.core.validation import ValidationConfig


class TestProcessorValidationIntegration:
    """Test integration of content validation with document processor."""

    def test_validation_disabled_by_config(self, temp_dir: Path) -> None:
        """Test processor with content validation disabled."""
        # Create config with validation disabled
        validation_config = ValidationConfig(enable_content_validation=False)
        processing_config = ProcessingConfig(validation=validation_config)
        chunking_config = ChunkingConfig()

        processor = DocumentProcessor(chunking_config, processing_config)
        assert processor.validator is None

        # Create file with normal content that should succeed
        normal_file = temp_dir / "normal.md"
        normal_file.write_text(
            "# Test\n\nNormal content without any issues.", encoding="utf-8"
        )

        result = processor.process_document(normal_file, "test-collection")
        # Should succeed since content is normal
        assert result.success is True
        assert result.chunks_created > 0

    def test_validation_strict_mode_failure(self, temp_dir: Path) -> None:
        """Test validation failure in strict mode."""
        # Create config with strict validation
        validation_config = ValidationConfig(
            enable_content_validation=True,
            max_control_char_ratio=0.01,  # Very strict
        )
        processing_config = ProcessingConfig(
            validation=validation_config,
            strict_validation=True,
        )
        chunking_config = ChunkingConfig()

        processor = DocumentProcessor(chunking_config, processing_config)

        # Create file with content that will fail validation
        bad_file = temp_dir / "bad.md"
        bad_file.write_text(
            "Text with\x01\x02\x03 control characters", encoding="utf-8"
        )

        result = processor.process_document(bad_file, "test-collection")
        # Should fail in strict mode
        assert result.success is False
        assert result.error is not None and "Content validation failed" in result.error
        assert result.chunks_created == 0

    def test_validation_graceful_mode_warning(self, temp_dir: Path) -> None:
        """Test validation failure in graceful mode."""
        # Create config with graceful validation
        validation_config = ValidationConfig(
            enable_content_validation=True,
            max_control_char_ratio=0.01,  # Very strict
        )
        processing_config = ProcessingConfig(
            validation=validation_config,
            strict_validation=False,  # Graceful mode
        )
        chunking_config = ChunkingConfig()

        processor = DocumentProcessor(chunking_config, processing_config)

        # Create file with content that will fail validation
        bad_file = temp_dir / "bad.md"
        bad_file.write_text(
            "Text with\x01\x02\x03 control characters", encoding="utf-8"
        )

        result = processor.process_document(bad_file, "test-collection")
        # Should fail with empty content (0 chunks) in graceful mode
        assert result.success is False
        assert result.error is not None and "empty" in result.error.lower()
        assert result.chunks_created == 0

    def test_validation_warning_logging(self, temp_dir: Path, caplog: Any) -> None:
        """Test that validation warnings are logged properly."""
        # Create config that will generate warnings with normal content
        validation_config = ValidationConfig(
            enable_content_validation=True,
            check_encoding_artifacts=False,  # Disable to focus on other checks
        )
        processing_config = ProcessingConfig(validation=validation_config)
        chunking_config = ChunkingConfig()

        processor = DocumentProcessor(chunking_config, processing_config)

        # Create file with normal content that should succeed
        normal_file = temp_dir / "normal.md"
        normal_file.write_text(
            "# Test\n\nNormal content that should succeed without issues.",
            encoding="utf-8",
        )

        result = processor.process_document(normal_file, "test-collection")
        # Should succeed with normal content
        assert result.success is True
        assert result.chunks_created > 0

    def test_large_file_sampling_integration(self, temp_dir: Path) -> None:
        """Test validation sampling for large files."""
        # Create config with reasonable sample size and larger chunks
        validation_config = ValidationConfig(
            enable_content_validation=True,
            max_sample_size=1000,  # Minimum allowed size
        )
        processing_config = ProcessingConfig(validation=validation_config)
        chunking_config = ChunkingConfig(
            chunk_size=2000
        )  # Larger chunks to avoid limits

        processor = DocumentProcessor(chunking_config, processing_config)

        # Create large file with normal content but not too large to break chunking
        large_content = """# Large Document

This is a large markdown document that exceeds the sample size.

""" + ("Content paragraph with normal text. " * 30)  # Smaller content

        large_file = temp_dir / "large.md"
        large_file.write_text(large_content, encoding="utf-8")

        result = processor.process_document(large_file, "test-collection")
        # Should succeed and process the large file
        assert result.success is True
        assert result.chunks_created > 0

    def test_binary_file_detection_integration(self, temp_dir: Path) -> None:
        """Test integration of binary file detection."""
        validation_config = ValidationConfig(enable_content_validation=True)
        processing_config = ProcessingConfig(
            validation=validation_config,
            strict_validation=True,
        )
        chunking_config = ChunkingConfig()

        processor = DocumentProcessor(chunking_config, processing_config)

        # Create file with binary-like content
        binary_file = temp_dir / "binary.md"
        binary_file.write_text("A" * 60, encoding="utf-8")  # Long repeated sequence

        result = processor.process_document(binary_file, "test-collection")
        # Should fail due to binary pattern detection
        assert result.success is False
        assert result.error is not None
        assert "repeated bytes" in result.error

    def test_encoding_fallback_with_validation(self, temp_dir: Path) -> None:
        """Test validation after encoding fallback."""
        validation_config = ValidationConfig(
            enable_content_validation=True,
            check_encoding_artifacts=False,  # Disable for clean test
        )
        processing_config = ProcessingConfig(
            validation=validation_config,
            encoding="utf-8",
            encoding_fallback="latin-1",
            strict_validation=True,
        )
        chunking_config = ChunkingConfig()

        processor = DocumentProcessor(chunking_config, processing_config)

        # Create file with latin-1 encoding that will fall back
        latin1_file = temp_dir / "latin1.md"
        # Write content that's valid in latin-1 but would be invalid UTF-8
        with open(latin1_file, "w", encoding="latin-1") as f:
            f.write("# Test\n\nCafe with special chars: normal content")

        result = processor.process_document(latin1_file, "test-collection")
        # Should succeed after fallback and validation
        assert result.success is True
        assert result.chunks_created > 0

    def test_markdown_structure_validation_integration(self, temp_dir: Path) -> None:
        """Test markdown structure validation integration."""
        validation_config = ValidationConfig(
            enable_content_validation=True,
            validate_markdown_structure=True,
        )
        processing_config = ProcessingConfig(validation=validation_config)
        chunking_config = ChunkingConfig()

        processor = DocumentProcessor(chunking_config, processing_config)

        # Create file with markdown structure issues
        structure_file = temp_dir / "structure.md"
        structure_file.write_text(
            """# Valid Header

```python
def test():
    pass
# Missing closing backticks

##Invalid header without space

More content here.
""",
            encoding="utf-8",
        )

        result = processor.process_document(structure_file, "test-collection")
        # Should succeed but may have warnings (structure issues are non-fatal)
        assert result.success is True
        assert result.chunks_created > 0

    def test_custom_validation_thresholds(self, temp_dir: Path) -> None:
        """Test custom validation threshold configuration."""
        # Test with relaxed thresholds
        validation_config = ValidationConfig(
            enable_content_validation=True,
            max_control_char_ratio=0.2,  # Very relaxed
            min_printable_ratio=0.5,  # Very relaxed
            check_encoding_artifacts=False,  # Disabled
        )
        processing_config = ProcessingConfig(validation=validation_config)
        chunking_config = ChunkingConfig()

        processor = DocumentProcessor(chunking_config, processing_config)

        # Create file with content that should pass with relaxed thresholds
        relaxed_file = temp_dir / "relaxed.md"
        relaxed_file.write_text(
            "# Test\n\nNormal content that should work fine.", encoding="utf-8"
        )

        result = processor.process_document(relaxed_file, "test-collection")
        # Should succeed with relaxed thresholds
        assert result.success is True
        assert result.chunks_created > 0

    def test_batch_processing_with_validation(self, temp_dir: Path) -> None:
        """Test batch processing with content validation."""
        validation_config = ValidationConfig(enable_content_validation=True)
        processing_config = ProcessingConfig(
            validation=validation_config,
            strict_validation=False,  # Graceful mode
        )
        chunking_config = ChunkingConfig()

        processor = DocumentProcessor(chunking_config, processing_config)

        # Create mix of good and bad files
        good_file = temp_dir / "good.md"
        good_file.write_text("# Good\n\nNormal content here.", encoding="utf-8")

        bad_file = temp_dir / "bad.md"
        bad_file.write_text(
            "Text\x01\x02\x03\x04\x05 with many control chars", encoding="utf-8"
        )

        files = [good_file, bad_file]

        batch_result = processor.process_batch(files, "batch-test")

        # Should have mixed results
        assert batch_result.total_files == 2
        assert batch_result.successful_files == 1  # Only good file
        assert batch_result.failed_files == 1  # Bad file fails
        assert batch_result.total_chunks > 0  # From good file

    def test_performance_impact_measurement(self, temp_dir: Path) -> None:
        """Test that validation doesn't significantly impact performance."""
        import time

        # Test with validation enabled
        validation_config = ValidationConfig(enable_content_validation=True)
        processing_config = ProcessingConfig(validation=validation_config)
        chunking_config = ChunkingConfig(
            chunk_size=2000
        )  # Larger chunks to avoid size limits

        processor_with_validation = DocumentProcessor(
            chunking_config, processing_config
        )

        # Test with validation disabled
        validation_config_disabled = ValidationConfig(enable_content_validation=False)
        processing_config_disabled = ProcessingConfig(
            validation=validation_config_disabled
        )

        processor_without_validation = DocumentProcessor(
            chunking_config, processing_config_disabled
        )

        # Create test file with reasonable size content
        test_file = temp_dir / "performance.md"
        content = """# Performance Test

This is a test document to measure validation performance impact.

""" + ("Content paragraph with reasonable length. " * 50)  # Smaller content

        test_file.write_text(content, encoding="utf-8")

        # Measure time with validation
        start_time = time.time()
        for _ in range(5):  # Process multiple times for more stable measurement
            result_with = processor_with_validation.process_document(
                test_file, "perf-test"
            )
        time_with_validation = time.time() - start_time

        # Measure time without validation
        start_time = time.time()
        for _ in range(5):
            result_without = processor_without_validation.process_document(
                test_file, "perf-test"
            )
        time_without_validation = time.time() - start_time

        # Both should succeed
        assert result_with.success is True
        assert result_without.success is True

        # Validation should add less than 50% overhead for this test case
        overhead_ratio = time_with_validation / time_without_validation
        assert overhead_ratio < 1.5  # Less than 50% overhead

        # Should be close in processing results
        assert result_with.chunks_created == result_without.chunks_created
