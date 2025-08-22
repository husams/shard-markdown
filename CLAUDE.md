# Shard Markdown Development Instructions

## knowledge base
@guides/knowledge-based.md

## Project Overview

Shard Markdown is a focused CLI tool for intelligent markdown document chunking. Following the Unix philosophy of "do one thing well", it excels at breaking down markdown files into meaningful segments with optional ChromaDB storage. This document provides essential instructions for AI agents working on this codebase.

## Directory Structure

```
shard-markdown/
├── src/shard_markdown/      # Main package source
│   ├── cli/                 # Simplified CLI interface (main.py only)
│   ├── core/                # Core processing logic
│   │   ├── chunker.py      # Core chunking algorithms
│   │   └── strategies/      # Chunking strategies
│   ├── storage/            # Storage backends
│   │   ├── base.py         # Storage interface
│   │   └── vectordb.py     # ChromaDB implementation
│   ├── config/             # Configuration management
│   └── utils/              # Utility functions
├── tests/                   # Test suite
├── docs/                    # Project documentation
├── guides/                  # Development guides (load only when needed)
└── scripts/                 # Development and CI scripts
```

## General Guidelines

### Tool Usage Priority
- **ALWAYS use MCP tools over Bash** when available (mcp__* tools have priority)
- **ALWAYS use Serena tools** for file operations (mcp__serena__*)
- Only use Bash for commands not available via MCP tools
- Prefer specialized tools over general-purpose commands

### Sub-Agent Usage
- **ALWAYS use Task tool with sub-agents** for complex or specialized tasks
- Check available sub-agents using the Task tool description
- **If no suitable sub-agent exists**:
  1. Use `sub-agent-generator` to create a new specialized agent
  2. Write the agent specification to `.claude/agents/`
  3. Ask the user to restart Claude Code to load the new agent
- Leverage sub-agents for parallel task execution when possible

### Code Standards
- **Python Version**: 3.8+ (target 3.12)
- **Code Style**: Black formatter, 88 char line length
- **Linting**: Ruff with project configuration
- **Type Hints**: Required for all new code
- **Docstrings**: Google style for all public functions/classes

### Essential Commands
```bash
# Format code
uv run ruff format src/ tests/

# Lint code
uv run ruff check --fix src/ tests/

# Type checking
uv run mypy src/

# Run tests
uv run pytest
```

### Important Principles
1. **Never modify user data** without explicit permission
2. **Respect markdown structure** when processing documents
3. **Keep CLI simple** - No subcommands, just direct action
4. **Test all ChromaDB operations** before committing
5. **Document breaking changes** clearly (Note: CLI was completely redesigned in v2.0)
6. **Maintain test coverage** at ≥90% for all modules
7. **No temporary files in source tree** - Never create temp files or test scripts in the main source directories
8. **Clean up after push** - Remove any temporary files, test data, or debug scripts after pushing changes

## When to Load Guides

**IMPORTANT**: Only load these guides when working on their specific areas. Use the Read tool to load them:

### Development Guide
- **File**: `guides/development-guide.md`
- **Load with**: `Read tool: /guides/development-guide.md`
- **When to load**:
  - Implementing new features or commands
  - Refactoring existing code
  - Understanding project architecture
  - Adding new chunking strategies
  - Working with ChromaDB integration
  - Debugging development issues

### Testing Guide
- **File**: `guides/testing-guide.md`
- **Load with**: `Read tool: /guides/testing-guide.md`
- **When to load**:
  - Writing unit or integration tests
  - Debugging test failures
  - Setting up test environments
  - Working with test fixtures
  - Understanding test coverage
  - Configuring CI/CD testing

## Quick Reference

### ChromaDB Connection
- Default host: `localhost`
- Default port: `8000`
- Test with: `shard-md test.md --store --collection test --dry-run`

### Configuration Files
1. `~/.shard-md/config.yaml` (global)
2. `./.shard-md/config.yaml` (local)
3. `./shard-md.yaml` (project)

Edit these files directly with any text editor. No configuration commands exist.

### Environment Variables
- `CHROMA_HOST`: ChromaDB host
- `CHROMA_PORT`: ChromaDB port
- `SHARD_MD_CHUNK_SIZE`: Default chunk size
- `SHARD_MD_LOG_LEVEL`: Logging level

## Critical Files

- `src/shard_markdown/cli/main.py`: Simplified CLI entry point (~100 lines)
- `src/shard_markdown/core/chunker.py`: Core chunking algorithms
- `src/shard_markdown/storage/vectordb.py`: ChromaDB storage backend
- `src/shard_markdown/config/settings.py`: Configuration management
- `pyproject.toml`: Project configuration and dependencies

## **IMPORTANT** Temporary Files and Testing

### Where to Create Temporary Files
- **Use `/tmp` or system temp directory** for temporary files
- **Use `tests/fixtures/` directory** for test data files
- **Use Python's `tempfile` module** for runtime temporary files
- **Never create test scripts** in `src/` directories

### Cleanup Requirements
- **MUST** Remove all temporary files after testing
- **MUST** Clean up debug scripts before committing
- **MUST** Delete test outputs after validation
- Use `.gitignore` patterns for any persistent temp files

## **IMPORTANT** Notes

### CLI Simplification (v2.0)
- **NO SUBCOMMANDS**: The tool now works like a simple Unix utility
- **Direct action**: `shard-md <input>` processes files immediately
- **Removed commands**: No more `process`, `collections`, `query`, or `config` subcommands
- **Storage via flag**: Use `--store` to save to ChromaDB instead of separate commands

- The project uses `uv` for dependency management
- Pre-commit hooks are configured - install with `pre-commit install`
- CI/CD runs on GitHub Actions - check `.github/workflows/`
- Use below chromaDB collection ask questions claude code
    1. clause-hooks: Claude code information about hooks
    2. clause-subagents: Claude code information about sub agents
- Allows say "Hi" to the user when start new session.
- You **MUST** **ALLOWS** reflect of the error reported by Edit/MultiEdit tools. and **FIX** them.
