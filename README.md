# Shard Markdown

Intelligent markdown document chunking for ChromaDB collections.

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview

Shard Markdown is a powerful CLI tool that intelligently processes markdown documents into structured chunks and stores them in ChromaDB collections. It's designed for RAG (Retrieval-Augmented Generation) workflows, document processing pipelines, and vector database management.

### Key Features

- **Structure-Aware Chunking**: Respects markdown headers, lists, and code blocks
- **Multiple Chunking Strategies**: Structure-aware, fixed-size, and semantic chunking
- **ChromaDB Integration**: Native support for ChromaDB collections and operations
- **Metadata Preservation**: Extracts and enhances document metadata
- **Batch Processing**: Efficiently process multiple files with concurrent execution
- **Rich CLI Interface**: Beautiful terminal output with progress tracking
- **Flexible Configuration**: YAML-based configuration with environment variable support

## Quick Start

### Installation

```bash
# Install from PyPI (when available)
uv add shard-markdown

# Or install from source
git clone https://github.com/shard-markdown/shard-markdown.git
cd shard-markdown
uv pip install -e .
```

### Basic Usage

```bash
# Process a single markdown file
shard-md process --collection my-docs document.md

# Process multiple files with custom settings
shard-md process --collection tech-docs --chunk-size 1500 --recursive docs/

# List collections
shard-md collections list

# Search documents
shard-md query search "machine learning" --collection tech-docs

# Show configuration
shard-md config show
```

## Installation

### Requirements

- Python 3.8 or higher
- ChromaDB server (local or remote)

### Install from PyPI

```bash
pip shard-markdown
```

### Install from Source

```bash
git clone https://github.com/shard-markdown/shard-markdown.git
cd shard-markdown
uv sync
```

### Development Installation

```bash
git clone https://github.com/shard-markdown/shard-markdown.git
cd shard-markdown

# Install with development dependencies
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Configuration

Shard Markdown uses YAML configuration files with the following precedence:

1. `~/.shard-md/config.yaml` (global)
2. `./.shard-md/config.yaml` (project-local)
3. `./shard-md.yaml` (project root)

### Initialize Configuration

```bash
# Create default configuration
shard-md config init

# Create global configuration
shard-md config init --global

# Show current configuration
shard-md config show
```

### Sample Configuration

```yaml
chromadb:
  host: localhost
  port: 8000
  ssl: false
  timeout: 30

chunking:
  default_size: 1000
  default_overlap: 200
  method: structure
  respect_boundaries: true

processing:
  batch_size: 10
  max_workers: 4
  recursive: false
  include_frontmatter: true

logging:
  level: INFO
  file_path: null
```

### Environment Variables

You can override configuration with environment variables:

```bash
export CHROMA_HOST=localhost
export CHROMA_PORT=8000
export SHARD_MD_CHUNK_SIZE=1500
export SHARD_MD_LOG_LEVEL=DEBUG
```

## Commands

### Process Documents

Process markdown files into ChromaDB collections:

```bash
# Basic processing
shard-md process --collection my-docs document.md

# Advanced processing
shard-md process \\
  --collection technical-docs \\
  --chunk-size 1500 \\
  --chunk-overlap 300 \\
  --chunk-method structure \\
  --recursive \\
  --create-collection \\
  docs/

# Dry run (preview what would be processed)
shard-md process --collection test --dry-run *.md
```

### Manage Collections

```bash
# List collections
shard-md collections list

# Create collection
shard-md collections create my-docs --description "My documentation"

# Get collection info
shard-md collections info my-docs

# Delete collection
shard-md collections delete old-docs
```

### Query Documents

```bash
# Search documents
shard-md query search "machine learning" --collection tech-docs

# Get specific document
shard-md query get doc_123 --collection my-docs

# List documents
shard-md query list-docs --collection my-docs --limit 50
```

### Configuration Management

```bash
# Show configuration
shard-md config show

# Set configuration values
shard-md config set chromadb.host localhost
shard-md config set chunking.default_size 1500

# Show configuration file locations
shard-md config path
```

## Chunking Strategies

### Structure-Aware Chunking (Default)

Respects markdown document structure:

- Never splits code blocks
- Prefers splits at header boundaries
- Respects list item boundaries
- Maintains hierarchical context

### Fixed-Size Chunking

Creates chunks based on character limits:

- Simple character-based splitting
- Optional word boundary respect
- Configurable overlap

### Semantic Chunking

Splits based on content meaning:

- Sentence boundary detection
- Paragraph preservation
- Context-aware splitting

## Metadata

Shard Markdown automatically extracts and preserves rich metadata:

### File-Level Metadata

- File path, name, size
- Creation and modification timestamps
- File hash for integrity

### Document-Level Metadata

- YAML frontmatter
- Title, author, tags
- Document statistics

### Chunk-Level Metadata

- Position in document
- Structural context
- Parent sections
- Processing information

## Development

### Project Structure

```
shard-markdown/
├── src/shard_markdown/          # Main package
│   ├── cli/                     # CLI interface
│   ├── core/                    # Core processing
│   ├── chromadb/                # ChromaDB integration
│   ├── config/                  # Configuration management
│   └── utils/                   # Utilities
├── tests/                       # Test suite
├── docs/                        # Documentation
└── scripts/                     # Development scripts
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=shard_markdown

# Run specific test categories
pytest -m unit
pytest -m integration
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Install development dependencies: `uv pip install -e ".[dev]"`
4. Install pre-commit hooks: `pre-commit install`
5. Make your changes
6. Run tests: `pytest`
7. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [Read the Docs](https://shard-markdown.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/shard-markdown/shard-markdown/issues)
- **Discussions**: [GitHub Discussions](https://github.com/shard-markdown/shard-markdown/discussions)

## Acknowledgments

- [ChromaDB](https://www.trychroma.com/) for the excellent vector database
- [Click](https://click.palletsprojects.com/) for the CLI framework
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation
