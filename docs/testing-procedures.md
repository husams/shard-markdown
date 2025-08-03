# Testing Procedures and Best Practices

## Overview

This document outlines the comprehensive testing procedures for the shard-markdown CLI utility, including test execution strategies, best practices, and maintenance guidelines.

## Test Suite Organization

### Directory Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── unit/                       # Unit tests (fast, isolated)
│   ├── core/
│   │   ├── test_models.py      # Data model validation
│   │   ├── test_parser.py      # Markdown parsing logic
│   │   ├── test_processor.py   # Document processing pipeline
│   │   └── test_chunking/      # Chunking algorithms
│   ├── cli/
│   │   ├── test_main.py        # Main CLI interface
│   │   └── test_process_command.py  # Process command
│   ├── config/
│   │   └── test_settings.py    # Configuration validation
│   └── utils/                  # Utility functions
├── integration/                # Integration tests
│   ├── test_document_processing.py
│   └── test_chromadb_integration.py
├── e2e/                       # End-to-end tests
│   └── test_cli_workflows.py
├── performance/               # Performance tests
│   └── test_benchmarks.py
└── fixtures/                  # Test data and resources
    ├── documents/
    ├── configs/
    └── outputs/
```

## Test Execution Procedures

### 1. Pre-Development Testing

**Purpose**: Ensure development environment is properly configured

```bash
# Verify environment setup
python -m pytest --version
python -c "import shard_markdown; print('Package importable')"

# Quick smoke test
python -m pytest tests/unit/test_parser.py::TestMarkdownParser::test_parser_initialization -v

# Dependency check
python -m pytest tests/conftest.py --collect-only
```

### 2. Development Workflow Testing

**Purpose**: Run relevant tests during active development

#### Fast Development Loop

```bash
# Run tests for current module
python -m pytest tests/unit/core/test_models.py -v

# Run with file watching (if pytest-watch installed)
ptw tests/unit/core/ -- -v

# Quick coverage check
python -m pytest tests/unit/core/ --cov=src/shard_markdown/core --cov-report=term-missing
```

#### Feature Development

```bash
# Test specific feature area
python -m pytest tests/unit/core/test_chunking/ -v

# Include integration tests
python -m pytest tests/unit/core/ tests/integration/test_document_processing.py -v

# Run with debugging
python -m pytest tests/unit/core/test_processor.py::TestDocumentProcessor::test_process_document_success -v -s --pdb
```

### 3. Pre-Commit Testing

**Purpose**: Ensure all changes pass basic quality checks

```bash
# Run all unit tests
python -m pytest tests/unit/ -v

# Check code coverage
python -m pytest tests/unit/ --cov=src/shard_markdown --cov-report=html --cov-fail-under=85

# Quick integration check
python -m pytest tests/integration/ -x -v

# Lint and format check
black --check src/ tests/
isort --check-only src/ tests/
flake8 src/ tests/
mypy src/
```

### 4. Continuous Integration Testing

**Purpose**: Comprehensive testing for pull requests and merges

```bash
# Full test suite (excluding performance)
python -m pytest tests/ -m "not performance" --cov=src/shard_markdown --cov-report=xml

# Performance baseline (if needed)
python -m pytest tests/performance/ --benchmark-only --benchmark-save=baseline

# Cross-platform testing (varies by CI system)
python -m pytest tests/ --platform=linux
python -m pytest tests/ --platform=windows
python -m pytest tests/ --platform=macos
```

### 5. Release Testing

**Purpose**: Final validation before release

```bash
# Complete test suite
python -m pytest tests/ --cov=src/shard_markdown --cov-report=html

# Performance benchmarks
python -m pytest tests/performance/ --benchmark-compare=baseline

# End-to-end validation
python -m pytest tests/e2e/ -v --tb=short

# Package installation test
uv pip install -e .
shard-md --help
shard-md --version
```

## Test Development Guidelines

### 1. Unit Test Best Practices

#### Test Structure

```python
class TestComponentName:
    """Test suite for ComponentName class."""

    @pytest.fixture
    def component(self):
        """Create component instance for testing."""
        return ComponentName(config)

    def test_basic_functionality(self, component):
        """Test basic functionality."""
        # Arrange
        input_data = "test input"
        expected_output = "expected result"

        # Act
        result = component.process(input_data)

        # Assert
        assert result == expected_output

    def test_error_condition(self, component):
        """Test error handling."""
        with pytest.raises(ExpectedError):
            component.process(invalid_input)
```

#### Naming Conventions

- Test files: `test_<module_name>.py`
- Test classes: `TestClassName`
- Test methods: `test_<functionality_being_tested>`
- Fixtures: `<resource_name>` (descriptive, no test_ prefix)

#### Test Categories

```python
@pytest.mark.unit
def test_unit_functionality():
    """Fast, isolated test."""
    pass

@pytest.mark.integration
def test_integration_workflow():
    """Test component interactions."""
    pass

@pytest.mark.e2e
def test_end_to_end_scenario():
    """Full system test."""
    pass

@pytest.mark.performance
def test_performance_benchmark():
    """Performance measurement."""
    pass

@pytest.mark.slow
def test_time_consuming_operation():
    """Test that takes significant time."""
    pass
```

### 2. Mock and Fixture Guidelines

#### Effective Mocking

```python
# Mock external dependencies
@pytest.fixture
def mock_chromadb_client():
    """Mock ChromaDB client."""
    with patch('module.ChromaDBClient') as mock:
        client = Mock()
        client.connect.return_value = True
        mock.return_value = client
        yield client

# Use dependency injection for testability
class DocumentProcessor:
    def __init__(self, config, chromadb_client=None):
        self.config = config
        self.chromadb_client = chromadb_client or ChromaDBClient(config.chromadb)
```

#### Fixture Design

```python
# Scope fixtures appropriately
@pytest.fixture(scope="session")
def expensive_setup():
    """One-time setup for entire test session."""
    setup_data = create_expensive_resource()
    yield setup_data
    cleanup_expensive_resource(setup_data)

@pytest.fixture
def test_data():
    """Fresh test data for each test."""
    return {"key": "value"}

# Parameterized fixtures for multiple scenarios
@pytest.fixture(params=[100, 500, 1000])
def chunk_size(request):
    """Test with different chunk sizes."""
    return request.param
```

### 3. CLI Testing Strategies

#### Direct Command Testing

```python
def test_cli_command_direct():
    """Test CLI command directly."""
    from click.testing import CliRunner
    from mymodule import cli

    runner = CliRunner()
    result = runner.invoke(cli, ['command', '--option', 'value'])

    assert result.exit_code == 0
    assert "expected output" in result.output
```

#### Isolated Runner Testing

```python
def test_cli_isolated():
    """Test CLI in isolated environment."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create test files
        with open('test.md', 'w') as f:
            f.write('# Test\nContent')

        # Run command
        result = runner.invoke(cli, ['process', '--collection', 'test', 'test.md'])
        assert result.exit_code == 0
```

### 4. Integration Testing Patterns

#### Database Integration

```python
@pytest.mark.integration
def test_chromadb_integration():
    """Test with real ChromaDB instance."""
    # Use test containers or mock server
    with TestChromaDBServer() as server:
        client = ChromaDBClient(server.config)
        # Test real operations
        assert client.connect()
```

#### File System Testing

```python
def test_file_processing(tmp_path):
    """Test file operations."""
    # Create test files
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test\nContent")

    # Process
    result = processor.process_document(test_file, "collection")

    # Verify
    assert result.success
    assert test_file.exists()  # Original file preserved
```

## Test Data Management

### 1. Test Fixtures

#### Document Fixtures

```python
@pytest.fixture
def simple_markdown():
    """Simple markdown document."""
    return """# Title

Introduction paragraph.

## Section 1
Content for section 1.
"""

@pytest.fixture
def complex_markdown():
    """Complex markdown with frontmatter and code."""
    return """---
title: "Complex Doc"
author: "Test"
---

# Complex Document

## Code Example
```python
def example():
    return "hello"
```

"""

```

#### Configuration Fixtures
```python
@pytest.fixture
def test_config():
    """Test configuration."""
    return AppConfig(
        chromadb=ChromaDBConfig(host="localhost", port=8000),
        chunking=ChunkingConfig(chunk_size=500, overlap=100)
    )
```

### 2. Test Data Generation

#### Dynamic Test Data

```python
def generate_large_document(sections=100):
    """Generate large test document."""
    content = ["# Large Document\n\n"]
    for i in range(sections):
        content.append(f"## Section {i}\n")
        content.append(f"Content for section {i}.\n\n")
    return "".join(content)

@pytest.fixture(params=[10, 50, 100])
def variable_document(request):
    """Document with variable size."""
    return generate_large_document(request.param)
```

## Error Testing Procedures

### 1. Exception Testing

```python
def test_error_conditions():
    """Test various error conditions."""
    # Expected exceptions
    with pytest.raises(ValidationError):
        ComponentName(invalid_config)

    # Error message validation
    with pytest.raises(ProcessingError) as exc_info:
        component.process(bad_input)
    assert "specific error message" in str(exc_info.value)
```

### 2. Edge Case Testing

```python
@pytest.mark.parametrize("input_value,expected", [
    ("", ProcessingError),           # Empty input
    ("a" * 1000000, ProcessingError), # Too large
    (None, TypeError),               # None input
    ("invalid\x00content", ProcessingError), # Invalid characters
])
def test_edge_cases(input_value, expected):
    """Test edge cases."""
    with pytest.raises(expected):
        component.process(input_value)
```

## Performance Testing Procedures

### 1. Benchmark Testing

```python
def test_processing_performance(benchmark):
    """Benchmark processing performance."""
    result = benchmark(processor.process_document, test_file, "collection")
    assert result.success
    # benchmark object automatically captures timing

def test_memory_usage():
    """Test memory usage patterns."""
    import psutil
    import os

    process = psutil.Process(os.getpid())
    baseline = process.memory_info().rss

    # Perform operation
    processor.process_large_document(large_file)

    peak = process.memory_info().rss
    increase = (peak - baseline) / 1024 / 1024  # MB

    assert increase < 100, f"Memory usage too high: {increase}MB"
```

### 2. Load Testing

```python
def test_concurrent_processing():
    """Test concurrent processing capacity."""
    import concurrent.futures

    files = [create_test_file(i) for i in range(10)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(processor.process_document, f, "collection")
            for f in files
        ]

        results = [f.result() for f in futures]

    assert all(r.success for r in results)
```

## Continuous Testing Procedures

### 1. Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest-unit
        entry: pytest tests/unit/
        language: system
        pass_filenames: false

      - id: coverage-check
        name: coverage-check
        entry: pytest tests/unit/ --cov=src/shard_markdown --cov-fail-under=80
        language: system
        pass_filenames: false
```

### 2. CI/CD Pipeline Testing

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11, 3.12]
        os: [ubuntu-latest, windows-latest, macos-latest]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v3
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          uv pip install -e ".[dev]"

      - name: Run unit tests
        run: pytest tests/unit/ --cov=src/shard_markdown --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Test Maintenance Procedures

### 1. Regular Maintenance Tasks

#### Weekly

- Review test failures and flaky tests
- Update test data and fixtures as needed
- Check test execution times and optimize slow tests

#### Monthly

- Review test coverage reports
- Update test documentation
- Refactor redundant or outdated tests

#### Quarterly

- Comprehensive test suite review
- Performance baseline updates
- Test infrastructure improvements

### 2. Test Quality Metrics

#### Coverage Targets

- **Unit tests**: >90% line coverage
- **Integration tests**: >80% workflow coverage
- **E2E tests**: 100% critical path coverage

#### Performance Targets

- **Unit test execution**: <2 minutes total
- **Integration tests**: <10 minutes total
- **E2E tests**: <30 minutes total

#### Quality Indicators

- Test reliability: >98% pass rate
- Test maintainability: Clear, readable test code
- Test documentation: Complete procedure coverage

## Troubleshooting Common Issues

### 1. Test Environment Issues

```bash
# Clean test environment
rm -rf .pytest_cache __pycache__ .coverage htmlcov/
pip uninstall shard-markdown -y
uv pip install -e ".[dev]"

# Reset test database
rm -rf test_chromadb/
```

### 2. Mock/Fixture Issues

```python
# Debug fixture issues
pytest --fixtures tests/unit/test_module.py

# Debug specific test
pytest tests/unit/test_module.py::test_function -vv -s --pdb
```

### 3. Coverage Issues

```bash
# Detailed coverage report
pytest tests/unit/ --cov=src/shard_markdown --cov-report=html --cov-report=term-missing

# Coverage by test file
pytest tests/unit/test_module.py --cov=src/shard_markdown/module --cov-report=term-missing
```

This comprehensive testing procedure ensures reliable, maintainable, and efficient testing of the shard-markdown CLI utility across all development phases and deployment scenarios.
