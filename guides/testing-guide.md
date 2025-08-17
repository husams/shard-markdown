# Testing Guide

## Testing Framework

The project uses `pytest` as the primary testing framework with the following extensions:
- `pytest-cov`: Code coverage reporting
- `pytest-asyncio`: Async test support
- `pytest-mock`: Mocking utilities
- `pytest-timeout`: Test timeout management

## Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_chunker.py     # Chunking algorithm tests
│   ├── test_processor.py   # Processing pipeline tests
│   └── test_metadata.py    # Metadata extraction tests
├── integration/            # Integration tests
│   ├── test_chromadb.py   # ChromaDB integration
│   ├── test_cli.py        # CLI command tests
│   └── test_pipeline.py   # End-to-end pipeline
├── fixtures/              # Test data and fixtures
│   ├── documents/         # Sample markdown files
│   └── configs/          # Test configurations
└── conftest.py           # Shared fixtures and configuration
```

## Running Tests

### Basic Commands
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_chunker.py

# Run specific test function
pytest tests/unit/test_chunker.py::test_structure_aware_chunking

# Run tests matching pattern
pytest -k "chunker"
```

### Coverage Reports
```bash
# Run with coverage
pytest --cov=shard_markdown

# Generate HTML coverage report
pytest --cov=shard_markdown --cov-report=html

# Show missing lines
pytest --cov=shard_markdown --cov-report=term-missing
```

### Test Categories
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run non-slow tests
pytest -m "not slow"

# Run ChromaDB tests
pytest -m chromadb
```

## Writing Tests

### Unit Test Example
```python
# tests/unit/test_chunker.py
import pytest
from shard_markdown.core.chunker import StructureAwareChunker

class TestStructureAwareChunker:
    @pytest.fixture
    def chunker(self):
        return StructureAwareChunker(chunk_size=100, overlap=20)

    def test_basic_chunking(self, chunker):
        content = "# Header\\n\\nParagraph content"
        chunks = chunker.chunk(content)

        assert len(chunks) > 0
        assert all(len(c.content) <= 100 for c in chunks)

    def test_respects_code_blocks(self, chunker):
        content = "Text\\n```python\\ncode\\n```\\nMore text"
        chunks = chunker.chunk(content)

        # Code block should not be split
        code_chunk = next(c for c in chunks if "```" in c.content)
        assert "```python" in code_chunk.content
        assert "```" in code_chunk.content

    @pytest.mark.parametrize("size,expected", [
        (50, 3),
        (100, 2),
        (200, 1),
    ])
    def test_chunk_sizes(self, size, expected):
        chunker = StructureAwareChunker(chunk_size=size)
        content = "x" * 150
        chunks = chunker.chunk(content)
        assert len(chunks) == expected
```

### Integration Test Example
```python
# tests/integration/test_chromadb.py
import pytest
from unittest.mock import Mock, patch
from shard_markdown.chromadb.client import ChromaDBClient

@pytest.mark.chromadb
class TestChromaDBIntegration:
    @pytest.fixture
    def client(self):
        with patch('chromadb.Client') as mock_client:
            yield ChromaDBClient(host="localhost", port=8000)

    @pytest.mark.asyncio
    async def test_create_collection(self, client):
        result = await client.create_collection("test-collection")
        assert result.name == "test-collection"

    def test_add_documents(self, client):
        docs = [{"content": "test", "metadata": {}}]
        client.add_documents("test-collection", docs)
        # Verify documents were added
```

### CLI Test Example
```python
# tests/integration/test_cli.py
from click.testing import CliRunner
from shard_markdown.cli.main import cli

def test_process_command():
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create test file
        with open("test.md", "w") as f:
            f.write("# Test Document\\n\\nContent")

        # Run command
        result = runner.invoke(cli, [
            "process",
            "--collection", "test",
            "test.md"
        ])

        assert result.exit_code == 0
        assert "Processing" in result.output

def test_config_show():
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "show"])

    assert result.exit_code == 0
    assert "chromadb" in result.output
```

## Test Fixtures

### Common Fixtures (`conftest.py`)
```python
# tests/conftest.py
import pytest
from pathlib import Path
import tempfile

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_markdown():
    """Sample markdown content."""
    return """
# Main Title

## Section 1
Content for section 1.

## Section 2
Content for section 2.

```python
def example():
    return "code"
```
"""

@pytest.fixture
def mock_chromadb_client(mocker):
    """Mock ChromaDB client."""
    client = mocker.Mock()
    client.list_collections.return_value = []
    return client

@pytest.fixture(scope="session")
def test_config():
    """Test configuration."""
    return {
        "chromadb": {
            "host": "localhost",
            "port": 8000
        },
        "chunking": {
            "default_size": 1000,
            "default_overlap": 200
        }
    }
```

## Mocking

### Mocking External Services
```python
from unittest.mock import patch, Mock

@patch('shard_markdown.chromadb.client.chromadb.Client')
def test_with_mock_chromadb(mock_client):
    # Configure mock
    mock_instance = Mock()
    mock_client.return_value = mock_instance
    mock_instance.list_collections.return_value = []

    # Test code
    from shard_markdown.chromadb.client import ChromaDBClient
    client = ChromaDBClient()
    collections = client.list_collections()

    # Assertions
    assert collections == []
    mock_instance.list_collections.assert_called_once()
```

### Using pytest-mock
```python
def test_with_mocker(mocker):
    # Mock a function
    mock_func = mocker.patch('shard_markdown.core.processor.process_file')
    mock_func.return_value = {"status": "success"}

    # Test code
    from shard_markdown.core.processor import process_file
    result = process_file("test.md")

    # Assertions
    assert result["status"] == "success"
    mock_func.assert_called_with("test.md")
```

## Test Data Management

### Using Fixtures Directory
```python
@pytest.fixture
def test_document(request):
    """Load test document from fixtures."""
    fixture_dir = Path(request.fspath).parent / "fixtures" / "documents"
    doc_path = fixture_dir / "sample.md"
    return doc_path.read_text()
```

### Generating Test Data
```python
@pytest.fixture
def large_document():
    """Generate large test document."""
    sections = []
    for i in range(100):
        sections.append(f"## Section {i}\\n\\nContent for section {i}\\n")
    return "\\n".join(sections)
```

## Performance Testing

### Benchmarking
```python
import pytest
import time

@pytest.mark.benchmark
def test_chunking_performance(benchmark, large_document):
    from shard_markdown.core.chunker import StructureAwareChunker
    chunker = StructureAwareChunker()

    # Benchmark the chunking operation
    result = benchmark(chunker.chunk, large_document)

    # Performance assertions
    assert benchmark.stats["mean"] < 1.0  # Less than 1 second
```

### Load Testing
```python
@pytest.mark.slow
@pytest.mark.timeout(30)
def test_batch_processing():
    """Test processing multiple documents."""
    documents = [f"doc{i}.md" for i in range(100)]
    start = time.time()

    # Process documents
    results = process_batch(documents)

    duration = time.time() - start
    assert duration < 30  # Should complete within 30 seconds
    assert len(results) == 100
```

## Debugging Tests

### Using pytest debugger
```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger at start of test
pytest --trace

# Show local variables on failure
pytest -l
```

### Debugging specific test
```python
def test_complex_logic():
    # Add breakpoint
    import pdb; pdb.set_trace()

    # Or use pytest.set_trace()
    pytest.set_trace()

    # Test logic
    result = complex_function()
    assert result == expected
```

## CI/CD Testing

### GitHub Actions Configuration
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      - name: Run tests
        run: |
          pytest --cov=shard_markdown --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Test Best Practices

### 1. Test Organization
- One test class per module/class being tested
- Group related tests together
- Use descriptive test names

### 2. Test Independence
- Each test should be independent
- Use fixtures for setup/teardown
- Avoid test order dependencies

### 3. Assertions
- One logical assertion per test
- Use specific assertions (pytest.raises, etc.)
- Include helpful assertion messages

### 4. Test Coverage Goals
- Aim for >80% code coverage
- Focus on critical paths
- Test edge cases and error conditions

### 5. Performance
- Mark slow tests with @pytest.mark.slow
- Use test categories for selective running
- Mock external dependencies

## Troubleshooting

### Common Issues

1. **ChromaDB Connection Errors**
   ```bash
   # Start ChromaDB for tests
   docker run -d -p 8000:8000 chromadb/chroma

   # Or mock ChromaDB in tests
   ```

2. **Import Errors**
   ```bash
   # Ensure package is installed
   pip install -e .

   # Check PYTHONPATH
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
   ```

3. **Fixture Not Found**
   ```python
   # Ensure conftest.py is in test directory
   # Check fixture scope and naming
   ```

4. **Async Test Issues**
   ```python
   # Use pytest.mark.asyncio
   @pytest.mark.asyncio
   async def test_async_function():
       result = await async_function()
       assert result
   ```

## Manual Testing Checklist

### Pre-Testing Setup

#### Environment Preparation
- [ ] Virtual environment activated
- [ ] Latest dependencies installed (`uv pip install -e ".[dev]"`)
- [ ] ChromaDB running (if testing real integration)
- [ ] Test data directory prepared
- [ ] Previous test artifacts cleaned up

#### Test Data Preparation
```bash
# Create test directory structure
mkdir -p manual_tests/{simple,complex,large,edge_cases}

# Simple test documents
echo "# Simple Document
This is a basic test document.
## Section 1
Content here." > manual_tests/simple/basic.md
```

### Core CLI Testing

#### Process Command Tests
- [ ] Process single markdown file
- [ ] Process directory of files
- [ ] Process with custom chunk size
- [ ] Process with overlap settings
- [ ] Process with different chunking strategies
- [ ] Handle missing input files gracefully
- [ ] Handle permission errors

#### Collection Management Tests
- [ ] List available collections
- [ ] Create new collection
- [ ] Query existing collection
- [ ] Delete collection
- [ ] Handle connection errors

#### Configuration Tests
- [ ] Show current configuration
- [ ] Override with environment variables
- [ ] Use custom config files
- [ ] Validate configuration errors

### Testing Strategy Framework

#### Testing Philosophy
- **Test-Driven Development (TDD)**: Core functionality developed with tests first
- **Behavior-Driven Testing**: Tests describe user scenarios and expected outcomes
- **Layered Testing**: Unit, integration, and end-to-end tests provide complete coverage
- **Performance Testing**: Ensures tool performs well under various conditions
- **Cross-Platform Testing**: Validates functionality across operating systems

#### Testing Stack Dependencies
```toml
[tool.poetry.group.test.dependencies]
pytest = "^7.4.0"
pytest-cov = "^4.1.0"           # Coverage reporting
pytest-mock = "^3.11.0"         # Mocking utilities
pytest-asyncio = "^0.21.0"      # Async testing support
pytest-benchmark = "^4.0.0"     # Performance benchmarking
pytest-xdist = "^3.3.0"         # Parallel test execution
factory-boy = "^3.3.0"          # Test data generation
faker = "^19.6.0"               # Fake data generation
```

#### Test Organization Best Practices
- **Unit Tests**: Fast, isolated tests for individual components
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Full workflow validation
- **Performance Tests**: Load and benchmark testing
- **Smoke Tests**: Quick validation of basic functionality
