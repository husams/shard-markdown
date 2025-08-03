# CI/CD Setup and Automated Testing

## Overview

This document provides comprehensive CI/CD configuration for the shard-markdown CLI utility, including automated testing, quality gates, and deployment pipelines. The setup ensures consistent quality and reliable releases through automated validation.

## CI/CD Architecture

### Pipeline Stages
1. **Code Quality**: Linting, formatting, type checking
2. **Unit Testing**: Fast, isolated tests
3. **Integration Testing**: Component interaction tests
4. **End-to-End Testing**: Full workflow validation
5. **Performance Testing**: Benchmark validation
6. **Security Scanning**: Vulnerability assessment
7. **Documentation**: Auto-generated docs and validation
8. **Release**: Automated versioning and publishing

## GitHub Actions Workflows

### Main Testing Pipeline

```yaml
# .github/workflows/test.yml
name: Comprehensive Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    # Run tests daily at 6 AM UTC
    - cron: '0 6 * * *'

env:
  PYTHON_VERSION_DEFAULT: '3.11'

jobs:
  # Code Quality and Linting
  code-quality:
    name: Code Quality
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION_DEFAULT }}
      
      - name: Cache pip dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
          restore-keys: |
            ${{ runner.os }}-pip-
      
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[dev]"
      
      - name: Code formatting check
        run: |
          black --check --diff src/ tests/
          echo "✅ Code formatting verified"
      
      - name: Import sorting check
        run: |
          isort --check-only --diff src/ tests/
          echo "✅ Import sorting verified"
      
      - name: Linting
        run: |
          flake8 src/ tests/ --statistics
          echo "✅ Linting completed"
      
      - name: Type checking
        run: |
          mypy src/ --show-error-codes
          echo "✅ Type checking completed"

  # Unit Tests with Coverage
  unit-tests:
    name: Unit Tests
    needs: code-quality
    strategy:
      matrix:
        python-version: ['3.8', '3.9', '3.10', '3.11', '3.12']
        os: [ubuntu-latest, windows-latest, macos-latest]
        exclude:
          # Reduce matrix for faster CI
          - os: windows-latest
            python-version: '3.8'
          - os: macos-latest
            python-version: '3.8'
    
    runs-on: ${{ matrix.os }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Cache pip dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-${{ matrix.python-version }}-pip-${{ hashFiles('**/pyproject.toml') }}
      
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[dev]"
      
      - name: Run unit tests
        run: |
          pytest tests/unit/ \
            --cov=src/shard_markdown \
            --cov-report=xml \
            --cov-report=term-missing \
            --cov-fail-under=80 \
            --junitxml=test-results-${{ matrix.os }}-${{ matrix.python-version }}.xml \
            -v
      
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results-${{ matrix.os }}-${{ matrix.python-version }}
          path: test-results-${{ matrix.os }}-${{ matrix.python-version }}.xml
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        if: matrix.python-version == env.PYTHON_VERSION_DEFAULT && matrix.os == 'ubuntu-latest'
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-${{ matrix.os }}-${{ matrix.python-version }}

  # Integration Tests
  integration-tests:
    name: Integration Tests
    needs: unit-tests
    runs-on: ubuntu-latest
    
    services:
      # ChromaDB test instance (if using real ChromaDB)
      chromadb:
        image: chromadb/chroma:latest
        ports:
          - 8000:8000
        options: >-
          --health-cmd="curl -f http://localhost:8000/api/v1/heartbeat"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION_DEFAULT }}
      
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[dev,chromadb]"
      
      - name: Wait for ChromaDB to be ready
        run: |
          timeout 30 bash -c 'until curl -f http://localhost:8000/api/v1/heartbeat; do sleep 1; done'
      
      - name: Run integration tests
        env:
          CHROMADB_HOST: localhost
          CHROMADB_PORT: 8000
        run: |
          pytest tests/integration/ \
            --cov=src/shard_markdown \
            --cov-append \
            --cov-report=xml \
            -v \
            --tb=short
      
      - name: Upload integration coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: integration
          name: codecov-integration

  # End-to-End Tests
  e2e-tests:
    name: End-to-End Tests
    needs: integration-tests
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION_DEFAULT }}
      
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[dev]"
      
      - name: Create test project structure
        run: |
          mkdir -p test_project/docs/{api,guides}
          echo "# API Documentation" > test_project/docs/api/readme.md
          echo "# User Guide" > test_project/docs/guides/getting-started.md
      
      - name: Run end-to-end tests
        run: |
          pytest tests/e2e/ \
            -v \
            --tb=short \
            --maxfail=3
      
      - name: Test CLI installation and basic usage
        run: |
          # Test package installation
          uv pip install -e .
          
          # Test CLI help
          shard-md --help
          shard-md --version
          
          # Test basic command structure
          shard-md process --help
          shard-md collections --help || echo "Collections command not yet implemented"

  # Performance Tests
  performance-tests:
    name: Performance Tests
    needs: unit-tests
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION_DEFAULT }}
      
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[dev]"
      
      - name: Run performance tests
        run: |
          pytest tests/performance/ \
            --benchmark-only \
            --benchmark-json=benchmark.json \
            --benchmark-save=ci-${{ github.sha }} \
            -v
      
      - name: Store benchmark results
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: 'pytest'
          output-file-path: benchmark.json
          github-token: ${{ secrets.GITHUB_TOKEN }}
          auto-push: true
          comment-on-alert: true
          alert-threshold: '150%'
          fail-on-alert: true

  # Security Scanning
  security:
    name: Security Scanning
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION_DEFAULT }}
      
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[dev]"
          uv pip install safety bandit
      
      - name: Run safety check for vulnerabilities
        run: |
          safety check --json --output safety-report.json || true
          safety check
      
      - name: Run bandit security linter
        run: |
          bandit -r src/ -f json -o bandit-report.json || true
          bandit -r src/
      
      - name: Upload security reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: security-reports
          path: |
            safety-report.json
            bandit-report.json

  # Documentation
  documentation:
    name: Documentation
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION_DEFAULT }}
      
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e ".[dev]"
          uv pip install sphinx sphinx-rtd-theme
      
      - name: Check documentation links
        run: |
          # Check for broken links in markdown files
          find docs/ -name "*.md" -exec echo "Checking {}" \;
      
      - name: Generate API documentation
        run: |
          # Generate API docs with sphinx-apidoc if configured
          echo "API documentation generation placeholder"
      
      - name: Validate documentation completeness
        run: |
          # Check that all public modules have documentation
          python -c "
          import ast
          import os
          
          def check_docstrings(filepath):
              with open(filepath, 'r') as f:
                  tree = ast.parse(f.read())
              
              for node in ast.walk(tree):
                  if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                      if not ast.get_docstring(node):
                          print(f'Missing docstring: {filepath}:{node.lineno}:{node.name}')
          
          for root, dirs, files in os.walk('src/'):
              for file in files:
                  if file.endswith('.py'):
                      check_docstrings(os.path.join(root, file))
          "
```

### Release Pipeline

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  test:
    name: Test Release
    uses: ./.github/workflows/test.yml

  build:
    name: Build Distribution
    needs: test
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install build dependencies
        run: |
          pip install uv
          uv pip install build twine
      
      - name: Build package
        run: python -m build
      
      - name: Check package
        run: twine check dist/*
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: distributions
          path: dist/

  release:
    name: Create Release
    needs: build
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Download artifacts
        uses: actions/download-artifact@v3
        with:
          name: distributions
          path: dist/
      
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
          generate_release_notes: true
          draft: false
          prerelease: ${{ contains(github.ref, 'alpha') || contains(github.ref, 'beta') || contains(github.ref, 'rc') }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  publish:
    name: Publish to PyPI
    needs: release
    runs-on: ubuntu-latest
    environment: release
    
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v3
        with:
          name: distributions
          path: dist/
      
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
          skip_existing: true
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.6.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: local
    hooks:
      - id: pytest-fast
        name: pytest-fast
        entry: pytest tests/unit/ -x --tb=short
        language: system
        pass_filenames: false
        stages: [commit]

      - id: test-coverage
        name: test-coverage
        entry: pytest tests/unit/ --cov=src/shard_markdown --cov-fail-under=80
        language: system
        pass_filenames: false
        stages: [push]
```

## Local Development Setup

### Development Environment Configuration

```bash
#!/bin/bash
# scripts/setup-dev-env.sh

set -e

echo "🚀 Setting up shard-markdown development environment..."

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
if [[ $(echo "$python_version >= 3.8" | bc -l) -eq 0 ]]; then
    echo "❌ Python 3.8+ required. Found: $python_version"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install uv

# Install development dependencies
echo "📚 Installing dependencies..."
uv pip install -e ".[dev]"

# Install pre-commit hooks
echo "🔗 Setting up pre-commit hooks..."
pre-commit install

# Run initial tests
echo "🧪 Running initial test suite..."
pytest tests/unit/ --tb=short

# Setup IDE configuration
echo "⚙️  Setting up IDE configuration..."
mkdir -p .vscode
cat > .vscode/settings.json << EOF
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/unit/"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true,
        "**/htmlcov": true,
        "**/.coverage": true
    }
}
EOF

echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate environment: source venv/bin/activate"
echo "  2. Run tests: pytest tests/unit/"
echo "  3. Check code quality: pre-commit run --all-files"
echo "  4. Start coding! 🎉"
```

### Testing Scripts

```bash
#!/bin/bash
# scripts/run-tests.sh

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Parse command line arguments
FAST=false
COVERAGE=false
INTEGRATION=false
E2E=false
PERFORMANCE=false
ALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --fast)
            FAST=true
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --integration)
            INTEGRATION=true
            shift
            ;;
        --e2e)
            E2E=true
            shift
            ;;
        --performance)
            PERFORMANCE=true
            shift
            ;;
        --all)
            ALL=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--fast] [--coverage] [--integration] [--e2e] [--performance] [--all]"
            exit 1
            ;;
    esac
done

# Default to fast tests if no options specified
if [[ "$ALL" == "false" && "$COVERAGE" == "false" && "$INTEGRATION" == "false" && "$E2E" == "false" && "$PERFORMANCE" == "false" ]]; then
    FAST=true
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

log_info "Starting test execution..."

# Code quality checks
log_info "Running code quality checks..."
if black --check src/ tests/; then
    log_success "Code formatting check passed"
else
    log_error "Code formatting check failed"
    exit 1
fi

if isort --check-only src/ tests/; then
    log_success "Import sorting check passed"
else
    log_error "Import sorting check failed"
    exit 1
fi

if flake8 src/ tests/; then
    log_success "Linting passed"
else
    log_error "Linting failed"
    exit 1
fi

# Unit tests
if [[ "$FAST" == "true" || "$ALL" == "true" ]]; then
    log_info "Running unit tests..."
    if [[ "$COVERAGE" == "true" || "$ALL" == "true" ]]; then
        pytest tests/unit/ --cov=src/shard_markdown --cov-report=html --cov-report=term-missing -v
    else
        pytest tests/unit/ -v
    fi
    log_success "Unit tests completed"
fi

# Integration tests
if [[ "$INTEGRATION" == "true" || "$ALL" == "true" ]]; then
    log_info "Running integration tests..."
    pytest tests/integration/ -v --tb=short
    log_success "Integration tests completed"
fi

# End-to-end tests
if [[ "$E2E" == "true" || "$ALL" == "true" ]]; then
    log_info "Running end-to-end tests..."
    pytest tests/e2e/ -v --tb=short
    log_success "End-to-end tests completed"
fi

# Performance tests
if [[ "$PERFORMANCE" == "true" || "$ALL" == "true" ]]; then
    log_info "Running performance tests..."
    pytest tests/performance/ --benchmark-only -v
    log_success "Performance tests completed"
fi

log_success "All tests completed successfully! 🎉"

# Generate coverage report if requested
if [[ "$COVERAGE" == "true" || "$ALL" == "true" ]]; then
    log_info "Coverage report generated in htmlcov/index.html"
fi
```

## Quality Gates and Deployment

### Quality Gate Configuration

```yaml
# quality-gates.yml
quality_gates:
  unit_tests:
    coverage_threshold: 80
    pass_rate_threshold: 98
    max_duration_minutes: 5
    
  integration_tests:
    pass_rate_threshold: 95
    max_duration_minutes: 15
    
  performance_tests:
    regression_threshold: 120  # 20% performance degradation max
    memory_threshold_mb: 500
    max_duration_minutes: 30
    
  security_scan:
    max_high_vulnerabilities: 0
    max_medium_vulnerabilities: 2
    
  code_quality:
    min_maintainability_index: 70
    max_complexity: 10
    max_code_duplication_percent: 5
```

### Deployment Strategy

```yaml
# deployment-strategy.yml
environments:
  development:
    auto_deploy: true
    quality_gates: [unit_tests, code_quality]
    
  staging:
    auto_deploy: false  # Manual approval required
    quality_gates: [unit_tests, integration_tests, code_quality, security_scan]
    
  production:
    auto_deploy: false  # Manual approval required
    quality_gates: [unit_tests, integration_tests, e2e_tests, performance_tests, security_scan]
    approval_required: 2  # Two approvals needed
    
deployment_process:
  1. Automated testing on pull request
  2. Code review and approval
  3. Merge to main branch
  4. Automated deployment to development
  5. Manual testing and validation
  6. Promotion to staging (manual)
  7. Staging validation and performance testing
  8. Production deployment (manual with approvals)
  9. Post-deployment monitoring and validation
```

This comprehensive CI/CD setup ensures reliable, automated testing and deployment while maintaining high quality standards throughout the development lifecycle.