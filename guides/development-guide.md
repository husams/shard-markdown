# Development Guide

## Setting Up Development Environment

### Prerequisites
- Python 3.8+ (recommend 3.12)
- uv package manager
- ChromaDB server (local or Docker)

### Initial Setup
```bash
# Clone repository
git clone https://github.com/shard-markdown/shard-markdown.git
cd shard-markdown

# Install dependencies with uv
uv sync

# Install development dependencies
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Verify installation
shard-md --version
```

### ChromaDB Setup
```bash
# Option 1: Docker (recommended)
docker run -p 8000:8000 chromadb/chroma

# Option 2: Local installation
pip install chromadb
chroma run --path ./chroma_data
```

## Project Architecture

### Module Structure

#### CLI Module (`src/shard_markdown/cli/`)
- `main.py`: Entry point and command groups
- `process.py`: Document processing commands
- `collections.py`: Collection management commands
- `query.py`: Query and search commands
- `config.py`: Configuration commands

#### Core Module (`src/shard_markdown/core/`)
- `chunker.py`: Main chunking algorithms
  - `StructureAwareChunker`: Respects markdown structure
  - `FixedSizeChunker`: Character-based chunking
  - `SemanticChunker`: Meaning-based chunking
- `processor.py`: Document processing pipeline
- `metadata.py`: Metadata extraction and enhancement
- `models.py`: Pydantic models for data validation

#### ChromaDB Module (`src/shard_markdown/chromadb/`)
- `client.py`: ChromaDB client wrapper
- `collection.py`: Collection operations
- `query.py`: Query building and execution
- `embeddings.py`: Embedding function management

#### Config Module (`src/shard_markdown/config/`)
- `settings.py`: Configuration management
- `loader.py`: YAML file loading
- `validators.py`: Configuration validation

### Key Design Patterns

1. **Strategy Pattern**: Chunking algorithms
2. **Factory Pattern**: Chunker creation
3. **Repository Pattern**: ChromaDB operations
4. **Chain of Responsibility**: Processing pipeline

## Adding New Features

### 1. New Chunking Strategy

```python
# src/shard_markdown/core/chunker.py
from .base import BaseChunker

class CustomChunker(BaseChunker):
    def chunk(self, content: str) -> List[Chunk]:
        # Implementation
        pass

    def validate_chunk(self, chunk: Chunk) -> bool:
        # Validation logic
        pass
```

### 2. New CLI Command

```python
# src/shard_markdown/cli/custom.py
import click
from .main import cli

@cli.group()
def custom():
    """Custom command group."""
    pass

@custom.command()
@click.option('--option', help='Option description')
def subcommand(option):
    """Subcommand description."""
    # Implementation
```

### 3. New Metadata Extractor

```python
# src/shard_markdown/core/metadata.py
class CustomExtractor(BaseExtractor):
    def extract(self, content: str) -> Dict[str, Any]:
        # Extract custom metadata
        return metadata
```

## Code Style Guidelines

### Imports
```python
# Standard library
import os
from typing import List, Dict, Optional

# Third-party
import click
from pydantic import BaseModel

# Local
from shard_markdown.core import Chunker
from shard_markdown.utils import logger
```

### Function Documentation
```python
def process_document(
    file_path: Path,
    chunk_size: int = 1000,
    overlap: int = 200
) -> List[Chunk]:
    """Process a markdown document into chunks.

    Args:
        file_path: Path to the markdown file
        chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap

    Returns:
        List of processed chunks

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If chunk_size <= overlap
    """
```

### Error Handling
```python
try:
    result = process_file(path)
except FileNotFoundError:
    logger.error(f"File not found: {path}")
    raise click.ClickException(f"File not found: {path}")
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

## Performance Considerations

### Batch Processing
- Use `asyncio` for I/O-bound operations
- Implement connection pooling for ChromaDB
- Use generators for large file processing

### Memory Management
- Stream large files instead of loading entirely
- Clear caches after batch operations
- Use weak references for temporary objects

### Optimization Tips
1. Profile with `cProfile` before optimizing
2. Use `lru_cache` for expensive computations
3. Batch ChromaDB operations (add_documents)
4. Implement progress bars for long operations

## Debugging

### Debug Mode
```bash
# Enable debug logging
export SHARD_MD_LOG_LEVEL=DEBUG
shard-md process --debug document.md

# Use Python debugger
python -m pdb -m shard_markdown.cli.main process document.md
```

### Common Issues

1. **ChromaDB Connection**
   - Check server is running: `curl http://localhost:8000/api/v1`
   - Verify firewall settings
   - Check SSL configuration

2. **Memory Issues**
   - Reduce batch size
   - Enable streaming mode
   - Increase system memory limits

3. **Encoding Errors**
   - Ensure UTF-8 encoding
   - Handle BOM markers
   - Validate input files

## Pull Request Guidelines

### Before Submitting
1. Run all tests: `pytest`
2. Format code: `ruff format src/ tests/`
3. Lint code: `ruff check src/ tests/`
4. Type check: `mypy src/`
5. Update documentation if needed
6. Add tests for new features

### PR Description Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```
