# Python Development Best Practices & Guidelines

This document outlines the Python coding standards, development guidelines, and testing practices for the shard-markdown repository.

## Code Quality Standards

### Formatting and Linting

The project uses **Ruff** as the primary linting and formatting tool, configured in `pyproject.toml`:

- **Line length**: 88 characters
- **Target Python version**: 3.12+
- **Formatting**: Ruff format (replaces Black)
- **Import sorting**: Integrated with Ruff

#### Running Code Quality Checks

```bash
# Format code
ruff format src/ tests/

# Lint and fix code
ruff check --fix src/ tests/

# Type checking
mypy src/
```

### Enabled Ruff Rules

- **E, W**: pycodestyle errors and warnings
- **F**: pyflakes
- **B**: bugbear (flake8-bugbear equivalents)
- **C4**: comprehensions (flake8-comprehensions equivalents)
- **D**: pydocstyle (Google convention)
- **I**: isort
- **N**: pep8-naming
- **UP**: pyupgrade
- **S**: bandit security checks

### Type Checking

- **Tool**: MyPy with strict configuration
- **Requirements**:
  - All functions must have type annotations
  - No untyped definitions allowed
  - Strict equality checks enabled

## Python Best Practices

### Code Structure

```python
# Standard library imports first
import os
from pathlib import Path
from typing import Optional, Dict, Any

# Third-party imports
import click
from pydantic import BaseModel
from rich.console import Console

# Local imports
from shard_markdown.core.models import ChunkMetadata
from shard_markdown.utils.errors import ValidationError
```

### Error Handling

```python
# Use custom exceptions from utils.errors
from shard_markdown.utils.errors import ShardMarkdownError, ValidationError

def process_document(path: Path) -> None:
    """Process a markdown document with proper error handling."""
    try:
        validate_file_path(path)
        content = load_document(path)
        chunks = chunk_document(content)
    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
        raise
    except ShardMarkdownError as e:
        logger.error(f"Processing failed: {e}")
        raise
```

### Configuration Management

- Use Pydantic models for configuration validation
- Support YAML configuration files with precedence:
  1. `~/.shard-md/config.yaml` (global)
  2. `./.shard-md/config.yaml` (project-local)
  3. `./shard-md.yaml` (project root)

### Logging

```python
from shard_markdown.utils.logging import get_logger

logger = get_logger(__name__)

def process_file(file_path: Path) -> None:
    """Process file with proper logging."""
    logger.info(f"Processing file: {file_path}")
    try:
        # processing logic
        logger.debug("File processed successfully")
    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")
        raise
```

## Development Guidelines

### Project Structure

```
src/shard_markdown/
├── __init__.py              # Package initialization
├── __main__.py              # Entry point for -m execution
├── cli/                     # CLI interface
│   ├── __init__.py
│   ├── main.py             # Main CLI entry point
│   └── commands/           # Command modules
├── core/                   # Core processing logic
│   ├── __init__.py
│   ├── models.py           # Data models
│   ├── processor.py        # Main processing engine
│   └── chunking/           # Chunking strategies
├── chromadb/               # ChromaDB integration
├── config/                 # Configuration management
└── utils/                  # Utility modules
```

### Dependency Management

- Use `uv` for dependency management
- Pin dependencies with version ranges in `pyproject.toml`
- Separate development dependencies in `[project.optional-dependencies]`

### Pre-commit Hooks

Install and use pre-commit hooks:

```bash
pre-commit install
```

Configured hooks:
- Ruff formatting and linting
- MyPy type checking
- Security scanning with Bandit
- Dependency vulnerability checks with Safety

### Documentation Standards

- **Docstring convention**: Google style
- **Coverage**: All public functions and classes must have docstrings
- **Examples**: Include usage examples in docstrings for complex functions

```python
def chunk_document(content: str, chunk_size: int = 1000) -> List[str]:
    """Chunk a document into smaller pieces.

    Args:
        content: The document content to chunk.
        chunk_size: Maximum size of each chunk in characters.

    Returns:
        List of document chunks.

    Raises:
        ValueError: If chunk_size is less than 1.

    Example:
        >>> chunks = chunk_document("Long document...", chunk_size=500)
        >>> len(chunks)
        3
    """
```

## Testing Guidelines

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared test configuration
├── unit/                    # Unit tests
│   ├── core/
│   ├── cli/
│   └── config/
├── integration/             # Integration tests
├── e2e/                     # End-to-end tests
└── performance/             # Performance benchmarks
```

### Testing Framework

- **Primary**: pytest with plugins
- **Coverage**: pytest-cov
- **Mocking**: pytest-mock
- **Async**: pytest-asyncio
- **Benchmarks**: pytest-benchmark

### Test Categories

Mark tests with appropriate markers:

```python
import pytest

@pytest.mark.unit
def test_chunk_creation():
    """Unit test for chunk creation."""
    pass

@pytest.mark.integration
def test_chromadb_integration():
    """Integration test with ChromaDB."""
    pass

@pytest.mark.e2e
def test_full_workflow():
    """End-to-end workflow test."""
    pass

@pytest.mark.slow
def test_large_document_processing():
    """Slow test for large documents."""
    pass
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=shard_markdown

# Run specific categories
pytest -m unit                    # Unit tests only
pytest -m integration            # Integration tests only
pytest -m "not slow"             # Exclude slow tests

# Run with output
pytest -v -s
```

### Test Coverage Requirements

- **Minimum coverage**: 85%
- **Core modules**: 90%+ coverage required
- **Exclusions**: Test files, abstract methods, debug code

### Testing Best Practices

1. **Arrange-Act-Assert** pattern
2. **Descriptive test names** explaining what is being tested
3. **Mock external dependencies** in unit tests
4. **Use fixtures** for common test data
5. **Test edge cases** and error conditions

```python
def test_chunk_document_with_empty_content():
    """Test chunking behavior with empty content."""
    # Arrange
    content = ""
    chunk_size = 1000

    # Act
    result = chunk_document(content, chunk_size)

    # Assert
    assert result == []

def test_chunk_document_raises_on_invalid_size():
    """Test that invalid chunk size raises ValueError."""
    with pytest.raises(ValueError, match="Chunk size must be positive"):
        chunk_document("content", chunk_size=0)
```

### Continuous Integration

The project uses GitHub Actions for CI/CD:

- **Code quality**: Ruff formatting and linting
- **Type checking**: MyPy validation
- **Security**: Bandit security scanning
- **Testing**: Full test suite with coverage reporting
- **Dependency checking**: Safety vulnerability scanning

### Performance Considerations

- **Batch processing**: Use concurrent execution for multiple files
- **Memory management**: Process large files in chunks
- **Caching**: Cache expensive operations where appropriate
- **Profiling**: Use pytest-benchmark for performance testing

### Security Best Practices

- **Input validation**: Validate all user inputs
- **Path traversal protection**: Use pathlib.Path for file operations
- **Secret management**: Never log or commit secrets
- **Dependency scanning**: Regular security audits with Bandit and Safety

## Development Workflow

1. **Create feature branch** from main
2. **Install development dependencies**: `uv pip install -e ".[dev]"`
3. **Install pre-commit hooks**: `pre-commit install`
4. **Write code** following guidelines above
5. **Run linting and formatting** (**MUST** be done after any changes in src/ or tests/):
   ```bash
   ruff format src/ tests/
   ruff check --fix src/ tests/
   ```
6. **Run type checking** (**MUST** be done after any changes in src/ or tests/):
   ```bash
   mypy src/
   ```
7. **Write tests** with appropriate coverage
8. **Run test suite**:
   ```bash
   pytest
   ```
9. **Commit changes** with descriptive messages
10. **Submit pull request** with test coverage and documentation

## Agent Instructions

### **CRITICAL: Type Safety and CI/CD Prevention Rules**

**MANDATORY CHECKS**: After creating or modifying ANY Python file, agents MUST run ALL of the following checks in sequence:

1. **Linting and Formatting** (REQUIRED):
   ```bash
   ruff format src/ tests/
   ruff check --fix src/ tests/
   ```

2. **Type Checking** (CRITICAL - CI/CD BLOCKER):
   ```bash
   mypy src/ tests/
   ```

3. **Pre-commit Validation** (RECOMMENDED):
   ```bash
   pre-commit run --all-files
   ```

### **Type Safety Requirements**

**NEVER commit code that fails MyPy type checking.** The following patterns MUST be avoided as they cause CI/CD failures:

#### **1. Optional/Union Attribute Access**
```python
# ❌ WRONG - Will cause CI/CD failure
assert "error" in result.error.lower()  # result.error could be None

# ✅ CORRECT - Add None check first
assert result.error is not None
assert "error" in result.error.lower()
```

#### **2. Missing Type Annotations on Fixtures**
```python
# ❌ WRONG - Will cause CI/CD failure
@pytest.fixture
def sample_data(request) -> Dict[str, Any]:  # 'request' missing type
    return request.param

# ✅ CORRECT - Always type fixture parameters
@pytest.fixture
def sample_data(request: pytest.FixtureRequest) -> Dict[str, Any]:
    return request.param
```

#### **3. Untyped Decorators**
```python
# ❌ WRONG - Will cause CI/CD failure
@field_validator("field_name")
@classmethod
def validate_field(cls, v: str) -> str:  # Decorator typing issue

# ✅ CORRECT - Add type ignore for Pydantic decorators
@field_validator("field_name")  # type: ignore[misc]
@classmethod
def validate_field(cls, v: str) -> str:
```

#### **4. Generator Return Types**
```python
# ❌ WRONG - Will cause CI/CD failure
def data_generator():
    yield item

# ✅ CORRECT - Specify Generator return type
from typing import Generator

def data_generator() -> Generator[ItemType, None, None]:
    yield item
```

### **Development Workflow Enforcement**

**BEFORE making ANY commit, agents MUST:**

1. **Verify Local Type Checking**: `mypy src/ tests/` returns exit code 0
2. **Verify All Linting**: `ruff check src/ tests/` returns exit code 0
3. **Verify Pre-commit Hooks**: `pre-commit run --all-files` passes all checks
4. **Run Affected Tests**: Ensure no regressions introduced

### **CI/CD Failure Response Protocol**

**If ANY CI/CD check fails after your changes:**

1. **IMMEDIATELY investigate** using available tools (Bash, Grep, Read)
2. **NEVER ignore type errors** - they indicate potential runtime bugs
3. **FIX ALL MyPy errors** before proceeding with other tasks
4. **VALIDATE fixes locally** before pushing additional commits
5. **DOCUMENT lessons learned** for future prevention

### **Preventive Measures**

**To prevent CI/CD failures, agents should:**

1. **Use strict typing practices** from the start of any code changes
2. **Test edge cases** including None values and empty collections
3. **Add type annotations proactively** rather than reactively
4. **Validate type safety** as part of every development task
5. **Monitor for new type checking rules** in MyPy configuration updates

### **Legacy Code Handling**

**When working with existing code that has type issues:**

1. **Fix type errors** in files you modify (don't ignore them)
2. **Add gradual typing** improvements where possible
3. **Document type improvements** in commit messages
4. **Consider broader type safety improvements** for the module

**Example Workflow**: If you've modified files in `src/shard_markdown/core/`, run:

```bash
# 1. Format and lint
ruff format src/ tests/
ruff check --fix src/ tests/

# 2. Type check (CRITICAL)
mypy src/ tests/

# 3. Validate with pre-commit
pre-commit run --all-files

# 4. Run affected tests
pytest tests/unit/core/ -v
```

**FAILURE IS NOT AN OPTION**: Type checking failures block the entire CI/CD pipeline and prevent deployments. Always prioritize type safety compliance.

This ensures code quality and adherence to project standards before proceeding with additional tasks.

## Environment Setup

```bash
# Clone repository
git clone https://github.com/shard-markdown/shard-markdown.git
cd shard-markdown

# Install with development dependencies
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Verify setup
pytest --version
ruff --version
mypy --version
```

This ensures consistent development practices across the team and maintains high code quality standards.


# COMMIT RULES
- Allows use amend commits with "--amend{ option, if pull request already open for the branch.
