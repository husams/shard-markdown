# Performance Tests

These tests are intentionally excluded from CI/CD due to their resource-intensive nature.

## Running Performance Tests

### Run all performance tests:
```bash
uv run pytest tests/performance/ -v -m performance
```

### Run specific test categories:
```bash
# Large file tests only
uv run pytest tests/performance/test_large_files.py -v

# Memory profiling
uv run pytest tests/performance/test_memory_efficiency.py -v --memprof

# Concurrent processing stress tests
uv run pytest tests/performance/test_concurrent_processing.py -v
```

## When to Run

- Before major releases
- After performance optimization changes
- When investigating performance issues
- During capacity planning

## Test Data Generation

Generate large test files:
```bash
python scripts/generate_test_data.py --size 10mb --output tests/performance/data/
```

## Performance Baselines

Current acceptable performance metrics:
- 10MB file: < 30 seconds
- 100 concurrent files: < 5 minutes
- Memory usage: < 500MB for any single file
- ChromaDB insertion: > 1000 chunks/second
