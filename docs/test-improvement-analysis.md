# Deep Analysis: Unit Test Mock Reduction Strategy

## Current State Analysis

### Mock Usage Patterns Identified

#### 1. **ChromaDB Async/Sync Client Tests (80 mocks)**
- **Files**: `test_async_client.py`, `test_client.py`
- **Pattern**: Every test method mocks `chromadb.AsyncHttpClient` or `chromadb.HttpClient`
- **Justification**: VALID - Testing async client behavior without running ChromaDB server
- **Opportunity**: CONSOLIDATION possible

#### 2. **CLI Tests (20 mocks)**
- **File**: `test_main.py`
- **Pattern**: Mocking parser, chunker, metadata extractor, config
- **Justification**: PARTIALLY VALID - CLI should test command parsing, not business logic
- **Opportunity**: SIGNIFICANT reduction possible

#### 3. **Processor Tests (15 mocks)**
- **File**: `test_processor.py`
- **Pattern**: Mocking core components to test orchestration
- **Justification**: MIXED - Some tests need mocks, others could use real components
- **Opportunity**: MODERATE reduction possible

#### 4. **Good Examples (0 mocks)**
- **File**: `test_chunker.py`
- **Pattern**: Uses real implementations with actual markdown
- **This is our target pattern!**

## Specific Improvement Recommendations

### Priority 1: Consolidate ChromaDB Mock Fixtures (Save ~30 mocks)

**Current Problem**: Repetitive mock setup in every test method
```python
# This pattern repeats 13 times in test_async_client.py
with patch("chromadb.AsyncHttpClient") as mock_client_class:
    mock_client = AsyncMock()
    mock_client.heartbeat = AsyncMock(return_value=None)
    # ... same setup code ...
```

**Solution**: Create shared fixtures
```python
@pytest.fixture
def mock_chromadb_async_client():
    """Shared fixture for ChromaDB async client mocking."""
    with patch("chromadb.AsyncHttpClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.heartbeat = AsyncMock(return_value=None)
        mock_client.get_collection = AsyncMock()
        mock_client.get_or_create_collection = AsyncMock()
        mock_client.list_collections = AsyncMock(return_value=[])
        mock_client.delete_collection = AsyncMock()
        
        async def async_mock_client(*args, **kwargs):
            return mock_client
        
        mock_client_class.side_effect = async_mock_client
        yield mock_client

# Then each test becomes:
async def test_connect_method(self, config, mock_chromadb_async_client):
    client = AsyncChromaDBClient(config)
    await client.connect()
    assert client.client == mock_chromadb_async_client
```

**Impact**: 
- Reduces 40 async mock setups to 1 fixture
- Reduces 20 sync mock setups to 1 fixture
- **Total reduction: ~30 mocks**

### Priority 2: Replace CLI Mocks with Integration Tests (Save ~15 mocks)

**Current Problem**: CLI tests mock all business logic
```python
@pytest.fixture
def mock_parser(self):
    with patch("shard_markdown.cli.main.MarkdownParser") as mock:
        # ... mocking internal behavior ...

@pytest.fixture
def mock_chunker(self):
    with patch("shard_markdown.cli.main.ChunkingEngine") as mock:
        # ... mocking internal behavior ...
```

**Solution**: Test CLI with real components for basic scenarios
```python
def test_basic_processing_real(self, cli_runner, sample_markdown_file):
    """Test CLI with real components - no mocks."""
    result = cli_runner.invoke(shard_md, [str(sample_markdown_file)])
    
    assert result.exit_code == 0
    assert "Total chunks:" in result.output
    # Verify actual chunking occurred
    assert "chunk" in result.output.lower()

def test_cli_argument_parsing(self, cli_runner):
    """Test CLI argument parsing only - focused test."""
    # Only test that CLI correctly parses arguments
    # Don't test the actual processing
    result = cli_runner.invoke(shard_md, ["--help"])
    assert "--size" in result.output
    assert "--strategy" in result.output
```

**Impact**:
- Remove parser mock (4 instances)
- Remove chunker mock (4 instances)
- Remove metadata_extractor mock (4 instances)
- Keep config mock for configuration testing only
- **Total reduction: ~12 mocks**

### Priority 3: Hybrid Processor Testing (Save ~8 mocks)

**Current Problem**: All processor tests mock core components
```python
@pytest.fixture
def mock_parser(self):
    with patch("shard_markdown.core.processor.MarkdownParser") as mock:
        yield mock.return_value
```

**Solution**: Mix real and mocked components based on test purpose
```python
class TestDocumentProcessorIntegration:
    """Integration tests using real components."""
    
    def test_process_document_real(self, chunking_config, sample_markdown_file):
        """Test with real parser and chunker."""
        processor = DocumentProcessor(chunking_config)
        result = processor.process_document(sample_markdown_file, "test")
        
        assert result.success is True
        assert result.chunks_created > 0

class TestDocumentProcessorUnit:
    """Unit tests for error handling - mocks allowed."""
    
    @pytest.fixture
    def mock_parser_error(self):
        """Mock only for error simulation."""
        with patch("shard_markdown.core.processor.MarkdownParser") as mock:
            mock.return_value.parse.side_effect = Exception("Parse error")
            yield mock.return_value
```

**Impact**:
- Convert 5 tests to use real components
- Keep mocks only for error simulation (3 tests)
- **Total reduction: ~8 mocks**

### Priority 4: Test Utility Helpers (Save ~5 mocks)

**Create test utilities to reduce mock complexity:**
```python
# tests/unit/helpers.py
class TestDataBuilder:
    """Builder for test data without mocks."""
    
    @staticmethod
    def create_markdown_ast(content: str) -> MarkdownAST:
        """Create real AST from markdown content."""
        parser = MarkdownParser()
        return parser.parse(content)
    
    @staticmethod
    def create_test_chunks(count: int = 3) -> list[DocumentChunk]:
        """Create test chunks without mocking."""
        return [
            DocumentChunk(
                id=f"chunk_{i}",
                content=f"Test content {i}",
                metadata={"index": i}
            )
            for i in range(count)
        ]
```

## Implementation Plan

### Phase 1: Quick Wins (1-2 hours)
1. Create shared ChromaDB mock fixtures
2. Consolidate repetitive mock setups
3. **Expected reduction: 30 mocks**

### Phase 2: CLI Refactoring (2-3 hours)
1. Separate CLI argument tests from processing tests
2. Create integration tests with real components
3. Remove unnecessary mocks
4. **Expected reduction: 12 mocks**

### Phase 3: Processor Hybrid Testing (2-3 hours)
1. Split processor tests into integration and unit
2. Use real components where possible
3. Keep mocks only for error simulation
4. **Expected reduction: 8 mocks**

### Phase 4: Test Utilities (1 hour)
1. Create test data builders
2. Replace mock fixtures with builders
3. **Expected reduction: 5 mocks**

## Expected Outcomes

### Before
- **Current mocks**: 120
- **Test complexity**: High
- **Maintenance burden**: High
- **Test reliability**: Moderate

### After
- **Target mocks**: 65 (realistic goal)
- **Test complexity**: Low
- **Maintenance burden**: Low
- **Test reliability**: High
- **Test coverage**: Improved (testing real behavior)

## Key Principles

1. **Mock External Dependencies Only**: ChromaDB clients, file I/O errors
2. **Use Real Components When Possible**: Parser, chunker, metadata extractor
3. **Consolidate Mock Fixtures**: One fixture per mock type, not per test
4. **Separate Concerns**: CLI tests for CLI, unit tests for units
5. **Test Builders Over Mocks**: Create real test data when feasible

## Success Metrics

- ✅ Mock count reduced from 120 to ≤65
- ✅ All tests still pass
- ✅ Coverage maintained at ≥90%
- ✅ Test execution time similar or better
- ✅ Code is more maintainable

## Notes

- The 40 ChromaDB async mocks are legitimate and should be kept (but consolidated)
- Focus on removing mocks that test implementation details
- Prioritize testing actual behavior over mock interactions
- Consider using `pytest-mock` for cleaner mock management