# Development Workflow Guide

This document provides a comprehensive guide to the development workflow for the shard-markdown project, focusing on preventing CI/CD failures and maintaining high code quality.

## Quick Start for New Developers

### 1. Initial Setup

```bash
# Clone the repository
git clone https://github.com/shard-markdown/shard-markdown.git
cd shard-markdown

# Run automated setup (REQUIRED)
python scripts/setup-dev-environment.py
```

The setup script will:
- ✅ Verify Python 3.12+ installation
- ✅ Check uv package manager
- ✅ Install all dependencies
- ✅ Install pre-commit hooks (CRITICAL)
- ✅ Install pre-push hooks (CRITICAL)
- ✅ Verify development tools
- ✅ Run initial quality checks

### 2. IDE Setup (VS Code Recommended)

VS Code settings are automatically configured in `.vscode/`:
- Real-time type checking with MyPy
- Automatic formatting with Ruff
- Integrated linting and error highlighting
- Debug configurations for CLI and tests

**Required Extensions** (install these):
- Python Extension Pack
- Ruff (linting/formatting)
- MyPy (type checking)

## Development Workflow

### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards in [CLAUDE.md](../CLAUDE.md)

3. **Run quality checks frequently**:
   ```bash
   # Quick check (runs in ~10s)
   python scripts/verify.py --fast
   
   # Full check with auto-fix
   python scripts/verify.py --fix
   ```

4. **Test your changes**:
   ```bash
   # Unit tests only
   pytest tests/unit/ -v
   
   # All tests
   pytest tests/ -v
   ```

### Commit Process

When you commit, pre-commit hooks **automatically run**:

1. **Ruff formatting** - Formats your code
2. **Ruff linting** - Checks for issues
3. **MyPy type checking** - Verifies types
4. **Security scanning** - Checks for vulnerabilities
5. **YAML/JSON validation** - Validates config files

**If hooks fail**, your commit is blocked until you fix the issues.

Example output:
```bash
$ git commit -m "Add new feature"

Running pre-commit hooks...
✅ ruff-format.......................Passed
✅ ruff..................................Passed  
✅ mypy..................................Passed
✅ bandit................................Passed
✅ trailing-whitespace...................Passed
✅ end-of-file-fixer.....................Passed
✅ check-yaml............................Passed

[feature/your-feature-name abc1234] Add new feature
```

### Push Process

When you push, pre-push hooks **automatically run**:

1. **Type checking** (CRITICAL - blocks CI/CD failures)
2. **Linting** (HIGH priority)
3. **Formatting check** (HIGH priority)

Example output:
```bash
$ git push origin feature/your-feature-name

🔍 Pre-push validation starting...
▶ Running critical pre-push checks
✅ Code Formatting (ruff format) (0.89s) - PASSED
✅ Linting (ruff check) (1.12s) - PASSED  
✅ Type Checking (mypy) (2.34s) - PASSED
✅ All 3 pre-push checks passed

🎉 Pre-push validation completed successfully!
```

## Type Safety Enforcement

### Critical Anti-Patterns (CI/CD Blockers)

Based on real issues found in PR #49, these patterns **will cause CI/CD failures**:

#### 1. Optional Attribute Access
```python
# ❌ WRONG - Causes CI/CD failure
def process_result(result: Optional[Result]) -> str:
    return result.error.lower()  # result.error could be None

# ✅ CORRECT - Safe attribute access
def process_result(result: Optional[Result]) -> str:
    if result is None or result.error is None:
        return "no error"
    return result.error.lower()
```

#### 2. Untyped Fixture Parameters
```python
# ❌ WRONG - Causes CI/CD failure
@pytest.fixture
def sample_data(request) -> Dict[str, Any]:  # request not typed
    return request.param

# ✅ CORRECT - Properly typed
@pytest.fixture
def sample_data(request: pytest.FixtureRequest) -> Dict[str, Any]:
    return request.param
```

#### 3. Generator Return Types
```python
# ❌ WRONG - Causes CI/CD failure
def data_generator():
    yield item

# ✅ CORRECT - Complete typing
from typing import Generator

def data_generator() -> Generator[ItemType, None, None]:
    yield item
```

### Type Checking Commands

```bash
# Check types (CRITICAL before pushing)
mypy src/

# Check specific file
mypy src/shard_markdown/core/models.py

# Check with verbose output
mypy src/ --verbose
```

## Quality Assurance

### Verification Script Options

The `scripts/verify.py` script is your main quality assurance tool:

```bash
# Basic check (all checks)
python scripts/verify.py

# Fix formatting/linting automatically
python scripts/verify.py --fix

# Fast mode (skip slow tests)
python scripts/verify.py --fast

# Include coverage validation
python scripts/verify.py --coverage

# Exit on first failure
python scripts/verify.py --exit-early

# Verbose output
python scripts/verify.py --verbose

# CI/CD mode (optimized for automation)
python scripts/verify.py --ci

# JSON output (for scripts/automation)
python scripts/verify.py --json

# Pre-push mode (critical checks only, fast)
python scripts/verify.py --pre-push
```

### Manual Quality Checks

```bash
# Format code
ruff format src/ tests/ scripts/

# Check linting
ruff check src/ tests/ scripts/

# Fix linting issues
ruff check --fix src/ tests/ scripts/

# Type checking
mypy src/

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest --cov=shard_markdown --cov-report=term-missing tests/

# Security scanning
bandit -r src/

# Pre-commit on all files
pre-commit run --all-files
```

## CI/CD Pipeline

### GitHub Actions Workflows

1. **CI Workflow** (`.github/workflows/ci.yml`):
   - Runs on every push/PR
   - Tests multiple Python versions (3.12, 3.13)
   - Tests multiple OS (Ubuntu, Windows, macOS)
   - Includes ChromaDB integration tests

2. **Type Safety Monitoring** (`.github/workflows/type-safety-monitoring.yml`):
   - Monitors type safety trends
   - Creates GitHub issues on type regressions
   - Generates type coverage reports
   - Comments on PRs with type safety status

### CI/CD Requirements

Before any PR can be merged, all CI checks must pass:

- ✅ **Linting** - Ruff checks pass
- ✅ **Formatting** - Code is properly formatted
- ✅ **Type checking** - MyPy validation passes (CRITICAL)
- ✅ **Tests** - All unit and integration tests pass
- ✅ **Security** - Bandit security scan passes
- ✅ **Coverage** - Minimum 80% test coverage
- ✅ **Build** - Package builds successfully

### Branch Protection Rules

Main branch is protected with:
- Required status checks (all CI workflows)
- Up-to-date branches required
- No direct pushes allowed
- Dismiss stale reviews on new commits

## Troubleshooting Common Issues

### Pre-commit Hook Failures

```bash
# If pre-commit hooks fail to install
pre-commit uninstall
pre-commit install

# Update pre-commit hooks
pre-commit autoupdate

# Skip hooks temporarily (NOT RECOMMENDED)
git commit --no-verify -m "message"
```

### Type Checking Issues

```bash
# Common MyPy issues and solutions

# Issue: Import not found
# Solution: Add to [[tool.mypy.overrides]] in pyproject.toml
ignore_missing_imports = true

# Issue: Untyped function
# Solution: Add type annotations
def function(param: str) -> str:
    return param

# Issue: Optional access
# Solution: Add None checks
if value is not None:
    return value.method()
```

### Development Environment Issues

```bash
# Reset development environment
python scripts/setup-dev-environment.py

# Check environment health
python scripts/verify.py --verbose

# Reinstall dependencies
uv sync --dev --extra chromadb

# Clear caches
rm -rf .mypy_cache .ruff_cache .pytest_cache
```

## Performance Optimization

### Fast Development Cycle

For rapid iteration:

```bash
# Quick type check on specific file
mypy src/shard_markdown/core/models.py

# Fast test subset
pytest tests/unit/ -x  # Stop on first failure

# Format only changed files
ruff format $(git diff --name-only HEAD~1 | grep '\.py$')

# Quick verification (skips slow tests)
python scripts/verify.py --fast --exit-early
```

### Parallel Development

When working on multiple features:

```bash
# Stash current changes
git stash

# Switch to different feature
git checkout feature/other-feature

# Apply stash to new branch
git stash pop

# Quick context switch validation
python scripts/verify.py --pre-push
```

## Best Practices Summary

### 🎯 Critical Success Factors

1. **Always run setup script** on new environment setup
2. **Never bypass pre-commit/pre-push hooks** in normal development
3. **Fix type checking errors immediately** - they block CI/CD
4. **Run `scripts/verify.py --fix`** before submitting PR
5. **Test edge cases** especially for Optional types
6. **Use VS Code with provided settings** for real-time feedback

### 📋 Pre-PR Checklist

- [ ] `python scripts/verify.py` passes completely
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Type checking clean: `mypy src/`
- [ ] No security issues: `bandit -r src/`
- [ ] Code formatted: `ruff format src/ tests/`
- [ ] Documentation updated if needed
- [ ] CHANGELOG.md updated for notable changes

### 🚨 Emergency Procedures

**If CI/CD is broken:**

1. Check type safety monitoring workflow results
2. Run `python scripts/verify.py --ci` locally
3. Fix all type checking errors first (highest priority)
4. Create hotfix branch if needed
5. Follow expedited review process for critical fixes

**If hooks are causing issues:**

1. Don't disable hooks - fix the underlying issues
2. Use `python scripts/verify.py --fix` to auto-resolve
3. Check [CLAUDE.md](../CLAUDE.md) for specific type safety patterns
4. Consult the type safety checklist in `.github/PULL_REQUEST_TEMPLATE/`

This workflow ensures consistent, high-quality code that won't break CI/CD pipelines while maintaining developer productivity.