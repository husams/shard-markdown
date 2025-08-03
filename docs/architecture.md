# Architecture Overview

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Interface │────│  Core Engine    │────│   ChromaDB      │
│                 │    │                 │    │   Integration   │
│ • Command Parser│    │ • Document      │    │                 │
│ • Argument      │    │   Processor     │    │ • Collection    │
│   Validation    │    │ • Chunking      │    │   Management    │
│ • User Feedback │    │   Engine        │    │ • Document      │
│ • Progress      │    │ • Metadata      │    │   Storage       │
│   Tracking      │    │   Extractor     │    │ • Query Engine  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Configuration  │    │   File System   │    │    Logging      │
│   Management    │    │    Handler      │    │   & Monitoring  │
│                 │    │                 │    │                 │
│ • Settings      │    │ • File I/O      │    │ • Structured    │
│   Validation    │    │ • Directory     │    │   Logging       │
│ • Profile       │    │   Traversal     │    │ • Progress      │
│   Management    │    │ • Format        │    │   Metrics       │
│ • Environment   │    │   Detection     │    │ • Error         │
│   Variables     │    │ • Batch         │    │   Reporting     │
│                 │    │   Processing    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 1.2 Component Layering

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ CLI Parser  │  │ User Output │  │  Progress Display   │  │
│  │ (Click)     │  │ (Rich)      │  │  (Rich Progress)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Command     │  │ Workflow    │  │  Configuration      │  │
│  │ Handlers    │  │ Orchestra.  │  │  Management         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     Business Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Document    │  │ Chunking    │  │  Metadata           │  │
│  │ Processor   │  │ Engine      │  │  Extractor          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Integration Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ ChromaDB    │  │ File System │  │  Logging &          │  │
│  │ Adapter     │  │ Adapter     │  │  Monitoring         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ ChromaDB    │  │ File System │  │  Python Runtime     │  │
│  │ Instance    │  │ & Storage   │  │  & Dependencies     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 2. Core Components

### 2.1 CLI Interface Module (`cli/`)

#### 2.1.1 Command Parser (`cli/parser.py`)

```python
class CommandParser:
    """Main CLI command parser using Click framework"""

    def __init__(self):
        self.app = click.Group()
        self._register_commands()

    def _register_commands(self):
        """Register all CLI commands and subcommands"""
        pass

    def parse_and_execute(self, args: List[str]) -> int:
        """Parse arguments and execute appropriate command"""
        pass
```

#### 2.1.2 Command Handlers (`cli/commands/`)

```python
# cli/commands/process.py
class ProcessCommand:
    """Handler for document processing operations"""

    def execute(self, input_paths: List[str], options: ProcessOptions) -> ProcessResult:
        """Execute document processing workflow"""
        pass

# cli/commands/collections.py
class CollectionsCommand:
    """Handler for collection management operations"""

    def list_collections(self, options: ListOptions) -> List[CollectionInfo]:
        """List available collections"""
        pass

    def create_collection(self, name: str, options: CreateOptions) -> CollectionInfo:
        """Create new collection"""
        pass
```

### 2.2 Document Processing Engine (`core/`)

#### 2.2.1 Document Processor (`core/processor.py`)

```python
class DocumentProcessor:
    """Main document processing coordinator"""

    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.parser = MarkdownParser()
        self.chunker = ChunkingEngine(config.chunking)
        self.metadata_extractor = MetadataExtractor()

    def process_document(self, file_path: Path) -> ProcessingResult:
        """Process single document through full pipeline"""
        pass

    def process_batch(self, file_paths: List[Path]) -> BatchResult:
        """Process multiple documents with concurrency"""
        pass
```

#### 2.2.2 Markdown Parser (`core/parser.py`)

```python
class MarkdownParser:
    """Markdown document parser with AST generation"""

    def parse(self, content: str) -> MarkdownAST:
        """Parse markdown content into structured AST"""
        pass

    def extract_frontmatter(self, content: str) -> Tuple[Dict, str]:
        """Extract YAML frontmatter and content"""
        pass
```

#### 2.2.3 Chunking Engine (`core/chunking.py`)

```python
class ChunkingEngine:
    """Intelligent document chunking with structure awareness"""

    def __init__(self, config: ChunkingConfig):
        self.config = config
        self.strategies = {
            'structure': StructureAwareChunker(),
            'fixed': FixedSizeChunker(),
            'semantic': SemanticChunker()
        }

    def chunk_document(self, ast: MarkdownAST) -> List[DocumentChunk]:
        """Chunk document based on configured strategy"""
        pass
```

### 2.3 ChromaDB Integration (`chromadb/`)

#### 2.3.1 ChromaDB Client (`chromadb/client.py`)

```python
class ChromaDBClient:
    """ChromaDB client wrapper with connection management"""

    def __init__(self, config: ChromaDBConfig):
        self.config = config
        self.client = None
        self.connection_pool = ConnectionPool()

    def connect(self) -> bool:
        """Establish connection to ChromaDB instance"""
        pass

    def get_or_create_collection(self, name: str, metadata: Dict) -> Collection:
        """Get existing or create new collection"""
        pass
```

#### 2.3.2 Collection Manager (`chromadb/collections.py`)

```python
class CollectionManager:
    """High-level collection management operations"""

    def __init__(self, client: ChromaDBClient):
        self.client = client

    def create_collection(self, spec: CollectionSpec) -> Collection:
        """Create collection with validation"""
        pass

    def bulk_insert(self, collection: Collection, chunks: List[DocumentChunk]) -> InsertResult:
        """Bulk insert chunks with progress tracking"""
        pass
```

### 2.4 Configuration Management (`config/`)

#### 2.4.1 Configuration Schema (`config/schema.py`)

```python
class ChromaDBConfig(BaseModel):
    """ChromaDB connection configuration"""
    host: str = "localhost"
    port: int = 8000
    ssl: bool = False
    auth_token: Optional[str] = None
    timeout: int = 30

class ChunkingConfig(BaseModel):
    """Document chunking configuration"""
    default_size: int = 1000
    default_overlap: int = 200
    method: ChunkingMethod = ChunkingMethod.STRUCTURE
    respect_boundaries: bool = True
    max_tokens: Optional[int] = None

class AppConfig(BaseModel):
    """Main application configuration"""
    chromadb: ChromaDBConfig = ChromaDBConfig()
    chunking: ChunkingConfig = ChunkingConfig()
    processing: ProcessingConfig = ProcessingConfig()
    logging: LoggingConfig = LoggingConfig()
```

## 3. Data Flow Architecture

### 3.1 Processing Pipeline Flow

```
Input Files
    │
    ▼
┌─────────────────┐
│ File Discovery  │ ──── Recursive directory traversal
│ & Validation    │      Pattern matching & filtering
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Batch Grouping  │ ──── Group files for efficient processing
│ & Scheduling    │      Load balancing across workers
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Document        │ ──── Read file content
│ Loading         │      Encoding detection & validation
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Markdown        │ ──── Parse to AST
│ Parsing         │      Extract frontmatter
└─────────────────┘      Validate structure
    │
    ▼
┌─────────────────┐
│ Intelligent     │ ──── Structure-aware chunking
│ Chunking        │      Size & overlap management
└─────────────────┘      Context preservation
    │
    ▼
┌─────────────────┐
│ Metadata        │ ──── Extract file metadata
│ Enhancement     │      Enhance with custom fields
└─────────────────┘      Validate metadata schema
    │
    ▼
┌─────────────────┐
│ ChromaDB        │ ──── Collection management
│ Operations      │      Bulk document insertion
└─────────────────┘      Index optimization
    │
    ▼
┌─────────────────┐
│ Result          │ ──── Success/failure reporting
│ Aggregation     │      Performance metrics
└─────────────────┘      Error analysis
```

### 3.2 Error Handling Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Operation     │────│  Error Handler  │────│  Error Reporter │
│   Execution     │    │                 │    │                 │
└─────────────────┘    │ • Categorize    │    │ • Log Error     │
         │              │   Error Type    │    │ • User Notice   │
         │              │ • Determine     │    │ • Metrics       │
    (Exception)         │   Recovery      │    │   Update        │
         │              │   Strategy      │    │                 │
         ▼              │ • Execute       │    └─────────────────┘
┌─────────────────┐    │   Recovery      │
│  Error Context  │────│                 │
│  Collection     │    └─────────────────┘
│                 │             │
│ • Stack Trace   │             ▼
│ • Operation     │    ┌─────────────────┐
│   Context       │    │  Recovery       │
│ • User Input    │    │  Actions        │
│ • System State  │    │                 │
└─────────────────┘    │ • Retry         │
                       │ • Skip          │
                       │ • Abort         │
                       │ • Fallback      │
                       └─────────────────┘
```

## 4. Database Schema Design

### 4.1 ChromaDB Collection Structure

```python
# Collection Metadata Schema
collection_metadata = {
    "name": "collection_name",
    "description": "Human-readable description",
    "created_at": "2024-01-01T00:00:00Z",
    "created_by": "shard-md-cli",
    "version": "1.0.0",
    "embedding_function": "default",
    "chunk_strategy": "structure",
    "source_files_count": 150,
    "total_chunks": 1250,
    "avg_chunk_size": 875,
    "custom_metadata": {
        "project": "documentation",
        "team": "engineering"
    }
}

# Document Chunk Schema
chunk_document = {
    "id": "doc_hash_chunk_index",
    "content": "chunk text content",
    "metadata": {
        # File-level metadata
        "source_file": "/path/to/document.md",
        "file_name": "document.md",
        "file_size": 12345,
        "file_modified": "2024-01-01T00:00:00Z",
        "file_hash": "sha256_hash",

        # Document-level metadata
        "title": "Document Title",
        "author": "Author Name",
        "tags": ["tag1", "tag2"],
        "frontmatter": {...},

        # Chunk-level metadata
        "chunk_index": 0,
        "chunk_size": 875,
        "chunk_start": 0,
        "chunk_end": 875,
        "overlap_start": 0,
        "overlap_end": 100,
        "structural_context": "## Section Title",
        "parent_sections": ["# Main Title", "## Section Title"],

        # Processing metadata
        "processed_at": "2024-01-01T00:00:00Z",
        "processed_by": "shard-md-cli",
        "chunking_method": "structure",
        "version": "1.0.0"
    },
    "embedding": [0.1, 0.2, ...],  # Generated by ChromaDB
}
```

## 5. Concurrency and Performance

### 5.1 Threading Model

```python
class ProcessingPool:
    """Manages concurrent document processing"""

    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.semaphore = Semaphore(max_workers)

    async def process_batch(self, documents: List[Path]) -> List[ProcessingResult]:
        """Process documents concurrently with resource management"""
        tasks = []
        for doc in documents:
            task = self.executor.submit(self._process_single, doc)
            tasks.append(task)

        return await asyncio.gather(*tasks)
```

### 5.2 Memory Management

```python
class MemoryManager:
    """Manages memory usage during processing"""

    def __init__(self, max_memory_mb: int = 512):
        self.max_memory = max_memory_mb * 1024 * 1024
        self.current_usage = 0

    def can_process(self, document_size: int) -> bool:
        """Check if document can be processed within memory limits"""
        estimated_usage = document_size * 2.5  # Processing overhead
        return (self.current_usage + estimated_usage) < self.max_memory
```

## 6. Extension Points

### 6.1 Plugin Architecture

```python
class ChunkingPlugin(ABC):
    """Base class for custom chunking strategies"""

    @abstractmethod
    def chunk(self, document: MarkdownAST, config: ChunkingConfig) -> List[DocumentChunk]:
        """Implement custom chunking logic"""
        pass

class MetadataExtractorPlugin(ABC):
    """Base class for custom metadata extractors"""

    @abstractmethod
    def extract(self, document: MarkdownAST, file_path: Path) -> Dict[str, Any]:
        """Extract custom metadata from document"""
        pass
```

### 6.2 Configuration Extension

```python
class PluginManager:
    """Manages loading and execution of plugins"""

    def __init__(self):
        self.chunking_plugins: Dict[str, ChunkingPlugin] = {}
        self.metadata_plugins: List[MetadataExtractorPlugin] = []

    def register_chunking_plugin(self, name: str, plugin: ChunkingPlugin):
        """Register custom chunking strategy"""
        self.chunking_plugins[name] = plugin

    def load_plugins_from_config(self, config: PluginConfig):
        """Load plugins specified in configuration"""
        pass
```

## 7. Testing Architecture

### 7.1 Test Structure

```
tests/
├── unit/
│   ├── test_chunking.py
│   ├── test_parser.py
│   ├── test_chromadb.py
│   └── test_config.py
├── integration/
│   ├── test_cli_commands.py
│   ├── test_processing_pipeline.py
│   └── test_chromadb_integration.py
├── e2e/
│   ├── test_full_workflow.py
│   └── test_cli_interface.py
├── performance/
│   ├── test_benchmarks.py
│   └── test_memory_usage.py
└── fixtures/
    ├── sample_documents/
    ├── config_files/
    └── expected_outputs/
```

### 7.2 Mock and Fixture Strategy

```python
class MockChromaDBClient:
    """Mock ChromaDB client for testing"""

    def __init__(self):
        self.collections = {}
        self.documents = {}

    def create_collection(self, name: str, metadata: Dict) -> MockCollection:
        """Create mock collection"""
        pass

@pytest.fixture
def sample_markdown_documents():
    """Provide sample markdown documents for testing"""
    return [
        Path("tests/fixtures/sample_documents/simple.md"),
        Path("tests/fixtures/sample_documents/complex.md"),
        Path("tests/fixtures/sample_documents/with_frontmatter.md")
    ]
```
