# CI/CD Configuration for shard-markdown

This document describes the comprehensive CI/CD setup configured for the shard-markdown project.

## Workflow Overview

### 🔄 Core Workflows

#### 1. **CI Pipeline** (`ci.yml`)

**Triggers:** Push to main/develop, Pull requests, Manual dispatch

**Jobs:**

- **lint**: Code quality checks (black, isort, flake8, mypy, pre-commit)
- **test**: Multi-platform testing (Ubuntu, Windows, macOS) across Python 3.8-3.12
- **coverage**: Test coverage with ChromaDB integration (80% minimum)
- **build**: Package building and installation testing
- **benchmark**: Performance benchmarks (PR only)
- **security**: Security scanning with safety and bandit

#### 2. **Release Pipeline** (`release.yml`)

**Triggers:** GitHub releases, Manual dispatch

**Jobs:**

- **validate-release**: Version validation and environment setup
- **test-before-release**: Full test suite before release
- **build-and-publish**: Build and publish to PyPI/TestPyPI
- **create-github-release**: Automated GitHub release creation
- **notify-success**: Release success notifications

#### 3. **Documentation** (`docs.yml`)

**Triggers:** Changes to docs/, src/, README.md, Manual dispatch

**Jobs:**

- **build-docs**: Sphinx documentation generation
- **cli-docs**: Auto-generated CLI documentation
- **deploy-docs**: GitHub Pages deployment
- **docs-quality**: Documentation quality checks
- **update-docs**: Automated documentation updates

#### 4. **Dependencies** (`dependencies.yml`)

**Triggers:** Weekly schedule, dependency file changes, Manual dispatch

**Jobs:**

- **security-audit**: Security vulnerability scanning
- **dependency-review**: Outdated dependency detection
- **auto-update**: Automated dependency updates (creates PRs)
- **license-check**: License compliance checking

#### 5. **End-to-End Tests** (`e2e.yml`)

**Triggers:** Push to main, Pull requests, Daily schedule, Manual dispatch

**Jobs:**

- **e2e-cli**: CLI workflow testing with real ChromaDB
- **e2e-installation**: Package installation testing
- **e2e-chromadb-configs**: Multiple ChromaDB version testing
- **e2e-performance**: Load testing (scheduled/manual only)

#### 6. **Automation** (`automation.yml`)

**Triggers:** Issues, Pull requests, Weekly schedule

**Jobs:**

- **auto-label**: Intelligent issue/PR labeling
- **stale-management**: Stale issue/PR cleanup
- **welcome**: New contributor welcoming
- **pr-size-warning**: Large PR warnings
- **dependency-notifications**: Dependency update notifications

### 🎯 Key Features

#### Multi-Platform Support

- **Operating Systems**: Ubuntu, Windows, macOS
- **Python Versions**: 3.8, 3.9, 3.10, 3.11, 3.12
- **ChromaDB Versions**: Multiple version compatibility testing

#### Security & Quality

- **Code Quality**: black, isort, flake8, mypy, pre-commit
- **Security Scanning**: safety (vulnerabilities), bandit (code security)
- **Test Coverage**: 80% minimum coverage requirement
- **License Compliance**: GPL/AGPL detection and warnings

#### Automation

- **Intelligent Labeling**: Auto-labeling based on content and file changes
- **Dependency Management**: Weekly automated updates with PR creation
- **Stale Management**: 30-day stale, 7-day close policy
- **Welcome Messages**: New contributor onboarding

#### Publishing

- **Trusted Publishing**: OIDC-based PyPI publishing (no API keys needed)
- **Dual Environment**: TestPyPI and PyPI support
- **Version Management**: Automatic version updating and validation
- **Asset Management**: Build artifact uploads and release asset management

## Configuration Files

### Pre-commit Configuration

- **File**: `.pre-commit-config.yaml`
- **Features**: Code formatting, linting, security scanning, documentation checks
- **Integration**: Runs locally and in CI

### Issue Templates

- **Bug Report**: Structured bug reporting with environment details
- **Feature Request**: Feature proposals with use cases and priorities
- **Question**: Q&A template for support requests

### Pull Request Template

- **Comprehensive**: Change type, testing, documentation, security considerations
- **Checklists**: Code quality, testing, documentation requirements

## Setup Requirements

### Repository Secrets

No secrets required for basic CI/CD! Uses trusted publishing for PyPI.

Optional secrets for enhanced features:

- `CODECOV_TOKEN`: For Codecov integration
- `GITHUB_TOKEN`: Automatically provided by GitHub

### Repository Settings

#### Branch Protection

Recommended branch protection rules for `main`:

```yaml
Required status checks:
  - lint
  - test
  - coverage
  - build

Require branches to be up to date: true
Restrict pushes: true
```

#### Environments

1. **testpypi**: For test releases
2. **pypi**: For production releases
3. **github-pages**: For documentation deployment

#### Labels

Auto-created labels for organization:

- `bug`, `enhancement`, `documentation`
- `cli`, `core`, `chromadb`, `configuration`
- `size/XS`, `size/S`, `size/M`, `size/L`, `size/XL`
- `stale`, `needs-triage`, `question`

## Usage Guide

### Development Workflow

1. **Create feature branch** from `main`
2. **Make changes** and commit
3. **Push branch** - triggers CI checks
4. **Create PR** - triggers full test suite
5. **Review and merge** - triggers documentation updates

### Release Workflow

1. **Manual Release**:

   ```bash
   # Trigger release workflow
   gh workflow run release.yml -f version=1.0.0 -f environment=testpypi
   ```

2. **GitHub Release**:
   - Create release tag via GitHub UI
   - Automatically triggers production release

### Monitoring

- **Workflow Status**: Check Actions tab for real-time status
- **Coverage Reports**: Uploaded as artifacts and sent to Codecov
- **Security Reports**: Generated weekly and on dependency changes
- **Performance Benchmarks**: Run on PRs and available as artifacts

## Maintenance

### Weekly Tasks (Automated)

- Dependency updates (Mondays)
- Stale issue cleanup (Sundays)
- Security audits

### Monthly Tasks (Manual)

- Review and update workflow versions
- Check for new linting rules or tools
- Review security scan results
- Update documentation

### Troubleshooting

#### Common Issues

1. **Test Failures**: Check ChromaDB service status in logs
2. **Build Failures**: Verify Python version compatibility
3. **Security Scan Failures**: Review safety and bandit reports
4. **Large PR Warnings**: Consider breaking into smaller PRs

#### Debugging

- Check workflow logs in GitHub Actions tab
- Use workflow_dispatch for manual testing
- Review artifact uploads for detailed reports

## Best Practices

### For Contributors

1. **Run pre-commit locally**: `pre-commit install && pre-commit run --all-files`
2. **Test before pushing**: `uv run pytest`
3. **Keep PRs focused**: Single feature/fix per PR
4. **Update documentation**: Include relevant doc updates

### For Maintainers

1. **Monitor security alerts**: Weekly security audit review
2. **Review dependency updates**: Automated PRs need human verification
3. **Maintain environments**: Keep PyPI trusted publishing configured
4. **Update workflows**: Regular maintenance of action versions

---

**Generated with [Claude Code](https://claude.ai/code)**

This comprehensive CI/CD setup provides enterprise-grade automation for the shard-markdown project, ensuring code quality, security, and reliable releases while minimizing manual maintenance overhead.
