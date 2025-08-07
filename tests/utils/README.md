# Test Utilities and Helper Functions

This directory contains reusable test utilities that help reduce code duplication and improve test maintainability across the shard-markdown test suite.

## Overview

The test utilities are organized into several helper classes:

- **FileHelper**: Create various types of test files (markdown, Unicode, large files, etc.)
- **MockHelper**: Create mock objects and configurations for testing
- **AssertionHelper**: Common assertion patterns for test validation
- **DataGenerator**: Generate test data like markdown templates and chunks
- **TimingHelper**: Performance testing and execution time validation
- **CleanupHelper**: Cleanup operations for test files and resources

## Quick Start

Import the helpers you need in your test files:

```python
from tests.utils.helpers import (
    FileHelper,
    MockHelper,
    AssertionHelper,
    DataGenerator,
    TimingHelper,
)
```

## Helper Classes

### FileHelper

Create test files with various characteristics:

```python
# Create a basic markdown file
markdown_file = FileHelper.create_markdown_file(
    temp_dir, "test.md", "# Test Document\n\nContent here."
)

# Create a large file for performance testing
large_file = FileHelper.create_large_markdown_file(
    temp_dir, "large.md", num_sections=50
)

# Create files with specific characteristics
unicode_file = FileHelper.create_unicode_markdown_file(temp_dir, "unicode.md")
empty_file = FileHelper.create_empty_file(temp_dir, "empty.md")
binary_file = FileHelper.create_binary_file(temp_dir, "corrupt.md")

# Create a file with exact size (useful for size limit testing)
sized_file = FileHelper.create_file_at_size(temp_dir, "exact.md", 1000)
```

### MockHelper

Create mock objects and configurations:

```python
# Create mock configurations
chromadb_config = MockHelper.create_mock_chromadb_config(
    host="test-host", port=9000
)

chunking_config = MockHelper.create_mock_chunking_config(
    chunk_size=500, overlap=100
)

processing_config = MockHelper.create_mock_processing_config(
    batch_size=1, max_workers=1  # Test-optimized settings
)

# Create mock data objects
processing_result = MockHelper.create_mock_processing_result(
    success=True, chunks_created=5
)

document_chunk = MockHelper.create_mock_document_chunk(
    chunk_id="test_1", content="Test content"
)

markdown_ast = MockHelper.create_mock_markdown_ast()

# Create mock service objects
collection_manager = MockHelper.create_mock_collection_manager()
chromadb_client = MockHelper.create_mock_chromadb_client()
```

### AssertionHelper

Common assertion patterns:

```python
# Assert processing success
AssertionHelper.assert_processing_result_success(
    result, expected_chunks=5, min_processing_time=0.1
)

# Assert processing failure
AssertionHelper.assert_processing_result_failure(
    result, expected_error_keywords=["file", "not found"]
)

# Assert file size
AssertionHelper.assert_file_size_within_range(file_path, 1000, 2000)

# Assert chunk validity
AssertionHelper.assert_chunks_valid(chunks)
```

### DataGenerator

Generate test data:

```python
# Generate markdown content templates
templates = DataGenerator.generate_markdown_content_templates()
simple_content = templates["simple"]
technical_content = templates["technical"]

# Generate test chunks
chunks = DataGenerator.generate_test_chunks(count=10)

# Generate performance test files
perf_files = DataGenerator.generate_performance_test_files(
    temp_dir, count=20, size_per_file=5000
)
```

### TimingHelper

Performance testing utilities:

```python
# Time function execution
result, execution_time = TimingHelper.time_function(my_function, arg1, arg2)

# Assert execution time is within limits
result = TimingHelper.assert_execution_time(
    my_function, max_time=2.0, arg1, arg2
)
```

### CleanupHelper

Cleanup operations:

```python
# Clean up temporary files
CleanupHelper.cleanup_temp_files([file1, file2, file3])

# Restore file permissions after testing
CleanupHelper.restore_file_permissions(file_path)
```

## Using with Existing Fixtures

The utilities work seamlessly with existing pytest fixtures defined in `conftest.py`:

```python
def test_with_utilities_and_fixtures(temp_dir, chunking_config, sample_chunks):
    # Use existing fixtures
    assert chunking_config.chunk_size == 300

    # Enhance with utilities
    large_file = FileHelper.create_large_markdown_file(temp_dir, "large.md")
    AssertionHelper.assert_chunks_valid(sample_chunks)

    # Mix and match as needed
    templates = DataGenerator.generate_markdown_content_templates()
    # ... test logic
```

## Enhanced Fixtures

The updated `conftest.py` provides enhanced fixtures using these utilities:

- `test_processing_config`: Test-optimized processing configuration
- `unicode_markdown_file`: File with Unicode content
- `empty_markdown_file`: Empty file for edge case testing
- `large_markdown_file`: Large file for performance testing
- `file_at_size_limit`: File at exact size limit
- `binary_file`: Binary file for error testing

## Parameterized Testing

New parameterized fixtures for testing multiple scenarios:

```python
def test_different_chunk_sizes(chunk_sizes):
    # Tests run with sizes: 50, 100, 500, 1000, 2000
    config = MockHelper.create_mock_chunking_config(chunk_size=chunk_sizes)
    # ... test logic

def test_different_encodings(encodings):
    # Tests run with: "utf-8", "latin-1", "ascii"
    file = FileHelper.create_markdown_file(temp_dir, "test.md", "content", encodings)
    # ... test logic
```

## Best Practices

1. **Prefer utilities over inline file creation**: Use `FileHelper` instead of creating files manually
2. **Use assertion helpers**: Replace custom assertions with `AssertionHelper` methods
3. **Generate realistic test data**: Use `DataGenerator` for consistent test content
4. **Mock consistently**: Use `MockHelper` for consistent mock object creation
5. **Clean up resources**: Use `CleanupHelper` for proper test cleanup
6. **Time performance tests**: Use `TimingHelper` for performance-sensitive tests

## Example: Complete Test Refactoring

**Before** (duplicated code):
```python
def test_process_file_success(temp_dir):
    content = "# Test\n\nContent here."
    file_path = temp_dir / "test.md"
    file_path.write_text(content)

    result = processor.process(file_path)
    assert result.success is True
    assert result.error is None
    assert result.chunks_created > 0

def test_process_file_failure(temp_dir):
    # Similar file creation code...
    # Similar assertion code...
```

**After** (using utilities):
```python
def test_process_file_success(temp_dir):
    file_path = FileHelper.create_markdown_file(temp_dir, "test.md", "# Test\n\nContent here.")
    result = processor.process(file_path)
    AssertionHelper.assert_processing_result_success(result)

def test_process_file_failure(temp_dir):
    file_path = FileHelper.create_empty_file(temp_dir, "empty.md")
    result = processor.process(file_path)
    AssertionHelper.assert_processing_result_failure(result, ["empty"])
```

## Contributing

When adding new test utilities:

1. Follow the existing class structure and naming conventions
2. Add comprehensive docstrings with examples
3. Include type hints for all parameters and return values
4. Follow the project's coding standards (use `ruff` for formatting)
5. Add the utility to the appropriate helper class
6. Update this documentation

## Testing the Utilities

The utilities themselves are tested in `tests/unit/test_utilities_example.py`, which also serves as a comprehensive usage example.
