# Error Handling Specification

## 1. Error Classification System

### 1.1 Error Categories

#### 1.1.1 Input Validation Errors (Category: INPUT)

- **Code Range**: 1000-1099
- **Description**: Errors related to invalid user input, arguments, or file formats
- **Recovery Strategy**: User correction required
- **Examples**: Invalid file paths, unsupported file formats, malformed configuration

#### 1.1.2 Configuration Errors (Category: CONFIG)

- **Code Range**: 1100-1199
- **Description**: Errors in configuration loading, validation, or environment setup
- **Recovery Strategy**: Configuration correction or environment setup
- **Examples**: Missing config files, invalid configuration values, environment variable issues

#### 1.1.3 File System Errors (Category: FILESYSTEM)

- **Code Range**: 1200-1299
- **Description**: File system access, permission, and I/O errors
- **Recovery Strategy**: File system correction or permission adjustment
- **Examples**: File not found, permission denied, disk space issues, encoding problems

#### 1.1.4 Processing Errors (Category: PROCESSING)

- **Code Range**: 1300-1399
- **Description**: Errors during document parsing, chunking, or content processing
- **Recovery Strategy**: Skip file or adjust processing parameters
- **Examples**: Markdown parsing errors, chunking failures, metadata extraction issues

#### 1.1.5 ChromaDB Errors (Category: DATABASE)

- **Code Range**: 1400-1499
- **Description**: ChromaDB connection, operation, and data integrity errors
- **Recovery Strategy**: Retry operation, check connection, or adjust database configuration
- **Examples**: Connection failures, authentication errors, collection issues, insertion failures

#### 1.1.6 System Errors (Category: SYSTEM)

- **Code Range**: 1500-1599
- **Description**: System-level errors including memory, threading, and resource constraints
- **Recovery Strategy**: Resource adjustment or system configuration changes
- **Examples**: Out of memory, thread pool exhaustion, resource limits exceeded

#### 1.1.7 Network Errors (Category: NETWORK)

- **Code Range**: 1600-1699
- **Description**: Network connectivity and communication errors
- **Recovery Strategy**: Retry with backoff or check network configuration
- **Examples**: Connection timeouts, DNS resolution failures, SSL/TLS errors

## 2. Error Handling Architecture

### 2.1 Exception Hierarchy

```python
class ShardMarkdownError(Exception):
    """Base exception for all shard-markdown errors."""

    def __init__(self, message: str, error_code: int, category: str,
                 context: Optional[Dict[str, Any]] = None,
                 cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.category = category
        self.context = context or {}
        self.cause = cause
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/reporting."""
        return {
            'error_code': self.error_code,
            'category': self.category,
            'message': self.message,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'cause': str(self.cause) if self.cause else None
        }

class InputValidationError(ShardMarkdownError):
    """Errors related to invalid input validation."""

    def __init__(self, message: str, error_code: int = 1000, **kwargs):
        super().__init__(message, error_code, "INPUT", **kwargs)

class ConfigurationError(ShardMarkdownError):
    """Errors related to configuration issues."""

    def __init__(self, message: str, error_code: int = 1100, **kwargs):
        super().__init__(message, error_code, "CONFIG", **kwargs)

class FileSystemError(ShardMarkdownError):
    """Errors related to file system operations."""

    def __init__(self, message: str, error_code: int = 1200, **kwargs):
        super().__init__(message, error_code, "FILESYSTEM", **kwargs)

class ProcessingError(ShardMarkdownError):
    """Errors during document processing."""

    def __init__(self, message: str, error_code: int = 1300, **kwargs):
        super().__init__(message, error_code, "PROCESSING", **kwargs)

class ChromaDBError(ShardMarkdownError):
    """Errors related to ChromaDB operations."""

    def __init__(self, message: str, error_code: int = 1400, **kwargs):
        super().__init__(message, error_code, "DATABASE", **kwargs)

class SystemError(ShardMarkdownError):
    """System-level errors."""

    def __init__(self, message: str, error_code: int = 1500, **kwargs):
        super().__init__(message, error_code, "SYSTEM", **kwargs)

class NetworkError(ShardMarkdownError):
    """Network-related errors."""

    def __init__(self, message: str, error_code: int = 1600, **kwargs):
        super().__init__(message, error_code, "NETWORK", **kwargs)
```

### 2.2 Error Context Collection

```python
class ErrorContext:
    """Collects and manages error context information."""

    def __init__(self):
        self._context = {}

    def add_file_context(self, file_path: Path, operation: str):
        """Add file-related context."""
        self._context.update({
            'file_path': str(file_path),
            'file_size': file_path.stat().st_size if file_path.exists() else None,
            'operation': operation,
            'file_exists': file_path.exists()
        })

    def add_processing_context(self, chunk_count: int, chunk_size: int, method: str):
        """Add processing-related context."""
        self._context.update({
            'chunk_count': chunk_count,
            'chunk_size': chunk_size,
            'chunking_method': method
        })

    def add_chromadb_context(self, collection_name: str, operation: str):
        """Add ChromaDB-related context."""
        self._context.update({
            'collection_name': collection_name,
            'database_operation': operation
        })

    def add_system_context(self):
        """Add system-related context."""
        import psutil
        self._context.update({
            'memory_available': psutil.virtual_memory().available,
            'cpu_percent': psutil.cpu_percent(),
            'disk_free': psutil.disk_usage('/').free
        })

    def get_context(self) -> Dict[str, Any]:
        """Get current context."""
        return self._context.copy()
```

## 3. Specific Error Scenarios

### 3.1 Input Validation Errors

#### 3.1.1 Invalid File Path (Code: 1001)

```python
def validate_input_paths(paths: List[str], recursive: bool) -> List[Path]:
    """Validate input file paths."""

    validated_paths = []
    for path_str in paths:
        try:
            path = Path(path_str).resolve()

            if not path.exists():
                raise InputValidationError(
                    f"Path does not exist: {path}",
                    error_code=1001,
                    context={'path': str(path), 'operation': 'path_validation'}
                )

            if path.is_file():
                if not path.suffix.lower() == '.md':
                    raise InputValidationError(
                        f"File is not a markdown file: {path}",
                        error_code=1002,
                        context={'path': str(path), 'suffix': path.suffix}
                    )
                validated_paths.append(path)

            elif path.is_dir():
                if recursive:
                    md_files = list(path.rglob('*.md'))
                    if not md_files:
                        raise InputValidationError(
                            f"No markdown files found in directory: {path}",
                            error_code=1003,
                            context={'path': str(path), 'recursive': True}
                        )
                    validated_paths.extend(md_files)
                else:
                    raise InputValidationError(
                        f"Path is directory but recursive flag not set: {path}",
                        error_code=1004,
                        context={'path': str(path), 'recursive': False}
                    )

        except OSError as e:
            raise FileSystemError(
                f"Cannot access path: {path_str}",
                error_code=1201,
                context={'path': path_str, 'os_error': str(e)},
                cause=e
            )

    return validated_paths
```

#### 3.1.2 Invalid Configuration Values (Code: 1101-1110)

```python
def validate_chunk_size(chunk_size: int, chunk_overlap: int) -> None:
    """Validate chunking parameters."""

    if chunk_size <= 0:
        raise ConfigurationError(
            "Chunk size must be positive",
            error_code=1101,
            context={'chunk_size': chunk_size}
        )

    if chunk_size < 100:
        raise ConfigurationError(
            "Chunk size too small (minimum 100 characters)",
            error_code=1102,
            context={'chunk_size': chunk_size, 'minimum': 100}
        )

    if chunk_size > 50000:
        raise ConfigurationError(
            "Chunk size too large (maximum 50,000 characters)",
            error_code=1103,
            context={'chunk_size': chunk_size, 'maximum': 50000}
        )

    if chunk_overlap < 0:
        raise ConfigurationError(
            "Chunk overlap cannot be negative",
            error_code=1104,
            context={'chunk_overlap': chunk_overlap}
        )

    if chunk_overlap >= chunk_size:
        raise ConfigurationError(
            "Chunk overlap must be smaller than chunk size",
            error_code=1105,
            context={'chunk_size': chunk_size, 'chunk_overlap': chunk_overlap}
        )
```

### 3.2 File System Errors

#### 3.2.1 File Reading Errors (Code: 1201-1210)

```python
def read_file_with_error_handling(file_path: Path) -> str:
    """Read file with comprehensive error handling."""

    context = ErrorContext()
    context.add_file_context(file_path, 'read')

    try:
        # Check file permissions
        if not os.access(file_path, os.R_OK):
            raise FileSystemError(
                f"No read permission for file: {file_path}",
                error_code=1201,
                context=context.get_context()
            )

        # Check file size
        file_size = file_path.stat().st_size
        if file_size > 100 * 1024 * 1024:  # 100MB limit
            raise FileSystemError(
                f"File too large: {file_path} ({file_size} bytes)",
                error_code=1202,
                context=context.get_context()
            )

        # Try multiple encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                return content
            except UnicodeDecodeError as e:
                if encoding == encodings[-1]:  # Last encoding failed
                    raise FileSystemError(
                        f"Cannot decode file with any supported encoding: {file_path}",
                        error_code=1203,
                        context={**context.get_context(), 'encodings_tried': encodings},
                        cause=e
                    )
                continue

    except FileNotFoundError as e:
        raise FileSystemError(
            f"File not found: {file_path}",
            error_code=1204,
            context=context.get_context(),
            cause=e
        )

    except PermissionError as e:
        raise FileSystemError(
            f"Permission denied: {file_path}",
            error_code=1205,
            context=context.get_context(),
            cause=e
        )

    except OSError as e:
        raise FileSystemError(
            f"OS error reading file: {file_path}",
            error_code=1206,
            context={**context.get_context(), 'os_error': str(e)},
            cause=e
        )
```

### 3.3 Processing Errors

#### 3.3.1 Markdown Parsing Errors (Code: 1301-1310)

```python
def parse_markdown_with_error_handling(content: str, file_path: Path) -> MarkdownAST:
    """Parse markdown with error handling."""

    context = ErrorContext()
    context.add_file_context(file_path, 'parse')

    try:
        # Validate content
        if not content.strip():
            raise ProcessingError(
                f"Empty or whitespace-only file: {file_path}",
                error_code=1301,
                context=context.get_context()
            )

        # Check for extremely long lines that might cause issues
        lines = content.split('\n')
        max_line_length = max(len(line) for line in lines)
        if max_line_length > 10000:
            raise ProcessingError(
                f"File contains extremely long lines: {file_path} (max: {max_line_length})",
                error_code=1302,
                context={**context.get_context(), 'max_line_length': max_line_length}
            )

        # Parse markdown
        parser = MarkdownParser()
        ast = parser.parse(content)

        if not ast.elements:
            raise ProcessingError(
                f"No valid markdown elements found: {file_path}",
                error_code=1303,
                context=context.get_context()
            )

        return ast

    except Exception as e:
        if isinstance(e, ProcessingError):
            raise

        raise ProcessingError(
            f"Markdown parsing failed: {file_path}",
            error_code=1304,
            context={**context.get_context(), 'parsing_error': str(e)},
            cause=e
        )
```

#### 3.3.2 Chunking Errors (Code: 1311-1320)

```python
def chunk_document_with_error_handling(ast: MarkdownAST, config: ChunkingConfig,
                                     file_path: Path) -> List[DocumentChunk]:
    """Chunk document with error handling."""

    context = ErrorContext()
    context.add_file_context(file_path, 'chunk')
    context.add_processing_context(0, config.chunk_size, config.method)

    try:
        chunker = ChunkingEngine(config)
        chunks = chunker.chunk_document(ast)

        if not chunks:
            raise ProcessingError(
                f"No chunks generated from document: {file_path}",
                error_code=1311,
                context=context.get_context()
            )

        # Validate chunk sizes
        oversized_chunks = [i for i, chunk in enumerate(chunks)
                           if len(chunk.content) > config.chunk_size * 1.5]

        if oversized_chunks:
            raise ProcessingError(
                f"Generated chunks exceed size limits: {file_path}",
                error_code=1312,
                context={**context.get_context(),
                        'oversized_chunks': oversized_chunks,
                        'max_allowed': config.chunk_size * 1.5}
            )

        context.add_processing_context(len(chunks), config.chunk_size, config.method)
        return chunks

    except Exception as e:
        if isinstance(e, ProcessingError):
            raise

        raise ProcessingError(
            f"Document chunking failed: {file_path}",
            error_code=1313,
            context={**context.get_context(), 'chunking_error': str(e)},
            cause=e
        )
```

### 3.4 ChromaDB Errors

#### 3.4.1 Connection Errors (Code: 1401-1410)

```python
def connect_chromadb_with_error_handling(config: ChromaDBConfig) -> chromadb.Client:
    """Connect to ChromaDB with comprehensive error handling."""

    context = {
        'host': config.host,
        'port': config.port,
        'ssl': config.ssl
    }

    try:
        # Test basic connectivity
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((config.host, config.port))
        sock.close()

        if result != 0:
            raise NetworkError(
                f"Cannot connect to ChromaDB server: {config.host}:{config.port}",
                error_code=1601,
                context=context
            )

        # Create client
        client = chromadb.HttpClient(
            host=config.host,
            port=config.port,
            ssl=config.ssl
        )

        # Test connection
        try:
            client.heartbeat()
        except Exception as e:
            raise ChromaDBError(
                f"ChromaDB heartbeat failed: {config.host}:{config.port}",
                error_code=1401,
                context={**context, 'heartbeat_error': str(e)},
                cause=e
            )

        return client

    except socket.gaierror as e:
        raise NetworkError(
            f"DNS resolution failed for ChromaDB host: {config.host}",
            error_code=1602,
            context={**context, 'dns_error': str(e)},
            cause=e
        )

    except socket.timeout as e:
        raise NetworkError(
            f"Connection timeout to ChromaDB: {config.host}:{config.port}",
            error_code=1603,
            context={**context, 'timeout': config.timeout},
            cause=e
        )

    except Exception as e:
        if isinstance(e, (ChromaDBError, NetworkError)):
            raise

        raise ChromaDBError(
            f"Unexpected error connecting to ChromaDB: {config.host}:{config.port}",
            error_code=1402,
            context={**context, 'unexpected_error': str(e)},
            cause=e
        )
```

#### 3.4.2 Collection Operation Errors (Code: 1411-1420)

```python
def get_or_create_collection_with_error_handling(client: chromadb.Client,
                                               name: str,
                                               create_if_missing: bool) -> chromadb.Collection:
    """Get or create collection with error handling."""

    context = ErrorContext()
    context.add_chromadb_context(name, 'get_or_create_collection')

    try:
        # Validate collection name
        if not name or not name.strip():
            raise ChromaDBError(
                "Collection name cannot be empty",
                error_code=1411,
                context=context.get_context()
            )

        if len(name) > 63:  # ChromaDB collection name limit
            raise ChromaDBError(
                f"Collection name too long: {name} (max 63 characters)",
                error_code=1412,
                context={**context.get_context(), 'name_length': len(name)}
            )

        # Try to get existing collection
        try:
            collection = client.get_collection(name)
            return collection

        except Exception as get_error:
            if not create_if_missing:
                raise ChromaDBError(
                    f"Collection does not exist and create_if_missing=False: {name}",
                    error_code=1413,
                    context=context.get_context(),
                    cause=get_error
                )

            # Create new collection
            try:
                collection = client.create_collection(name)
                return collection

            except Exception as create_error:
                raise ChromaDBError(
                    f"Failed to create collection: {name}",
                    error_code=1414,
                    context={**context.get_context(),
                            'get_error': str(get_error),
                            'create_error': str(create_error)},
                    cause=create_error
                )

    except Exception as e:
        if isinstance(e, ChromaDBError):
            raise

        raise ChromaDBError(
            f"Unexpected error with collection: {name}",
            error_code=1415,
            context={**context.get_context(), 'unexpected_error': str(e)},
            cause=e
        )
```

## 4. Error Recovery Strategies

### 4.1 Retry Mechanisms

```python
class RetryStrategy:
    """Configurable retry strategy for error recovery."""

    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0,
                 max_delay: float = 30.0, backoff_factor: float = 2.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    def should_retry(self, error: ShardMarkdownError, attempt: int) -> bool:
        """Determine if error should be retried."""

        # Never retry input validation errors
        if isinstance(error, InputValidationError):
            return False

        # Retry network and ChromaDB errors
        if isinstance(error, (NetworkError, ChromaDBError)):
            return attempt < self.max_attempts

        # Retry some file system errors
        if isinstance(error, FileSystemError) and error.error_code in [1206]:  # OS errors
            return attempt < self.max_attempts

        return False

    def get_delay(self, attempt: int) -> float:
        """Calculate delay before retry attempt."""

        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)

async def retry_with_strategy(operation: Callable, strategy: RetryStrategy,
                            context: Optional[Dict] = None) -> Any:
    """Execute operation with retry strategy."""

    last_error = None

    for attempt in range(1, strategy.max_attempts + 1):
        try:
            return await operation()

        except ShardMarkdownError as e:
            last_error = e

            if not strategy.should_retry(e, attempt):
                raise

            if attempt < strategy.max_attempts:
                delay = strategy.get_delay(attempt)
                logger.warning(f"Operation failed (attempt {attempt}/{strategy.max_attempts}), "
                              f"retrying in {delay}s: {str(e)}")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Operation failed after {strategy.max_attempts} attempts")
                raise

    # Should not reach here, but raise last error if we do
    if last_error:
        raise last_error
```

### 4.2 Graceful Degradation

```python
class GracefulDegradationHandler:
    """Handle errors with graceful degradation strategies."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.failed_files = []
        self.partial_results = []

    def handle_file_processing_error(self, error: ShardMarkdownError,
                                   file_path: Path) -> bool:
        """Handle errors during file processing."""

        self.failed_files.append({
            'file_path': file_path,
            'error': error,
            'timestamp': datetime.utcnow()
        })

        # Log error but continue processing other files
        logger.error(f"Failed to process {file_path}: {error.message}")

        # For certain errors, we can continue
        if isinstance(error, (ProcessingError, FileSystemError)):
            return True  # Continue processing other files

        # For system-critical errors, we should stop
        if isinstance(error, SystemError):
            return False  # Stop processing

        return True  # Default: continue processing

    def handle_chromadb_error(self, error: ChromaDBError,
                            chunks: List[DocumentChunk]) -> bool:
        """Handle ChromaDB operation errors."""

        # Try to save chunks to local backup
        backup_path = Path(f"backup_chunks_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")

        try:
            import json
            chunk_data = [
                {
                    'id': chunk.id,
                    'content': chunk.content,
                    'metadata': chunk.metadata
                }
                for chunk in chunks
            ]

            with open(backup_path, 'w') as f:
                json.dump(chunk_data, f, indent=2)

            logger.warning(f"ChromaDB operation failed, saved {len(chunks)} chunks to {backup_path}")
            return True

        except Exception as backup_error:
            logger.error(f"Failed to save backup: {backup_error}")
            return False

    def generate_error_report(self) -> Dict[str, Any]:
        """Generate comprehensive error report."""

        return {
            'summary': {
                'total_failed_files': len(self.failed_files),
                'error_categories': self._categorize_errors(),
                'most_common_errors': self._get_common_errors()
            },
            'failed_files': [
                {
                    'file_path': str(item['file_path']),
                    'error_code': item['error'].error_code,
                    'error_message': item['error'].message,
                    'error_category': item['error'].category,
                    'timestamp': item['timestamp'].isoformat()
                }
                for item in self.failed_files
            ],
            'recommendations': self._generate_recommendations()
        }

    def _categorize_errors(self) -> Dict[str, int]:
        """Categorize errors by type."""

        categories = {}
        for item in self.failed_files:
            category = item['error'].category
            categories[category] = categories.get(category, 0) + 1

        return categories

    def _get_common_errors(self) -> List[Dict[str, Any]]:
        """Get most common error codes."""

        error_counts = {}
        for item in self.failed_files:
            code = item['error'].error_code
            if code not in error_counts:
                error_counts[code] = {
                    'count': 0,
                    'message': item['error'].message,
                    'category': item['error'].category
                }
            error_counts[code]['count'] += 1

        # Return top 5 most common errors
        return sorted(error_counts.values(), key=lambda x: x['count'], reverse=True)[:5]

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on error patterns."""

        recommendations = []

        # Analyze error patterns
        categories = self._categorize_errors()

        if categories.get('FILESYSTEM', 0) > 0:
            recommendations.append(
                "Check file permissions and ensure all input files are accessible"
            )

        if categories.get('DATABASE', 0) > 0:
            recommendations.append(
                "Verify ChromaDB connection settings and ensure the server is running"
            )

        if categories.get('PROCESSING', 0) > 0:
            recommendations.append(
                "Consider adjusting chunk size parameters or using a different chunking method"
            )

        if categories.get('CONFIG', 0) > 0:
            recommendations.append(
                "Review configuration file settings and ensure all required values are provided"
            )

        return recommendations
```

## 5. User-Friendly Error Reporting

### 5.1 CLI Error Display

```python
def display_error_to_user(error: ShardMarkdownError, verbose: bool = False):
    """Display user-friendly error message."""

    console = Console()

    # Error header
    console.print(f"\n[bold red]Error {error.error_code}:[/bold red] {error.message}")

    # Context information
    if error.context:
        console.print("\n[yellow]Context:[/yellow]")
        for key, value in error.context.items():
            if isinstance(value, (str, int, float, bool)):
                console.print(f"  {key}: {value}")

    # Suggestions based on error type
    suggestions = get_error_suggestions(error)
    if suggestions:
        console.print("\n[blue]Suggestions:[/blue]")
        for suggestion in suggestions:
            console.print(f"  • {suggestion}")

    # Verbose information
    if verbose:
        console.print(f"\n[dim]Category:[/dim] {error.category}")
        console.print(f"[dim]Timestamp:[/dim] {error.timestamp}")

        if error.cause:
            console.print(f"[dim]Underlying cause:[/dim] {error.cause}")

def get_error_suggestions(error: ShardMarkdownError) -> List[str]:
    """Get user-friendly suggestions for error resolution."""

    suggestions = []

    if isinstance(error, InputValidationError):
        if error.error_code == 1001:  # File not found
            suggestions.append("Check that the file path is correct and the file exists")
            suggestions.append("Use absolute paths or ensure you're in the correct directory")
        elif error.error_code == 1002:  # Not markdown file
            suggestions.append("Ensure the file has a .md extension")
            suggestions.append("Verify the file contains markdown content")

    elif isinstance(error, ConfigurationError):
        suggestions.append("Review your configuration file settings")
        suggestions.append("Run 'shard-md config show' to see current configuration")
        suggestions.append("Use 'shard-md config init' to create a new configuration")

    elif isinstance(error, FileSystemError):
        if error.error_code == 1201:  # Permission denied
            suggestions.append("Check file permissions (chmod +r filename)")
            suggestions.append("Ensure you have read access to the file and directory")
        elif error.error_code == 1203:  # Encoding error
            suggestions.append("The file may contain non-UTF-8 characters")
            suggestions.append("Try saving the file with UTF-8 encoding")

    elif isinstance(error, ChromaDBError):
        suggestions.append("Verify ChromaDB server is running and accessible")
        suggestions.append("Check connection settings (host, port, SSL)")
        suggestions.append("Ensure you have proper authentication credentials")

    elif isinstance(error, NetworkError):
        suggestions.append("Check your network connection")
        suggestions.append("Verify the ChromaDB server address and port")
        suggestions.append("Check firewall settings")

    return suggestions
```

### 5.2 Progress and Status Reporting

```python
class ProgressReporter:
    """Report progress and handle errors during long operations."""

    def __init__(self, total_items: int, description: str = "Processing"):
        self.total_items = total_items
        self.processed = 0
        self.failed = 0
        self.errors = []

        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        )

        self.task_id = self.progress.add_task(description, total=total_items)

    def __enter__(self):
        self.progress.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress.stop()
        self._display_summary()

    def report_success(self, item_name: str):
        """Report successful processing of an item."""
        self.processed += 1
        self.progress.update(self.task_id, advance=1,
                           description=f"Processing: {item_name}")

    def report_error(self, item_name: str, error: ShardMarkdownError):
        """Report error processing an item."""
        self.failed += 1
        self.errors.append({'item': item_name, 'error': error})
        self.progress.update(self.task_id, advance=1,
                           description=f"Failed: {item_name}")

    def _display_summary(self):
        """Display processing summary."""
        console = Console()

        # Success summary
        if self.processed > 0:
            console.print(f"\n[green]✓ Successfully processed: {self.processed} items[/green]")

        # Error summary
        if self.failed > 0:
            console.print(f"[red]✗ Failed: {self.failed} items[/red]")

            # Show first few errors
            for error_info in self.errors[:3]:
                console.print(f"  • {error_info['item']}: {error_info['error'].message}")

            if len(self.errors) > 3:
                console.print(f"  ... and {len(self.errors) - 3} more errors")
                console.print("  Use --verbose for full error details")
```

This comprehensive error handling specification provides robust error management, clear user feedback, and appropriate recovery strategies for the shard-markdown CLI tool.
