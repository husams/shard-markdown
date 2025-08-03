# Technical Specifications
## Shard-Markdown CLI Utility

**Document Version:** 1.0
**Date:** August 2, 2025
**Related Document:** Product Requirements Document v1.0

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Interface │────│  Core Processor │────│ ChromaDB Client │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Argument Parser │    │ Markdown Parser │    │ Collection Mgmt │
│ Validation      │    │ Chunking Engine │    │ Document Store  │
│ Help System     │    │ Metadata Extractor│   │ Error Handling  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 1.2 Core Components

#### CLI Interface Module
- **Responsibility:** Handle command-line arguments, validation, and user interaction
- **Key Classes:** `CLIHandler`, `ArgumentValidator`, `OutputFormatter`
- **Dependencies:** Click/argparse, Rich (optional)

#### Core Processor Module
- **Responsibility:** Orchestrate the complete processing workflow
- **Key Classes:** `DocumentProcessor`, `ChunkingEngine`, `MetadataExtractor`
- **Dependencies:** Markdown parser, Pydantic

#### ChromaDB Client Module
- **Responsibility:** Manage database connections and document storage
- **Key Classes:** `ChromaDBClient`, `CollectionManager`, `DocumentStore`
- **Dependencies:** ChromaDB client library

---

## 2. Detailed Component Specifications

### 2.1 CLI Interface Implementation

#### Command Structure
```bash
shard-markdown [OPTIONS] INPUT_FILE

Options:
  --chunk-size INTEGER RANGE     Maximum characters per chunk [100<=x<=10000] [default: 1000]
  --overlap INTEGER RANGE        Character overlap between chunks [0<=x<=500] [default: 100]
  --collection-name TEXT         ChromaDB collection name [default: auto-generated]
  --db-path PATH                ChromaDB database path [default: ./chroma_db]
  --output-format [text|json]   Output format [default: text]
  --verbose                     Enable verbose logging
  --dry-run                     Preview chunks without storing
  --config-file PATH            Configuration file path
  --help                        Show this message and exit
  --version                     Show version and exit
```

#### Configuration File Format (YAML)
```yaml
# shard-markdown configuration
chunk_size: 1000
overlap: 100
collection_name: "markdown_chunks"
db_path: "./chroma_db"
output_format: "text"
verbose: false

# Advanced settings
chunking:
  respect_boundaries: true
  min_chunk_size: 50
  max_chunk_size: 10000

database:
  batch_size: 1000
  connection_timeout: 30
  retry_attempts: 3
```

### 2.2 Chunking Algorithm Specification

#### Intelligent Boundary Detection
```python
BOUNDARY_PRIORITIES = {
    'document_end': 100,
    'h1_header': 90,
    'h2_header': 80,
    'h3_header': 70,
    'paragraph_break': 60,
    'code_block_end': 50,
    'list_item_end': 40,
    'sentence_end': 30,
    'word_boundary': 10
}

def find_optimal_split_point(text: str, target_position: int, max_distance: int = 200) -> int:
    """
    Find the optimal position to split text near the target position,
    prioritizing semantic boundaries.
    """
    # Implementation details for boundary detection
```

#### Chunk Overlap Strategy
```python
def calculate_overlap(chunk_size: int, overlap_size: int, boundary_type: str) -> tuple[int, int]:
    """
    Calculate optimal overlap start and end positions based on content boundaries.

    Returns:
        tuple: (overlap_start_chars, overlap_end_chars)
    """
    # Ensure overlap respects semantic boundaries
    # Adjust overlap based on content type (code vs text)
```

### 2.3 Metadata Schema Implementation

#### Chunk Metadata Structure
```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class ChunkMetadata(BaseModel):
    chunk_id: UUID = Field(description="Unique identifier for the chunk")
    source_file: str = Field(description="Absolute path to source markdown file")
    sequence_number: int = Field(description="Sequential order in document", ge=0)
    content: str = Field(description="Actual chunk content")
    character_count: int = Field(description="Number of characters in chunk", gt=0)
    word_count: int = Field(description="Number of words in chunk", gt=0)
    headers_path: List[str] = Field(description="Hierarchical path of headers", default=[])
    content_type: str = Field(description="Type of content", regex="^(text|code|table|list|header)$")
    created_at: datetime = Field(description="Timestamp when chunk was created")
    overlap_start: int = Field(description="Characters overlapping with previous chunk", ge=0)
    overlap_end: int = Field(description="Characters overlapping with next chunk", ge=0)
    language: Optional[str] = Field(description="Language code if detected", default=None)

    # Additional metadata for advanced features
    hash_digest: str = Field(description="SHA-256 hash of content for deduplication")
    processing_version: str = Field(description="Version of processing algorithm used")

class DocumentMetadata(BaseModel):
    document_id: UUID = Field(description="Unique identifier for the document")
    file_path: str = Field(description="Original file path")
    file_size: int = Field(description="File size in bytes")
    total_chunks: int = Field(description="Total number of chunks created")
    processing_time: float = Field(description="Processing time in seconds")
    chunk_size_config: int = Field(description="Configured chunk size used")
    overlap_config: int = Field(description="Configured overlap used")
```

### 2.4 ChromaDB Integration Details

#### Collection Management
```python
class CollectionManager:
    def __init__(self, db_path: str, collection_name: str):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection_name = collection_name

    def get_or_create_collection(self) -> Collection:
        """Get existing collection or create new one with proper metadata."""
        metadata = {
            "created_by": "shard-markdown",
            "version": "1.0",
            "description": "Markdown document chunks for semantic search"
        }

        try:
            collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=self._get_embedding_function()
            )
        except ValueError:
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata=metadata,
                embedding_function=self._get_embedding_function()
            )

        return collection

    def _get_embedding_function(self):
        """Return appropriate embedding function for the collection."""
        # Default to sentence-transformers if available, otherwise use basic
        return chromadb.utils.embedding_functions.DefaultEmbeddingFunction()
```

#### Batch Storage Implementation
```python
class DocumentStore:
    def __init__(self, collection: Collection, batch_size: int = 1000):
        self.collection = collection
        self.batch_size = batch_size

    def store_chunks(self, chunks: List[ChunkMetadata]) -> None:
        """Store chunks in batches for optimal performance."""
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            self._store_batch(batch)

    def _store_batch(self, chunks: List[ChunkMetadata]) -> None:
        """Store a single batch of chunks."""
        documents = [chunk.content for chunk in chunks]
        metadatas = [chunk.dict(exclude={'content'}) for chunk in chunks]
        ids = [str(chunk.chunk_id) for chunk in chunks]

        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
```

---

## 3. Error Handling Specifications

### 3.1 Exception Hierarchy
```python
class ShardMarkdownError(Exception):
    """Base exception for shard-markdown operations."""
    pass

class FileProcessingError(ShardMarkdownError):
    """Raised when file cannot be processed."""
    pass

class ChunkingError(ShardMarkdownError):
    """Raised when chunking operation fails."""
    pass

class DatabaseError(ShardMarkdownError):
    """Raised when database operations fail."""
    pass

class ConfigurationError(ShardMarkdownError):
    """Raised when configuration is invalid."""
    pass
```

### 3.2 Error Recovery Strategies
```python
class ErrorRecovery:
    @staticmethod
    def retry_with_backoff(func, max_attempts: int = 3, base_delay: float = 1.0):
        """Implement exponential backoff for transient failures."""
        for attempt in range(max_attempts):
            try:
                return func()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)

    @staticmethod
    def handle_partial_failure(chunks: List[ChunkMetadata], failed_chunks: List[int]):
        """Handle scenarios where some chunks fail to store."""
        # Log failed chunks, attempt to reprocess, or save for manual review
```

---

## 4. Performance Optimization Specifications

### 4.1 Memory Management
```python
class MemoryEfficientProcessor:
    def __init__(self, max_memory_mb: int = 512):
        self.max_memory_mb = max_memory_mb

    def process_large_file(self, file_path: str) -> Iterator[ChunkMetadata]:
        """Process large files using streaming approach."""
        # Use generators and streaming to minimize memory usage
        # Monitor memory usage and adjust processing accordingly

    def estimate_memory_usage(self, file_size: int, chunk_size: int) -> int:
        """Estimate memory requirements for processing."""
        # Calculate expected memory usage based on file size and configuration
```

### 4.2 Performance Monitoring
```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}

    def measure_processing_time(self, file_path: str, operation: str):
        """Decorator to measure operation performance."""
        # Implementation for timing operations

    def track_memory_usage(self):
        """Monitor memory usage during processing."""
        # Implementation for memory monitoring

    def generate_performance_report(self) -> dict:
        """Generate performance summary report."""
        return {
            "total_processing_time": self.metrics.get("total_time"),
            "average_chunk_time": self.metrics.get("avg_chunk_time"),
            "peak_memory_usage": self.metrics.get("peak_memory"),
            "throughput_chars_per_second": self.metrics.get("throughput")
        }
```

---

## 5. Testing Specifications

### 5.1 Unit Test Coverage Requirements
- CLI argument parsing and validation: 100%
- Chunking algorithm accuracy: 95%
- Metadata extraction: 100%
- ChromaDB integration: 90%
- Error handling: 85%

### 5.2 Integration Test Scenarios
```python
class IntegrationTests:
    def test_end_to_end_processing(self):
        """Test complete workflow from CLI to database storage."""

    def test_large_file_processing(self):
        """Test processing of 50MB+ markdown files."""

    def test_concurrent_processing(self):
        """Test multiple instances processing different files."""

    def test_error_recovery(self):
        """Test recovery from various failure scenarios."""
```

### 5.3 Performance Test Benchmarks
- Process 1MB file in under 5 seconds
- Process 10MB file in under 30 seconds
- Process 100MB file in under 300 seconds (5 minutes)
- Memory usage not exceeding 2x file size
- Successful storage rate > 99%

---

## 6. Security Specifications

### 6.1 Input Validation
```python
class SecurityValidator:
    @staticmethod
    def validate_file_path(file_path: str) -> bool:
        """Validate file path for security issues."""
        # Check for path traversal attacks
        # Validate file extensions
        # Check file permissions

    @staticmethod
    def sanitize_content(content: str) -> str:
        """Sanitize content if required."""
        # Remove or escape potentially dangerous content
        # Preserve markdown formatting
```

### 6.2 Data Protection
- No sensitive data logging in production mode
- Secure temporary file handling with proper cleanup
- Memory zeroing after processing sensitive content
- Optional content encryption for stored chunks

---

## 7. Deployment and Distribution

### 7.1 Package Structure
```
shard-markdown/
├── shard_markdown/
│   ├── __init__.py
│   ├── cli.py
│   ├── processor.py
│   ├── chunking.py
│   ├── database.py
│   ├── models.py
│   └── utils.py
├── tests/
├── docs/
├── setup.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

### 7.2 Installation Methods
1. **PyPI Installation:** `uv add shard-markdown`
2. **Development Installation:** `uv pip install -e .`
3. **Docker Container:** `docker run shard-markdown:latest`
4. **Conda Package:** `conda install -c conda-forge shard-markdown`

---

## 8. Monitoring and Observability

### 8.1 Logging Configuration
```python
LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard"
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "shard-markdown.log",
            "formatter": "json"
        }
    },
    "loggers": {
        "shard_markdown": {
            "level": "INFO",
            "handlers": ["console", "file"]
        }
    }
}
```

### 8.2 Metrics Collection
- Processing time per file size category
- Chunk creation success rate
- Database storage success rate
- Error frequency by category
- Memory usage patterns

---

## 9. API Compatibility and Versioning

### 9.1 Semantic Versioning
- **MAJOR:** Incompatible API changes
- **MINOR:** Backward-compatible functionality additions
- **PATCH:** Backward-compatible bug fixes

### 9.2 Configuration Backward Compatibility
- Support previous configuration file formats
- Graceful handling of deprecated options
- Clear migration paths for breaking changes

---

## 10. Documentation Requirements

### 10.1 User Documentation
- Installation guide with troubleshooting
- Complete CLI reference with examples
- Configuration file documentation
- Performance tuning guide
- Common use cases and workflows

### 10.2 Developer Documentation
- API reference documentation
- Extension and plugin development guide
- Contributing guidelines
- Architecture decision records
- Testing and development setup

---

This technical specification provides the detailed implementation guidance needed for the development team to build the shard-markdown CLI utility according to the requirements outlined in the PRD.
