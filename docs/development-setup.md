# Development Setup

## Prerequisites
- Python 3.12+
- uv package manager
- Docker (for ChromaDB testing)

## Initial Setup

1. Clone repository:
```bash
git clone https://github.com/husams/shard-markdown.git
cd shard-markdown
```

2. Install with all dependencies:
```bash
uv pip install -e ".[chromadb]"
uv pip install --group dev
```

3. Install pre-commit hooks:
```bash
pre-commit install
```

4. Run tests to verify setup:
```bash
pytest
```

## Running Tests

### Unit tests only:
```bash
pytest -m unit
```

### With ChromaDB (requires Docker):
```bash
docker run -d -p 8000:8000 chromadb/chroma
pytest -m e2e
```

### Performance tests:
```bash
pytest tests/performance/ --benchmark-only
```

## Development Environment Configuration

### Virtual Environment Setup

```bash
# Create virtual environment (if not using uv)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate     # On Windows

# Install with uv (recommended)
pip install uv
uv pip install -e ".[chromadb]"
uv pip install --group dev
```

### IDE Configuration

#### VS Code Setup

Create `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "none",
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": true,
            "source.organizeImports.ruff": true
        }
    },
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/unit/"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true,
        "**/htmlcov": true,
        "**/.coverage": true,
        "**/.mypy_cache": true,
        "**/.ruff_cache": true
    }
}
```

#### PyCharm Setup

1. Set Python interpreter to your virtual environment
2. Install Ruff plugin
3. Configure Ruff as the formatter and linter
4. Set pytest as the test runner

### Environment Variables

Create a `.env` file for development:

```bash
# ChromaDB Configuration
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_SSL=false

# Development Settings
SHARD_MD_LOG_LEVEL=DEBUG
SHARD_MD_CHUNK_SIZE=1000
SHARD_MD_MAX_WORKERS=2

# Testing
PYTEST_CURRENT_TEST=true
```

## Development Workflow

### 1. Code Quality

Always run before committing:

```bash
# Format code
ruff format src/ tests/

# Lint and fix issues
ruff check --fix src/ tests/

# Type checking
mypy src/
```

### 2. Testing Strategy

#### Test Categories

- **Unit tests** (`tests/unit/`): Fast, isolated tests
- **Integration tests** (`tests/integration/`): Component interaction tests
- **E2E tests** (`tests/e2e/`): Full workflow tests with ChromaDB
- **Performance tests** (`tests/performance/`): Benchmark and performance tests

#### Running Different Test Suites

```bash
# Fast tests only (unit)
pytest -m unit

# All tests except slow ones
pytest -m "not slow"

# Integration tests (may require ChromaDB)
pytest -m integration

# E2E tests (requires ChromaDB running)
pytest -m e2e

# Performance benchmarks
pytest -m benchmark --benchmark-only

# All tests with coverage
pytest --cov=src/shard_markdown --cov-report=html
```

#### Test Configuration

The project uses `pytest.ini` for test configuration:

```ini
[tool:pytest]
minversion = 6.0
addopts = -ra -q --strict-markers --strict-config
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests
    benchmark: Performance benchmarks
```

### 3. Debugging

#### Enable Debug Logging

```bash
export SHARD_MD_LOG_LEVEL=DEBUG
python -m shard_markdown.cli.main --help
```

#### Using Debugger

```python
import pdb; pdb.set_trace()  # Add breakpoints
```

Or use your IDE's built-in debugger.

#### ChromaDB Debugging

Start ChromaDB with logging:

```bash
docker run -p 8000:8000 -e CHROMA_LOG_LEVEL=DEBUG chromadb/chroma
```

### 4. Pre-commit Hooks

Pre-commit hooks run automatically on commit. To run manually:

```bash
# Run all hooks
pre-commit run --all-files

# Run specific hook
pre-commit run ruff
pre-commit run mypy
```

## ChromaDB Setup for Development

### Local ChromaDB Instance

#### Using Docker (Recommended)

```bash
# Start ChromaDB server
docker run -d \
  --name chromadb \
  -p 8000:8000 \
  -v chromadb_data:/chroma/chroma \
  chromadb/chroma:latest

# Stop ChromaDB
docker stop chromadb

# Remove container
docker rm chromadb
```

#### Using Docker Compose

Create `docker-compose.dev.yml`:

```yaml
version: '3.8'
services:
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chromadb_data:/chroma/chroma
    environment:
      - CHROMA_LOG_LEVEL=INFO

volumes:
  chromadb_data:
```

Start with:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### Testing ChromaDB Connection

```python
import chromadb

# Test connection
client = chromadb.HttpClient(host="localhost", port=8000)
print(client.heartbeat())  # Should return timestamp

# List collections
collections = client.list_collections()
print(f"Found {len(collections)} collections")
```

## Performance Optimization

### Development Best Practices

1. **Use async/await** for I/O operations where possible
2. **Batch operations** when processing multiple documents
3. **Profile code** using `cProfile` or `line_profiler`
4. **Monitor memory usage** during development

### Profiling

```bash
# Profile script execution
python -m cProfile -o profile.stats script.py

# Analyze results
python -c "
import pstats
stats = pstats.Stats('profile.stats')
stats.sort_stats('cumulative').print_stats(20)
"
```

### Memory Profiling

```bash
pip install memory-profiler
python -m memory_profiler script.py
```

## Documentation Development

### Building Documentation

If using Sphinx (future enhancement):

```bash
# Install docs dependencies
uv pip install --group docs  # If configured

# Build HTML docs
cd docs/
make html

# Serve locally
python -m http.server 8080 -d _build/html/
```

### Documentation Standards

- Follow Google docstring style
- Include examples in docstrings
- Update README.md for significant changes
- Add troubleshooting entries for common issues

## Release Process (for Maintainers)

### Version Bumping

```bash
# Update version in pyproject.toml
# Create changelog entry
# Commit changes
git add .
git commit -m "chore: bump version to X.Y.Z"

# Create and push tag
git tag v1.0.0
git push origin v1.0.0
```

### Testing Release

```bash
# Build package
python -m build

# Check package
twine check dist/*

# Test upload to TestPyPI
twine upload --repository testpypi dist/*
```

## Troubleshooting Development Issues

### Common Setup Problems

1. **Import errors**: Ensure you installed with `-e` flag and all extras
2. **Test failures**: Check ChromaDB is running and accessible
3. **Type errors**: Install development dependencies and run `mypy`
4. **Format errors**: Run `ruff format` before committing

### Getting Help

- Check existing issues on GitHub
- Look at test files for usage examples  
- Enable debug logging for more information
- Join discussions in GitHub Discussions

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Follow the development workflow above
4. Ensure all tests pass: `pytest`
5. Ensure code quality: `ruff format` and `ruff check`
6. Submit a pull request with clear description

For detailed contribution guidelines, see [CONTRIBUTING.md](../CONTRIBUTING.md).