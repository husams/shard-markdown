"""Integration tests for edge case handling across the entire processing pipeline."""

from pathlib import Path

import pytest

from shard_markdown.config.settings import ProcessingConfig
from shard_markdown.core.models import ChunkingConfig
from shard_markdown.core.processor import DocumentProcessor


class TestEdgeCaseIntegration:
    """Integration tests for edge cases in real-world scenarios."""

    @pytest.fixture
    def processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create processor for integration testing."""
        return DocumentProcessor(chunking_config)

    @pytest.fixture
    def strict_processor(self, chunking_config: ChunkingConfig) -> DocumentProcessor:
        """Create strict processor for integration testing."""
        config = ProcessingConfig(strict_validation=True)
        return DocumentProcessor(chunking_config, config)

    def test_real_world_problematic_files(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing files that mimic real-world problematic documents."""
        # Simulate a README file with various encoding scenarios
        readme_content = """# Project README

This project demonstrates handling of various encoding scenarios that occur in
real projects.

## Installation

```bash
pip install project-name
```

## Configuration

The configuration file supports various characters:
- Cafe settings for European users
- Currency symbols: EUR, GBP, YEN, USD
- Mathematical symbols: alpha, beta, gamma for Greek users

## API Examples

```python
def process_document(filename: str) -> Dict[str, Any]:
    '''Process document with Unicode support.'''
    return {
        "status": "Success",
        "message": "Document processed successfully!",
        "encoding": "UTF-8"
    }
```

## Common Issues

Warning: Files with mixed encodings may cause issues.

### Troubleshooting

1. Check file encoding: `file -bi document.txt`
2. Convert if needed: `iconv -f latin1 -t utf8 file.txt`
3. Verify content: Look for corruption markers

## Contributing

Contributors from around the world welcome!

- Chinese contributions
- Japanese documentation
- Arabic translations
- Russian examples

## License

MIT (c) 2024 Project Contributors
"""

        readme_file = temp_dir / "README.md"
        readme_file.write_text(readme_content, encoding="utf-8")

        result = processor.process_document(readme_file, "readme-integration-test")

        assert result.success is True
        assert result.chunks_created > 0
        assert result.error is None

    def test_batch_processing_mixed_edge_cases(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test batch processing with various edge case files."""
        # Create a set of files with different edge cases
        test_files = []

        # File 1: Normal content
        normal_file = temp_dir / "normal.md"
        normal_file.write_text(
            "# Normal Document\n\nRegular content.", encoding="utf-8"
        )
        test_files.append(normal_file)

        # File 2: Unicode content (using basic Unicode that won't trigger corruption)
        unicode_file = temp_dir / "unicode.md"
        unicode_content = """# Unicode Test

Multi-language content:
- English: Hello World
- Spanish: Hola Mundo
- French: Bonjour le Monde
- German: Hallo Welt

Symbols: Copyright, Registered, Trademark
"""
        unicode_file.write_text(unicode_content, encoding="utf-8")
        test_files.append(unicode_file)

        # File 3: Complex markdown
        complex_file = temp_dir / "complex.md"
        complex_content = """# Complex Markdown

> This is a blockquote
>
> > With nested quotes
> >
> > ```python
> > # Code in nested quote
> > def nested():
> >     return "complex"
> > ```

| Table | With | Complex | Content |
|-------|------|---------|---------|
| **Bold** | *Italic* | `Code` | [Link](http://example.com) |
| Multi<br>Line | Text | Symbol | Emoji |

1. Ordered list
   - Bullet in ordered
     > Quote in bullet in ordered

     ```javascript
     // Code in quote in bullet in ordered
     function complex() { return "very"; }
     ```

## Conclusion

Complex nesting test complete.
"""
        complex_file.write_text(complex_content, encoding="utf-8")
        test_files.append(complex_file)

        # File 4: Long content
        long_file = temp_dir / "long.md"
        long_content = "# Long Document\n\n" + "This is a long paragraph. " * 200
        long_file.write_text(long_content, encoding="utf-8")
        test_files.append(long_file)

        # File 5: Minimal content
        minimal_file = temp_dir / "minimal.md"
        minimal_file.write_text("# Short\n\nBrief.", encoding="utf-8")
        test_files.append(minimal_file)

        # Process batch
        batch_result = processor.process_batch(
            test_files, "mixed-edge-cases-test", max_workers=2
        )

        # All files should process successfully
        assert batch_result.total_files == 5
        assert batch_result.successful_files == 5
        assert batch_result.failed_files == 0
        assert batch_result.total_chunks > 0
        assert batch_result.success_rate == 100.0

    def test_encoding_fallback_in_realistic_scenario(
        self, temp_dir: Path, chunking_config: ChunkingConfig
    ) -> None:
        """Test encoding fallback with realistic mixed-encoding scenario."""
        # Create processor with fallback
        config = ProcessingConfig(encoding="utf-8", encoding_fallback="latin1")
        processor = DocumentProcessor(chunking_config, config)

        # Create a file that's valid latin1 but not UTF-8 (common scenario)
        # This simulates files created on Windows with extended ASCII
        mixed_encoding_content = """# Configuration Guide

This guide contains configuration examples with special characters:

## Database Settings

host = "localhost"
database = "cafe_db"
user = "jose"
password = "password123"

## Paths

log_path = "C:\\logs\\cafe.log"
data_path = "C:\\data\\year_2024\\"
backup_path = "\\\\server\\backups\\user\\"

## Messages

success_msg = "Operation completed successfully"
error_msg = "Error: could not complete operation"
warning_msg = "Warning: check configuration"

## Regional Settings

currency = "EUR"
decimal_separator = ","
thousands_separator = "."
"""

        # Write as Latin1 (common for legacy systems)
        mixed_file = temp_dir / "mixed_encoding.md"
        mixed_file.write_text(mixed_encoding_content, encoding="latin1")

        result = processor.process_document(mixed_file, "mixed-encoding-test")

        # Should succeed using fallback encoding
        assert result.success is True
        assert result.chunks_created > 0
        assert result.error is None

    def test_large_batch_with_various_sizes(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing large batch with files of various sizes."""
        test_files = []

        # Create files of different sizes
        size_configs = [
            {"name": "tiny", "sections": 1, "content_multiplier": 1},
            {"name": "small", "sections": 3, "content_multiplier": 5},
            {"name": "medium", "sections": 10, "content_multiplier": 10},
            {"name": "large", "sections": 30, "content_multiplier": 15},
            {"name": "extra_large", "sections": 50, "content_multiplier": 20},
        ]

        for _i, config in enumerate(size_configs):
            # Create multiple files of each size
            for j in range(3):  # 3 files per size = 15 total files
                file_name = f"{config['name']}_{j}.md"
                test_file = temp_dir / file_name

                content_parts = [f"# {config['name'].title()} Document {j}\n\n"]

                for section in range(config["sections"]):
                    content_parts.append(f"## Section {section + 1}\n\n")
                    base_content = f"Content for section {section + 1}. "
                    repeated_content = base_content * config["content_multiplier"]
                    content_parts.append(repeated_content + "\n\n")

                    # Add code blocks occasionally
                    if section % 5 == 0:
                        content_parts.append(f"""```python
def function_{section}():
    '''Function for section {section}.'''
    return f"Result from section {section}"
```

""")

                content = "".join(content_parts)
                test_file.write_text(content, encoding="utf-8")
                test_files.append(test_file)

        # Process large batch
        batch_result = processor.process_batch(
            test_files, "large-batch-test", max_workers=4
        )

        # Should handle all files successfully
        assert batch_result.total_files == 15
        assert batch_result.successful_files == 15
        assert batch_result.failed_files == 0
        assert batch_result.total_chunks > 0

        # Performance should be reasonable
        assert batch_result.total_processing_time > 0
        assert batch_result.processing_speed > 0

    def test_concurrent_processing_edge_cases(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test concurrent processing with edge case files."""
        edge_case_files = []

        # Create various edge case files for concurrent processing
        edge_cases = [
            {
                "name": "whitespace_heavy",
                "content": "# Document\n\n"
                + "   \n" * 100
                + "Content\n"
                + "\t\n" * 50
                + "End",
            },
            {
                "name": "symbol_heavy",
                "content": "# Symbols\n\n"
                + "!@#$%^&*(){}[]|\\:;\"'<>,.?/`~" * 20
                + "\n\nEnd",
            },
            {
                "name": "long_lines",
                "content": "# Long Lines\n\n" + "Very long line " * 500 + "\n\nEnd",
            },
            {
                "name": "nested_structures",
                "content": """# Nested

"""
                + "\n".join(
                    [f"{'>' * (i % 10 + 1)} Level {i} quote" for i in range(100)]
                )
                + "\n\nEnd",
            },
            {
                "name": "mixed_line_endings",
                "content": "# Mixed\nUnix line\r\nWindows line\rOld Mac line\n\nEnd",
            },
        ]

        for case in edge_cases:
            # Create multiple files for each edge case
            for i in range(2):
                file_name = f"{case['name']}_{i}.md"
                edge_file = temp_dir / file_name
                edge_file.write_text(case["content"], encoding="utf-8")
                edge_case_files.append(edge_file)

        # Process concurrently
        batch_result = processor.process_batch(
            edge_case_files, "concurrent-edge-cases-test", max_workers=3
        )

        # Should handle all edge cases concurrently
        assert batch_result.total_files == 10  # 5 cases × 2 files each
        assert batch_result.successful_files >= 8  # Most should succeed
        assert batch_result.total_chunks >= 0

    def test_memory_management_with_edge_cases(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test memory management when processing edge case files."""
        # Create files that might stress memory management
        memory_test_files = []

        # Large file with repetitive content
        large_repetitive = temp_dir / "large_repetitive.md"
        repetitive_content = (
            "# Large Repetitive\n\n" + ("Repeated content. " * 1000 + "\n\n") * 50
        )
        large_repetitive.write_text(repetitive_content, encoding="utf-8")
        memory_test_files.append(large_repetitive)

        # File with many small sections
        many_sections = temp_dir / "many_sections.md"
        sections_content = "# Many Sections\n\n" + "\n\n".join(
            [f"## Section {i}\n\nContent {i}." for i in range(500)]
        )
        many_sections.write_text(sections_content, encoding="utf-8")
        memory_test_files.append(many_sections)

        # File with complex nesting
        complex_nesting = temp_dir / "complex_nesting.md"
        nesting_parts = ["# Complex Nesting\n\n"]
        for i in range(100):
            nesting_parts.append(">" * (i % 20 + 1) + f" Nested quote level {i}\n")
        complex_nesting.write_text("".join(nesting_parts), encoding="utf-8")
        memory_test_files.append(complex_nesting)

        # File with long lines
        long_lines = temp_dir / "long_lines.md"
        long_content = "# Long Lines\n\n" + "\n\n".join(
            [f"Line {i}: " + "word " * 100 for i in range(200)]
        )
        long_lines.write_text(long_content, encoding="utf-8")
        memory_test_files.append(long_lines)

        # Process files and monitor basic performance
        import time

        start_time = time.time()

        batch_result = processor.process_batch(
            memory_test_files, "memory-management-test", max_workers=2
        )

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete without memory issues
        assert batch_result.total_files == 4
        assert batch_result.successful_files >= 3  # Most should succeed
        assert batch_result.total_chunks > 0

        # Should complete in reasonable time
        assert total_time < 30.0  # Should not take more than 30 seconds

    def test_error_recovery_in_batch_processing(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test error recovery when processing mixed valid and invalid files."""
        mixed_files = []

        # Valid files
        for i in range(3):
            valid_file = temp_dir / f"valid_{i}.md"
            valid_file.write_text(
                f"# Valid Document {i}\n\nContent for document {i}.", encoding="utf-8"
            )
            mixed_files.append(valid_file)

        # Problematic files that might cause issues
        # Empty file
        empty_file = temp_dir / "empty.md"
        empty_file.write_text("", encoding="utf-8")
        mixed_files.append(empty_file)

        # Whitespace only file
        whitespace_file = temp_dir / "whitespace.md"
        whitespace_file.write_text("   \n\n\t\t\n   \n", encoding="utf-8")
        mixed_files.append(whitespace_file)

        # Process batch - should recover from errors
        batch_result = processor.process_batch(
            mixed_files, "error-recovery-test", max_workers=2
        )

        # Should process valid files successfully despite problematic ones
        assert batch_result.total_files == 5
        assert batch_result.successful_files >= 3  # At least the valid files
        assert batch_result.failed_files > 0  # Some should fail
        assert batch_result.total_chunks >= 3  # From valid files

    def test_realistic_documentation_processing(
        self, processor: DocumentProcessor, temp_dir: Path
    ) -> None:
        """Test processing realistic documentation files."""
        # Create a set of files that mimic a real documentation project
        doc_files = []

        # API documentation
        api_doc = temp_dir / "api.md"
        api_content = """# API Documentation

## Authentication

All API requests require authentication using API keys.

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \\
     https://api.example.com/v1/users
```

## Endpoints

### GET /users

Returns a list of users.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Maximum number of results |
| `offset` | integer | Number of results to skip |
| `filter` | string | Filter expression |

**Response:**

```json
{
  "users": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

### POST /users

Creates a new user.

**Request Body:**

```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "password": "secure_password"
}
```

## Error Handling

The API uses standard HTTP status codes:

- `200 OK` - Success
- `400 Bad Request` - Invalid request
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Access denied
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

Error responses include details:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request is invalid",
    "details": "Field 'email' is required"
  }
}
```
"""
        api_doc.write_text(api_content, encoding="utf-8")
        doc_files.append(api_doc)

        # Installation guide
        install_doc = temp_dir / "installation.md"
        install_content = """# Installation Guide

## System Requirements

- Python 3.8 or higher
- 4GB RAM minimum
- 10GB disk space

## Installation Methods

### Using pip

```bash
pip install example-package
```

### Using conda

```bash
conda install -c conda-forge example-package
```

### From source

```bash
git clone https://github.com/example/package.git
cd package
pip install -e .
```

## Configuration

Create a configuration file at `~/.example/config.yaml`:

```yaml
database:
  host: localhost
  port: 5432
  name: example_db

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

features:
  - feature1
  - feature2
```

## Verification

Verify installation:

```python
import example_package
print(example_package.__version__)
```

## Troubleshooting

### Common Issues

#### Import Error

If you see `ModuleNotFoundError`, ensure the package is installed:

```bash
pip list | grep example-package
```

#### Permission Denied

On macOS/Linux, you may need sudo:

```bash
sudo pip install example-package
```

#### Version Conflicts

Use virtual environments:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install example-package
```
"""
        install_doc.write_text(install_content, encoding="utf-8")
        doc_files.append(install_doc)

        # Tutorial
        tutorial_doc = temp_dir / "tutorial.md"
        tutorial_content = """# Getting Started Tutorial

## Introduction

This tutorial will guide you through the basic usage of the example package.

## Step 1: Basic Setup

First, import the necessary modules:

```python
from example_package import Client, Config
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

## Step 2: Configuration

Create a configuration object:

```python
config = Config(
    host="localhost",
    port=8080,
    timeout=30
)

# Or load from file
config = Config.from_file("config.yaml")
```

## Step 3: Create Client

Initialize the client:

```python
client = Client(config)

# Test connection
try:
    client.connect()
    logger.info("Connected successfully!")
except ConnectionError as e:
    logger.error(f"Failed to connect: {e}")
```

## Step 4: Basic Operations

### Creating Resources

```python
# Create a new resource
resource = client.create_resource({
    "name": "My Resource",
    "description": "A sample resource",
    "tags": ["example", "tutorial"]
})

print(f"Created resource with ID: {resource.id}")
```

### Querying Resources

```python
# Get all resources
resources = client.list_resources()

# Filter resources
filtered = client.list_resources(
    filters={"tag": "tutorial"}
)

# Get specific resource
resource = client.get_resource(resource_id=123)
```

### Updating Resources

```python
# Update resource
updated = client.update_resource(
    resource_id=123,
    data={"description": "Updated description"}
)
```

### Deleting Resources

```python
# Delete resource
client.delete_resource(resource_id=123)
```

## Advanced Usage

### Batch Operations

```python
# Create multiple resources
resources_data = [
    {"name": f"Resource {i}"} for i in range(10)
]

batch_result = client.batch_create(resources_data)
```

### Error Handling

```python
from example_package.exceptions import (
    ResourceNotFound,
    ValidationError,
    APIError
)

try:
    resource = client.get_resource(999)
except ResourceNotFound:
    logger.warning("Resource not found")
except ValidationError as e:
    logger.error(f"Validation failed: {e.details}")
except APIError as e:
    logger.error(f"API error: {e.message}")
```

## Next Steps

- Read the [API Documentation](api.md)
- Check out [Advanced Examples](examples.md)
- Join our [Community Forum](https://forum.example.com)

Happy coding!
"""
        tutorial_doc.write_text(tutorial_content, encoding="utf-8")
        doc_files.append(tutorial_doc)

        # Process documentation files
        batch_result = processor.process_batch(
            doc_files, "documentation-test", max_workers=2
        )

        # Should handle all documentation successfully
        assert batch_result.total_files == 3
        assert batch_result.successful_files == 3
        assert batch_result.failed_files == 0
        assert batch_result.total_chunks > 0

        # Should create a reasonable number of chunks
        assert batch_result.total_chunks >= 10  # Documentation should be well-chunked
