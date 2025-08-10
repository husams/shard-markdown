# Implementation Guide

## 1. Project Structure

### 1.1 Recommended Directory Layout

```
shard-markdown/
├── pyproject.toml              # Project configuration and dependencies
├── README.md                   # Project overview and quick start
├── LICENSE                     # License file
├── .gitignore                  # Git ignore patterns
├── .github/                    # GitHub workflows and templates
│   ├── workflows/
│   │   ├── ci.yml             # Continuous integration
│   │   ├── release.yml        # Release automation
│   │   └── docs.yml           # Documentation building
│   └── ISSUE_TEMPLATE.md      # Issue template
├── docs/                       # Technical documentation
│   ├── technical-specification.md
│   ├── cli-interface.md
│   ├── architecture.md
│   ├── implementation-guide.md
│   ├── error-handling.md
│   ├── usage-examples.md
│   └── testing-strategy.md
├── src/
│   └── shard_markdown/        # Main package
│       ├── __init__.py        # Package initialization
│       ├── __main__.py        # CLI entry point
│       ├── cli/               # CLI interface layer
│       │   ├── __init__.py
│       │   ├── main.py        # Main CLI application
│       │   ├── commands/      # Command implementations
│       │   │   ├── __init__.py
│       │   │   ├── process.py
│       │   │   ├── collections.py
│       │   │   ├── query.py
│       │   │   └── config.py
│       │   └── utils.py       # CLI utilities
│       ├── core/              # Core business logic
│       │   ├── __init__.py
│       │   ├── processor.py   # Document processor
│       │   ├── parser.py      # Markdown parser
│       │   ├── chunking/      # Chunking engines
│       │   │   ├── __init__.py
│       │   │   ├── base.py    # Base chunker interface
│       │   │   ├── structure.py  # Structure-aware chunker
│       │   │   ├── fixed.py   # Fixed-size chunker
│       │   │   └── semantic.py   # Semantic chunker
│       │   ├── metadata.py    # Metadata extraction
│       │   └── models.py      # Data models
│       ├── chromadb/          # ChromaDB integration
│       │   ├── __init__.py
│       │   ├── client.py      # ChromaDB client wrapper
│       │   ├── collections.py # Collection management
│       │   └── operations.py  # Database operations
│       ├── config/            # Configuration management
│       │   ├── __init__.py
│       │   ├── settings.py    # Configuration models
│       │   ├── loader.py      # Configuration loading
│       │   └── defaults.py    # Default configurations
│       └── utils/             # Shared utilities
│           ├── __init__.py
│           ├── logging.py     # Logging configuration
│           ├── progress.py    # Progress tracking
│           └── validation.py  # Input validation
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── conftest.py           # Pytest configuration
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   ├── e2e/                  # End-to-end tests
│   ├── performance/          # Performance tests
│   └── fixtures/             # Test fixtures
└── scripts/                  # Development scripts
    ├── build.sh              # Build script
    ├── test.sh               # Test runner
    └── release.sh            # Release script
```

## 2. Technology Stack

### 2.1 Core Dependencies

#### 2.1.1 CLI Framework

```toml
# Primary choice: Click (mature, well-documented)
click = "^8.1.0"
rich = "^13.5.0"  # Enhanced terminal output
```

#### 2.1.2 Data Processing

```toml
# Document processing
markdown = "^3.5.0"           # Markdown parsing
python-frontmatter = "^1.0.0" # YAML frontmatter
pydantic = "^2.4.0"           # Data validation

# Text processing
tiktoken = "^0.5.0"           # Token counting (OpenAI)
nltk = "^3.8.0"               # Natural language processing (optional)
```

#### 2.1.3 Database Integration

```toml
# ChromaDB integration
chromadb = "^0.4.15"          # Vector database client
```

#### 2.1.4 Configuration and Utilities

```toml
# Configuration management
pyyaml = "^6.0.0"             # YAML configuration files
python-dotenv = "^1.0.0"      # Environment variable loading

# Utilities
pathlib2 = "^2.3.7"          # Enhanced path handling (Python <3.11)
typing-extensions = "^4.8.0"  # Type hints backport
```

### 2.2 Development Dependencies

```toml
[tool.poetry.group.dev.dependencies]
# Testing
pytest = "^7.4.0"
pytest-cov = "^4.1.0"
pytest-mock = "^3.11.0"
pytest-asyncio = "^0.21.0"
pytest-benchmark = "^4.0.0"

# Code quality
black = "^23.9.0"             # Code formatting
isort = "^5.12.0"             # Import sorting
flake8 = "^6.1.0"             # Linting
mypy = "^1.6.0"               # Type checking
pre-commit = "^3.4.0"         # Git hooks

# Documentation
sphinx = "^7.2.0"             # Documentation generation
sphinx-click = "^5.0.0"       # CLI documentation
```

## 3. Core Implementation Components

### 3.1 CLI Framework Implementation

#### 3.1.1 Main CLI Application (`cli/main.py`)

```python
import click
from rich.console import Console
from rich.traceback import install

from ..config import load_config, AppConfig
from ..utils.logging import setup_logging
from .commands import process, collections, query, config

# Install rich tracebacks for better error display
install(show_locals=True)

console = Console()

@click.group()
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Configuration file path')
@click.option('--verbose', '-v', count=True,
              help='Increase verbosity (can be repeated)')
@click.option('--quiet', '-q', is_flag=True,
              help='Suppress non-error output')
@click.option('--log-file', type=click.Path(),
              help='Write logs to specified file')
@click.pass_context
def cli(ctx, config, verbose, quiet, log_file):
    """Shard Markdown - Intelligent document chunking for ChromaDB."""

    # Ensure context object exists
    ctx.ensure_object(dict)

    # Load configuration
    app_config = load_config(config)
    ctx.obj['config'] = app_config

    # Setup logging
    log_level = max(0, 30 - (verbose * 10)) if not quiet else 40
    setup_logging(level=log_level, file_path=log_file)

    # Store CLI options
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet

# Register commands
cli.add_command(process.process)
cli.add_command(collections.collections)
cli.add_command(query.query)
cli.add_command(config.config)

if __name__ == '__main__':
    cli()
```

#### 3.1.2 Process Command Implementation (`cli/commands/process.py`)

```python
import click
from pathlib import Path
from typing import List
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from ...core.processor import DocumentProcessor
from ...core.models import ProcessingConfig, ProcessingResult
from ...chromadb.client import ChromaDBClient
from ...utils.validation import validate_input_paths

@click.command()
@click.argument('input_paths', nargs=-1, required=True, type=click.Path(exists=True))
@click.option('--collection', '-c', required=True,
              help='Target ChromaDB collection name')
@click.option('--chunk-size', '-s', default=1000, type=int,
              help='Maximum chunk size in characters')
@click.option('--chunk-overlap', '-o', default=200, type=int,
              help='Overlap between chunks in characters')
@click.option('--chunk-method', type=click.Choice(['structure', 'fixed', 'semantic']),
              default='structure', help='Chunking method')
@click.option('--recursive', '-r', is_flag=True,
              help='Process directories recursively')
@click.option('--create-collection', is_flag=True,
              help='Create collection if it doesn\'t exist')
@click.option('--dry-run', is_flag=True,
              help='Show what would be processed without executing')
@click.pass_context
def process(ctx, input_paths, collection, chunk_size, chunk_overlap,
           chunk_method, recursive, create_collection, dry_run):
    """Process markdown files into ChromaDB collections."""

    config = ctx.obj['config']

    try:
        # Validate input paths
        validated_paths = validate_input_paths(input_paths, recursive)

        if dry_run:
            _show_dry_run_preview(validated_paths, collection, chunk_size, chunk_overlap)
            return

        # Initialize ChromaDB client
        chroma_client = ChromaDBClient(config.chromadb)
        if not chroma_client.connect():
            raise click.ClickException("Failed to connect to ChromaDB")

        # Initialize document processor
        processing_config = ProcessingConfig(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunk_method=chunk_method
        )
        processor = DocumentProcessor(processing_config, chroma_client)

        # Process documents with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:

            task = progress.add_task("Processing documents...", total=len(validated_paths))

            results = []
            for path in validated_paths:
                result = processor.process_document(path, collection, create_collection)
                results.append(result)
                progress.update(task, advance=1)

        # Display results summary
        _display_results_summary(results)

    except Exception as e:
        raise click.ClickException(f"Processing failed: {str(e)}")

def _show_dry_run_preview(paths: List[Path], collection: str,
                         chunk_size: int, chunk_overlap: int):
    """Display dry run preview of what would be processed."""
    console = Console()

    console.print(f"[bold]Dry Run Preview[/bold]")
    console.print(f"Collection: {collection}")
    console.print(f"Chunk size: {chunk_size}")
    console.print(f"Chunk overlap: {chunk_overlap}")
    console.print(f"Files to process: {len(paths)}")

    for path in paths[:10]:  # Show first 10 files
        console.print(f"  • {path}")

    if len(paths) > 10:
        console.print(f"  ... and {len(paths) - 10} more files")

def _display_results_summary(results: List[ProcessingResult]):
    """Display processing results summary."""
    console = Console()

    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    total_chunks = sum(r.chunks_created for r in results if r.success)

    console.print(f"\n[bold green]Processing Complete[/bold green]")
    console.print(f"Successfully processed: {successful}/{len(results)} files")
    console.print(f"Total chunks created: {total_chunks}")

    if failed > 0:
        console.print(f"[bold red]Failed: {failed} files[/bold red]")
        for result in results:
            if not result.success:
                console.print(f"  • {result.file_path}: {result.error}")
```

### 3.2 Core Processing Engine Implementation

#### 3.2.1 Document Processor (`core/processor.py`)

```python
from pathlib import Path
from typing import Dict, List, Optional
import hashlib
import asyncio

from .parser import MarkdownParser
from .chunking import ChunkingEngine
from .metadata import MetadataExtractor
from .models import ProcessingConfig, ProcessingResult, DocumentChunk
from ..chromadb.client import ChromaDBClient
from ..utils.logging import get_logger

logger = get_logger(__name__)

class DocumentProcessor:
    """Main document processing coordinator."""

    def __init__(self, config: ProcessingConfig, chroma_client: ChromaDBClient):
        self.config = config
        self.chroma_client = chroma_client
        self.parser = MarkdownParser()
        self.chunker = ChunkingEngine(config)
        self.metadata_extractor = MetadataExtractor()

    def process_document(self, file_path: Path, collection_name: str,
                        create_collection: bool = False) -> ProcessingResult:
        """Process single document through full pipeline."""

        try:
            logger.info(f"Processing document: {file_path}")

            # Read and parse document
            content = self._read_file(file_path)
            document_ast = self.parser.parse(content)

            # Extract metadata
            base_metadata = self.metadata_extractor.extract_file_metadata(file_path)
            doc_metadata = self.metadata_extractor.extract_document_metadata(document_ast)

            # Chunk document
            chunks = self.chunker.chunk_document(document_ast)

            # Enhance chunks with metadata
            enhanced_chunks = []
            for i, chunk in enumerate(chunks):
                enhanced_chunk = self._enhance_chunk_metadata(
                    chunk, i, base_metadata, doc_metadata, file_path
                )
                enhanced_chunks.append(enhanced_chunk)

            # Store in ChromaDB
            collection = self.chroma_client.get_or_create_collection(
                collection_name, create_if_missing=create_collection
            )

            insert_result = self.chroma_client.bulk_insert(collection, enhanced_chunks)

            return ProcessingResult(
                file_path=file_path,
                success=True,
                chunks_created=len(enhanced_chunks),
                processing_time=insert_result.processing_time,
                collection_name=collection_name
            )

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")
            return ProcessingResult(
                file_path=file_path,
                success=False,
                error=str(e)
            )

    def process_batch(self, file_paths: List[Path], collection_name: str,
                     create_collection: bool = False) -> List[ProcessingResult]:
        """Process multiple documents sequentially for reliability."""

        results = []
        for path in file_paths:
            try:
                result = self.process_document(path, collection_name, create_collection)
                results.append(result)
            except Exception as e:
                logger.error(f"Batch processing error for {path}: {str(e)}")
                results.append(ProcessingResult(
                    file_path=path,
                    success=False,
                    error=str(e)
                ))

        return results

    def _read_file(self, file_path: Path) -> str:
        """Read file content with encoding detection."""

        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        raise ValueError(f"Could not decode file {file_path} with any supported encoding")

    def _enhance_chunk_metadata(self, chunk: DocumentChunk, index: int,
                               file_metadata: Dict, doc_metadata: Dict,
                               file_path: Path) -> DocumentChunk:
        """Enhance chunk with comprehensive metadata."""

        # Generate unique chunk ID
        chunk_id = self._generate_chunk_id(file_path, index)

        # Combine all metadata
        enhanced_metadata = {
            **file_metadata,
            **doc_metadata,
            **chunk.metadata,
            'chunk_id': chunk_id,
            'chunk_index': index,
            'source_file': str(file_path),
            'file_name': file_path.name,
        }

        return DocumentChunk(
            id=chunk_id,
            content=chunk.content,
            metadata=enhanced_metadata,
            start_position=chunk.start_position,
            end_position=chunk.end_position
        )

    def _generate_chunk_id(self, file_path: Path, chunk_index: int) -> str:
        """Generate unique chunk identifier."""

        file_hash = hashlib.sha256(str(file_path).encode()).hexdigest()[:16]
        return f"{file_hash}_{chunk_index:04d}"
```

#### 3.2.2 Structure-Aware Chunking (`core/chunking/structure.py`)

```python
from typing import List, Optional
from markdown import Markdown
from markdown.extensions import toc
from markdown.treeprocessors import Treeprocessor

from ..models import DocumentChunk, MarkdownAST, ChunkingConfig
from .base import BaseChunker

class StructureAwareChunker(BaseChunker):
    """Intelligent chunking that respects markdown structure."""

    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        self.md = Markdown(extensions=['toc', 'codehilite', 'fenced_code'])

    def chunk_document(self, ast: MarkdownAST) -> List[DocumentChunk]:
        """Chunk document while respecting structure boundaries."""

        chunks = []
        current_chunk = ""
        current_start = 0
        current_context = []

        for element in ast.elements:
            element_text = self._element_to_text(element)

            # Check if adding this element exceeds chunk size
            if (len(current_chunk) + len(element_text) > self.config.chunk_size
                and current_chunk):

                # Create chunk with current content
                chunk = self._create_chunk(
                    current_chunk,
                    current_start,
                    current_start + len(current_chunk),
                    current_context.copy()
                )
                chunks.append(chunk)

                # Start new chunk with overlap
                overlap_content = self._get_overlap_content(current_chunk)
                current_chunk = overlap_content + element_text
                current_start = chunk.end_position - len(overlap_content)
            else:
                current_chunk += element_text

            # Update structural context
            if element.type == 'header':
                self._update_context(current_context, element)

        # Add final chunk if content remains
        if current_chunk.strip():
            chunk = self._create_chunk(
                current_chunk,
                current_start,
                current_start + len(current_chunk),
                current_context
            )
            chunks.append(chunk)

        return chunks

    def _create_chunk(self, content: str, start: int, end: int,
                     context: List[str]) -> DocumentChunk:
        """Create document chunk with metadata."""

        return DocumentChunk(
            content=content.strip(),
            metadata={
                'structural_context': ' > '.join(context),
                'parent_sections': context.copy(),
                'chunk_method': 'structure_aware'
            },
            start_position=start,
            end_position=end
        )

    def _get_overlap_content(self, content: str) -> str:
        """Get overlap content from end of current chunk."""

        if len(content) <= self.config.overlap:
            return content

        # Try to find sentence boundary for natural overlap
        overlap_start = len(content) - self.config.overlap

        # Look for sentence endings
        for i in range(overlap_start, len(content)):
            if content[i] in '.!?':
                return content[i+1:].lstrip()

        # Fallback to character-based overlap
        return content[-self.config.overlap:]

    def _update_context(self, context: List[str], header_element):
        """Update hierarchical context based on header level."""

        level = header_element.level
        header_text = header_element.text

        # Truncate context to appropriate level
        context[:] = context[:level-1]

        # Add current header
        if len(context) >= level:
            context[level-1] = header_text
        else:
            context.extend([''] * (level - len(context) - 1))
            context.append(header_text)

    def _element_to_text(self, element) -> str:
        """Convert AST element to text representation."""

        if element.type == 'header':
            return f"{'#' * element.level} {element.text}\n\n"
        elif element.type == 'paragraph':
            return f"{element.text}\n\n"
        elif element.type == 'code_block':
            return f"```{element.language or ''}\n{element.text}\n```\n\n"
        elif element.type == 'list':
            items = '\n'.join(f"- {item}" for item in element.items)
            return f"{items}\n\n"
        else:
            return f"{element.text}\n\n"
```

### 3.3 ChromaDB Integration Implementation

#### 3.3.1 ChromaDB Client (`chromadb/client.py`)

```python
import chromadb
from chromadb.config import Settings
from typing import Dict, List, Optional
import time

from ..config.settings import ChromaDBConfig
from ..core.models import DocumentChunk
from ..utils.logging import get_logger

logger = get_logger(__name__)

class ChromaDBClient:
    """ChromaDB client wrapper with connection management."""

    def __init__(self, config: ChromaDBConfig):
        self.config = config
        self.client = None
        self._connection_validated = False

    def connect(self) -> bool:
        """Establish connection to ChromaDB instance."""

        try:
            settings = Settings(
                chroma_server_host=self.config.host,
                chroma_server_http_port=self.config.port,
                chroma_server_ssl_enabled=self.config.ssl,
                chroma_server_grpc_port=None  # Disable gRPC
            )

            if self.config.ssl:
                settings.chroma_server_ssl_enabled = True

            self.client = chromadb.HttpClient(
                host=self.config.host,
                port=self.config.port,
                ssl=self.config.ssl,
                headers=self._get_auth_headers()
            )

            # Validate connection
            self.client.heartbeat()
            self._connection_validated = True

            logger.info(f"Connected to ChromaDB at {self.config.host}:{self.config.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {str(e)}")
            return False

    def get_or_create_collection(self, name: str,
                                create_if_missing: bool = False,
                                metadata: Optional[Dict] = None) -> chromadb.Collection:
        """Get existing or create new collection."""

        if not self._connection_validated:
            raise RuntimeError("ChromaDB connection not established")

        try:
            # Try to get existing collection
            collection = self.client.get_collection(name)
            logger.info(f"Retrieved existing collection: {name}")
            return collection

        except Exception:
            if not create_if_missing:
                raise ValueError(f"Collection '{name}' does not exist and create_if_missing=False")

            # Create new collection
            collection_metadata = metadata or {}
            collection_metadata.update({
                'created_by': 'shard-md-cli',
                'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'version': '1.0.0'
            })

            collection = self.client.create_collection(
                name=name,
                metadata=collection_metadata
            )

            logger.info(f"Created new collection: {name}")
            return collection

    def bulk_insert(self, collection: chromadb.Collection,
                   chunks: List[DocumentChunk]) -> 'InsertResult':
        """Bulk insert chunks with progress tracking."""

        start_time = time.time()

        try:
            # Prepare data for insertion
            ids = [chunk.id for chunk in chunks]
            documents = [chunk.content for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]

            # Insert into collection
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

            processing_time = time.time() - start_time

            logger.info(f"Inserted {len(chunks)} chunks in {processing_time:.2f}s")

            return InsertResult(
                success=True,
                chunks_inserted=len(chunks),
                processing_time=processing_time
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Bulk insert failed after {processing_time:.2f}s: {str(e)}")

            return InsertResult(
                success=False,
                error=str(e),
                processing_time=processing_time
            )

    def list_collections(self) -> List[Dict]:
        """List all available collections."""

        if not self._connection_validated:
            raise RuntimeError("ChromaDB connection not established")

        try:
            collections = self.client.list_collections()

            collection_info = []
            for collection in collections:
                info = {
                    'name': collection.name,
                    'metadata': collection.metadata,
                    'count': collection.count()
                }
                collection_info.append(info)

            return collection_info

        except Exception as e:
            logger.error(f"Failed to list collections: {str(e)}")
            raise

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers if token is configured."""

        headers = {}
        if self.config.auth_token:
            headers['Authorization'] = f"Bearer {self.config.auth_token}"

        return headers

class InsertResult:
    """Result of bulk insert operation."""

    def __init__(self, success: bool, chunks_inserted: int = 0,
                 processing_time: float = 0.0, error: Optional[str] = None):
        self.success = success
        self.chunks_inserted = chunks_inserted
        self.processing_time = processing_time
        self.error = error
```

## 4. Configuration Management

### 4.1 Configuration Schema (`config/settings.py`)

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum
from pathlib import Path

class ChunkingMethod(str, Enum):
    STRUCTURE = "structure"
    FIXED = "fixed"
    SEMANTIC = "semantic"

class ChromaDBConfig(BaseModel):
    """ChromaDB connection configuration."""

    host: str = Field(default="localhost", description="ChromaDB server host")
    port: int = Field(default=8000, ge=1, le=65535, description="ChromaDB server port")
    ssl: bool = Field(default=False, description="Use SSL connection")
    auth_token: Optional[str] = Field(default=None, description="Authentication token")
    timeout: int = Field(default=30, ge=1, description="Connection timeout in seconds")

    @validator('host')
    def validate_host(cls, v):
        if not v or not v.strip():
            raise ValueError("Host cannot be empty")
        return v.strip()

class ChunkingConfig(BaseModel):
    """Document chunking configuration."""

    default_size: int = Field(default=1000, ge=100, le=10000,
                             description="Default chunk size in characters")
    default_overlap: int = Field(default=200, ge=0, le=1000,
                                description="Default overlap between chunks")
    method: ChunkingMethod = Field(default=ChunkingMethod.STRUCTURE,
                                  description="Default chunking method")
    respect_boundaries: bool = Field(default=True,
                                   description="Respect markdown structure boundaries")
    max_tokens: Optional[int] = Field(default=None, ge=1,
                                     description="Maximum tokens per chunk")

    @validator('default_overlap')
    def validate_overlap(cls, v, values):
        if 'default_size' in values and v >= values['default_size']:
            raise ValueError("Overlap must be less than chunk size")
        return v

class ProcessingConfig(BaseModel):
    """Document processing configuration."""

    batch_size: int = Field(default=10, ge=1, le=100,
                           description="Number of documents to process in batch")
    recursive: bool = Field(default=False,
                           description="Process directories recursively by default")
    pattern: str = Field(default="*.md",
                        description="Default file pattern for filtering")
    include_frontmatter: bool = Field(default=True,
                                     description="Extract YAML frontmatter as metadata")
    include_path_metadata: bool = Field(default=True,
                                       description="Include file path information")

class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Default logging level")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                       description="Log message format")
    file_path: Optional[Path] = Field(default=None,
                                     description="Log file path")
    max_file_size: int = Field(default=10485760,  # 10MB
                              description="Maximum log file size in bytes")
    backup_count: int = Field(default=5,
                             description="Number of backup log files to keep")

class AppConfig(BaseModel):
    """Main application configuration."""

    chromadb: ChromaDBConfig = Field(default_factory=ChromaDBConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Custom user settings
    custom_metadata: Dict[str, Any] = Field(default_factory=dict,
                                           description="Custom metadata to add to all chunks")
    plugins: List[str] = Field(default_factory=list,
                              description="List of plugin modules to load")

    class Config:
        env_prefix = "SHARD_MD_"
        case_sensitive = False
```

## 5. Package Configuration

### 5.1 pyproject.toml

```toml
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "shard-markdown"
version = "0.1.0"
description = "Intelligent markdown document chunking for ChromaDB collections"
authors = ["Your Name <your.email@example.com>"]
license = "MIT"
readme = "README.md"
homepage = "https://github.com/yourusername/shard-markdown"
repository = "https://github.com/yourusername/shard-markdown"
documentation = "https://shard-markdown.readthedocs.io"
keywords = ["markdown", "chromadb", "cli", "chunking", "vector-database"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Text Processing :: Markup",
    "Topic :: Database",
]

[tool.poetry.dependencies]
python = "^3.8"
click = "^8.1.0"
rich = "^13.5.0"
markdown = "^3.5.0"
python-frontmatter = "^1.0.0"
pydantic = "^2.4.0"
chromadb = "^0.4.15"
pyyaml = "^6.0.0"
python-dotenv = "^1.0.0"
tiktoken = "^0.5.0"
typing-extensions = "^4.8.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-cov = "^4.1.0"
pytest-mock = "^3.11.0"
pytest-asyncio = "^0.21.0"
pytest-benchmark = "^4.0.0"
black = "^23.9.0"
isort = "^5.12.0"
flake8 = "^6.1.0"
mypy = "^1.6.0"
pre-commit = "^3.4.0"
sphinx = "^7.2.0"
sphinx-click = "^5.0.0"

[tool.poetry.scripts]
shard-md = "shard_markdown.cli.main:cli"

[tool.black]
line-length = 88
target-version = ['py38']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_first_party = ["shard_markdown"]

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[[tool.mypy.overrides]]
module = [
    "chromadb.*",
    "markdown.*",
    "frontmatter.*",
    "tiktoken.*"
]
ignore_missing_imports = true

[tool.pytest.ini_options]
minversion = "6.0"
addopts = "-ra -q --strict-markers --strict-config"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
    "e2e: marks tests as end-to-end tests",
]

[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*", "*/test_*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if self.debug:",
    "if settings.DEBUG",
    "raise AssertionError",
    "raise NotImplementedError",
    "if 0:",
    "if __name__ == .__main__.:",
    "class .*\\bProtocol\\):",
    "@(abc\\.)?abstractmethod",
]
```

## 6. Installation and Development Setup

### 6.1 Development Environment Setup

```bash
# Clone repository
git clone https://github.com/yourusername/shard-markdown.git
cd shard-markdown

# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Install pre-commit hooks
poetry run pre-commit install

# Run tests
poetry run pytest

# Run CLI in development mode
poetry run shard-md --help
```

### 6.2 Build and Distribution Scripts

#### 6.2.1 Build Script (`scripts/build.sh`)

```bash
#!/bin/bash
set -e

echo "Building shard-markdown package..."

# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Run tests
echo "Running tests..."
poetry run pytest

# Run linting
echo "Running code quality checks..."
poetry run black --check src/ tests/
poetry run isort --check-only src/ tests/
poetry run flake8 src/ tests/
poetry run mypy src/

# Build package
echo "Building package..."
poetry build

echo "Build complete! Distribution files are in dist/"
ls -la dist/
```

#### 6.2.2 Release Script (`scripts/release.sh`)

```bash
#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 1.0.0"
    exit 1
fi

VERSION=$1

echo "Preparing release $VERSION..."

# Update version
poetry version $VERSION

# Build package
./scripts/build.sh

# Create git tag
git add pyproject.toml
git commit -m "Bump version to $VERSION"
git tag -a "v$VERSION" -m "Release version $VERSION"

echo "Release $VERSION prepared!"
echo "To publish:"
echo "  git push origin main"
echo "  git push origin v$VERSION"
echo "  poetry publish"
```

This implementation guide provides a comprehensive foundation for building the shard-markdown CLI tool with all the specified requirements and following Python best practices.
