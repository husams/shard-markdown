# Troubleshooting Guide

## Installation Issues

### Problem: Tests fail with import errors
```
ModuleNotFoundError: No module named 'chromadb'
```

**Solution**:
1. Install with all extras: `uv pip install -e ".[chromadb]"`
2. Install dev dependencies: `uv pip install --group dev`

### Problem: ChromaDB connection failures
```
Error: Cannot connect to ChromaDB server: localhost:8000
```

**Solution for local development**:
1. Start ChromaDB Docker: `docker run -p 8000:8000 chromadb/chroma`
2. Or use persistent client in tests

**Solution for CI**:
1. Check Docker service configuration in workflow
2. Add health checks and wait logic

## Performance Issues

### Problem: Chunk validation failures
```
ProcessingError: Generated chunks exceed size limits
```

**Solution**:
1. Adjust chunk size configuration
2. Enable tolerance mode: `strict_validation: false`

### Problem: Concurrent processing efficiency
**Solution**:
1. Use multiprocessing instead of threading
2. Limit workers based on CPU cores
3. Consider I/O vs CPU-bound operations

## CI/CD Issues

### Problem: GitHub Actions failing with dependency errors
```
ERROR: Could not find a version that satisfies the requirement chromadb
```

**Solution**:
```yaml
# In your workflow file
- name: Install dependencies
  run: |
    pip install uv
    uv pip install -e ".[chromadb]"  # Install with ChromaDB support
    uv pip install --group dev        # Install dev dependencies
```

### Problem: ChromaDB Docker service not starting in CI
```
curl: (7) Failed to connect to localhost port 8000: Connection refused
```

**Solution**:
Configure ChromaDB service with proper health checks:

```yaml
services:
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - 8000:8000
    options: >-
      --health-cmd "curl -f http://localhost:8000/api/v1/heartbeat || exit 1"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

And add a proper wait step:

```yaml
- name: Wait for ChromaDB to be ready
  run: |
    echo "Waiting for ChromaDB to be ready..."
    for i in {1..30}; do
      if curl -f http://localhost:8000/api/v1/heartbeat >/dev/null 2>&1; then
        echo "ChromaDB is ready!"
        break
      fi
      echo "Attempt $i/30: ChromaDB not ready, waiting..."
      sleep 2
    done
    
    # Final check
    curl -f http://localhost:8000/api/v1/heartbeat || exit 1
```

### Problem: Cache service responded with 400
```
Error: Cache service responded with 400
```

**Solution**:
1. Clear cache or update cache key in workflow
2. Check cache key includes all relevant files:

```yaml
- name: Cache pip dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml', '**/uv.lock') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

## Development Environment Issues

### Problem: Virtual environment not activating
```
Command 'shard-md' not found
```

**Solution**:
1. Ensure virtual environment is activated: `source venv/bin/activate`
2. Install in editable mode: `uv pip install -e .`
3. Verify installation: `which shard-md`

### Problem: Pre-commit hooks failing
```
ruff failed
```

**Solution**:
1. Fix formatting issues: `ruff format src/ tests/`
2. Fix linting issues: `ruff check --fix src/ tests/`
3. Run hooks manually: `pre-commit run --all-files`

### Problem: Type checking failures
```
mypy: error: Cannot find implementation or library stub
```

**Solution**:
1. Install type dependencies: `uv pip install --group dev`
2. Add missing type annotations
3. Use type ignores for third-party libraries without stubs: `# type: ignore[import-untyped]`

## Testing Issues

### Problem: Tests hanging or timing out
```
Test session hangs indefinitely
```

**Solution**:
1. Check for infinite loops in test code
2. Add timeouts to pytest configuration:

```ini
# pytest.ini
[tool:pytest]
timeout = 300
```

3. Use `pytest -x` to stop on first failure

### Problem: Integration tests fail locally but pass in CI
```
Tests pass in GitHub Actions but fail on local machine
```

**Solution**:
1. Ensure ChromaDB is running locally: `docker run -p 8000:8000 chromadb/chroma`
2. Check environment variables: `CHROMADB_HOST=localhost CHROMADB_PORT=8000`
3. Clear test data: `rm -rf .chroma/` or equivalent cleanup

### Problem: Coverage reports are inaccurate
```
Coverage shows 0% despite running tests
```

**Solution**:
1. Use `--cov-append` for multiple test runs
2. Ensure coverage is measuring the right directory: `--cov=src/shard_markdown`
3. Check `.coveragerc` configuration

## Configuration Issues

### Problem: Configuration file not found
```
FileNotFoundError: config.yaml not found
```

**Solution**:
1. Initialize configuration: `shard-md config init`
2. Check configuration file locations:
   - `~/.shard-md/config.yaml` (global)
   - `./.shard-md/config.yaml` (project-local)
   - `./shard-md.yaml` (project root)

### Problem: Environment variables not recognized
```
Configuration value not overridden by environment variable
```

**Solution**:
Use correct environment variable names:
```bash
export CHROMA_HOST=localhost
export CHROMA_PORT=8000
export SHARD_MD_CHUNK_SIZE=1500
export SHARD_MD_LOG_LEVEL=DEBUG
```

## Performance Troubleshooting

### Problem: Slow document processing
```
Processing takes longer than expected
```

**Solution**:
1. Adjust worker count: `--max-workers 2`
2. Reduce chunk size: `--chunk-size 500`
3. Process files in batches: `--batch-size 5`
4. Enable progress monitoring: `--verbose`

### Problem: Memory usage growing continuously
```
Memory usage increases during processing
```

**Solution**:
1. Process files in smaller batches
2. Clear ChromaDB collections periodically
3. Monitor memory usage: `python -m memory_profiler script.py`

## Debugging Tips

### Enable Debug Logging
```bash
export SHARD_MD_LOG_LEVEL=DEBUG
shard-md process --collection debug-test document.md
```

### Test ChromaDB Connection
```python
import chromadb
client = chromadb.HttpClient(host="localhost", port=8000)
print(client.heartbeat())  # Should return current timestamp
```

### Validate Configuration
```bash
shard-md config show
shard-md config validate  # If available
```

### Profile Performance
```bash
python -m cProfile -o profile.stats -m shard_markdown.cli.main process document.md
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(10)"
```

## Getting Help

If you encounter issues not covered in this guide:

1. **Check GitHub Issues**: Search for similar problems at [GitHub Issues](https://github.com/husams/shard-markdown/issues)
2. **Enable Debug Mode**: Run with `--verbose` and `SHARD_MD_LOG_LEVEL=DEBUG`
3. **Collect System Information**:
   ```bash
   python --version
   pip list | grep -E "(chromadb|ruff|pytest)"
   docker --version  # If using ChromaDB Docker
   ```
4. **Create Minimal Reproduction**: Prepare a simple test case that demonstrates the issue
5. **Report Issues**: Include logs, system info, and reproduction steps when reporting new issues