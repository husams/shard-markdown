# Shard Markdown

Intelligent markdown document chunking for ChromaDB collections.

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview

Shard Markdown is a focused CLI tool that intelligently chunks markdown documents for optimal retrieval and analysis. Following the Unix philosophy of "do one thing well", it excels at breaking down markdown files into meaningful segments.

### Key Features

- **Simple Usage**: Just `shard-md document.md` - no complex subcommands
- **Structure-Aware Chunking**: Respects markdown headers, lists, and code blocks
- **Multiple Chunking Strategies**: Token, sentence, paragraph, section, semantic, structure, and fixed-size chunking
- **ChromaDB Storage**: Optional storage in vector databases with `--store`
- **Metadata Preservation**: Extracts and enhances document metadata
- **Batch Processing**: Efficiently process multiple files and directories
- **Clean Output**: Focused display of chunks with optional quiet mode
- **Flexible Configuration**: Simple YAML configuration with environment variable support

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
# Simple usage - display chunks
shard-md document.md

# Display with custom settings
shard-md docs/ --size 500 --overlap 50

# Store in ChromaDB
shard-md manual.md --store --collection documentation

# Process multiple files
shard-md *.md --store --collection my-docs --quiet

# Dry run with verbose output
shard-md large-doc.md --dry-run --verbose
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

Configuration is managed by directly editing these YAML files with any text editor. No configuration commands are needed.

### Sample Configuration

```yaml
# ~/.shard-md/config.yaml - edit with any text editor
chunk:
  size: 1000
  overlap: 200
  strategy: structure

storage:
  vectordb:
    host: localhost
    port: 8000
    collection: default

processing:
  recursive: false
  metadata: true
  preserve_structure: true

logging:
  level: INFO
  quiet: false
```

### Environment Variables

You can override configuration with environment variables:

```bash
export CHROMA_HOST=localhost
export CHROMA_PORT=8000
export SHARD_MD_CHUNK_SIZE=1500
export SHARD_MD_LOG_LEVEL=DEBUG
```

## Command-Line Options

```bash
shard-md [OPTIONS] INPUT
```

### Chunking Options
- `-s, --size INTEGER`: Chunk size (default: 1000)
- `-o, --overlap INTEGER`: Overlap between chunks (default: 200)
- `--strategy`: Chunking strategy (token/sentence/paragraph/section/semantic/structure/fixed)

### Storage Options
- `--store`: Store chunks in vector database
- `--collection TEXT`: Collection name for vectordb storage

### Processing Options
- `-r, --recursive`: Process directories recursively
- `-m, --metadata`: Include metadata in chunks
- `--preserve-structure`: Maintain markdown structure

### Utility Options
- `--dry-run`: Preview without storing
- `--config-path PATH`: Use alternate config file
- `-q, --quiet`: Suppress output (when storing)
- `-v, --verbose`: Verbose output
- `--version`: Show version
- `--help`: Show help

### Examples

```bash
# Simple usage - display chunks
shard-md README.md

# Display with custom settings
shard-md docs/ --size 500 --overlap 50

# Store in ChromaDB
shard-md manual.md --store --collection documentation

# Process directory recursively
shard-md ./docs --recursive --store --collection tech-docs

# Dry run with verbose output
shard-md large-doc.md --dry-run --verbose

# Process with custom config
shard-md book.md --config-path ./project-config.yaml

# Process and store quietly
shard-md *.md --store --collection my-docs --quiet
```

## Chunking Strategies

### Available Strategies

- **structure** (default): Respects markdown structure, never splits code blocks
- **token**: Token-based chunking for LLM compatibility
- **sentence**: Splits on sentence boundaries
- **paragraph**: Preserves paragraph integrity
- **section**: Splits on markdown headers
- **semantic**: Context-aware splitting based on meaning
- **fixed**: Simple character-based splitting with overlap

Choose a strategy with the `--strategy` option:
```bash
shard-md document.md --strategy semantic --size 1500
```

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
uv run pytest --cov=shard_markdown

# Run specific test categories
uv run pytest -m unit
pytest -m integration
```

### Code Quality

```bash
# Format code
ruff format src/ tests/

# Lint and fix code
ruff check --fix src/ tests/

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
