# Shard Markdown Architecture Documentation

## Table of Contents

1. [Overview](#overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Sequence Diagrams](#sequence-diagrams)
6. [Module Dependencies](#module-dependencies)
7. [Key Design Patterns](#key-design-patterns)
8. [Performance Considerations](#performance-considerations)
9. [Security Architecture](#security-architecture)

## Overview

Shard Markdown is an intelligent document processing system that chunks markdown documents and stores them in ChromaDB collections for efficient retrieval and search. The architecture follows a layered approach with clear separation of concerns across CLI interface, core processing logic, ChromaDB integration, and configuration management.

## High-Level Architecture

```mermaid
graph TB
    subgraph "User Interface Layer"
        CLI[CLI Interface]
        Commands[Command Modules]
    end

    subgraph "Core Processing Layer"
        Parser[Markdown Parser]
        Chunker[Chunking Engine]
        Processor[Document Processor]
        Metadata[Metadata Extractor]
    end

    subgraph "Storage Layer"
        ChromaClient[ChromaDB Client]
        Collections[Collection Manager]
        Operations[Storage Operations]
    end

    subgraph "Infrastructure Layer"
        Config[Configuration]
        Logging[Logging System]
        Errors[Error Handling]
        Validation[Data Validation]
    end

    subgraph "External Systems"
        ChromaDB[(ChromaDB)]
        FileSystem[(File System)]
    end

    CLI --> Commands
    Commands --> Processor
    Commands --> Config
    
    Processor --> Parser
    Processor --> Chunker
    Processor --> Metadata
    Processor --> ChromaClient
    
    ChromaClient --> Collections
    Collections --> Operations
    Operations --> ChromaDB
    
    Parser --> FileSystem
    Config --> FileSystem
    
    Processor --> Logging
    Processor --> Errors
    ChromaClient --> Validation

    style CLI fill:#e1f5fe
    style Processor fill:#f3e5f5
    style ChromaClient fill:#e8f5e8
    style Config fill:#fff3e0
```

## Component Architecture

### CLI Layer Components

```mermaid
graph LR
    subgraph "CLI Module"
        Main[main.py]
        
        subgraph "Commands"
            Process[process.py]
            Collections[collections.py]
            Query[query.py]
            Config[config.py]
        end
        
        Main --> Process
        Main --> Collections
        Main --> Query
        Main --> Config
    end

    subgraph "Dependencies"
        Click[Click Framework]
        Rich[Rich Console]
    end

    Main --> Click
    Main --> Rich
    
    style Main fill:#e1f5fe
    style Process fill:#e8f5e8
    style Collections fill:#f3e5f5
    style Query fill:#fff3e0
    style Config fill:#fce4ec
```

### Core Processing Components

```mermaid
graph TB
    subgraph "Core Processing"
        Processor[DocumentProcessor]
        Parser[MarkdownParser]
        
        subgraph "Chunking System"
            ChunkEngine[ChunkingEngine]
            BaseChunker[BaseChunker]
            FixedChunker[FixedChunker]
            StructureChunker[StructureChunker]
        end
        
        Metadata[MetadataExtractor]
        Models[Data Models]
    end

    Processor --> Parser
    Processor --> ChunkEngine
    Processor --> Metadata
    
    ChunkEngine --> BaseChunker
    BaseChunker <|-- FixedChunker
    BaseChunker <|-- StructureChunker
    
    Parser --> Models
    ChunkEngine --> Models
    Metadata --> Models

    style Processor fill:#e3f2fd
    style ChunkEngine fill:#f1f8e9
    style Models fill:#fce4ec
```

### ChromaDB Integration Components

```mermaid
graph LR
    subgraph "ChromaDB Layer"
        Client[ChromaDBClient]
        Factory[ClientFactory]
        Collections[CollectionManager]
        Operations[StorageOperations]
        Protocol[ProtocolInterface]
        MockClient[MockClient]
    end

    subgraph "External"
        ChromaDB[(ChromaDB Server)]
    end

    Factory --> Client
    Factory --> MockClient
    Client --> Collections
    Client --> Operations
    Client --> Protocol
    Client --> ChromaDB
    MockClient -.-> Protocol

    style Client fill:#e8f5e8
    style Factory fill:#f3e5f5
    style MockClient fill:#fff3e0
```

## Data Flow

### Document Processing Flow

```mermaid
flowchart TD
    A[Markdown File] --> B[File Reader]
    B --> C[Content Validation]
    C --> D[Markdown Parser]
    D --> E[AST Generation]
    E --> F[Metadata Extraction]
    F --> G[Chunking Engine]
    G --> H[Chunk Enhancement]
    H --> I[ChromaDB Storage]
    I --> J[Processing Result]

    subgraph "Error Handling"
        K[Error Capture]
        L[Error Logging]
        M[Error Response]
    end

    C -.-> K
    D -.-> K
    G -.-> K
    I -.-> K
    K --> L
    L --> M

    style A fill:#e1f5fe
    style E fill:#f3e5f5
    style I fill:#e8f5e8
    style J fill:#fff3e0
    style K fill:#ffebee
```

### Batch Processing Flow

```mermaid
flowchart TD
    A[File List] --> B[Thread Pool Executor]
    B --> C[Concurrent Processing]
    
    subgraph "Worker Threads"
        D[Worker 1]
        E[Worker 2]
        F[Worker N]
    end
    
    C --> D
    C --> E
    C --> F
    
    D --> G[Individual Results]
    E --> G
    F --> G
    
    G --> H[Result Aggregation]
    H --> I[Batch Statistics]
    I --> J[Final Result]

    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style H fill:#e8f5e8
    style J fill:#fff3e0
```

## Sequence Diagrams

### Single Document Processing

```mermaid
sequenceDiagram
    participant CLI
    participant Processor
    participant Parser
    participant Chunker
    participant ChromaClient
    participant ChromaDB

    CLI->>Processor: process_document(file_path)
    Processor->>Processor: _read_file(file_path)
    Processor->>Parser: parse(content)
    Parser->>Parser: create AST
    Parser-->>Processor: MarkdownAST
    
    Processor->>Processor: extract_metadata(ast)
    Processor->>Chunker: chunk_document(ast)
    Chunker->>Chunker: apply chunking strategy
    Chunker-->>Processor: DocumentChunk[]
    
    Processor->>Processor: _enhance_chunks()
    Processor->>ChromaClient: bulk_insert(chunks)
    ChromaClient->>ChromaDB: add(ids, documents, metadatas)
    ChromaDB-->>ChromaClient: success
    ChromaClient-->>Processor: InsertResult
    Processor-->>CLI: ProcessingResult
```

### Collection Management

```mermaid
sequenceDiagram
    participant CLI
    participant CollectionCmd
    participant ChromaClient
    participant ChromaDB

    CLI->>CollectionCmd: collections list
    CollectionCmd->>ChromaClient: connect()
    ChromaClient->>ChromaDB: heartbeat()
    ChromaDB-->>ChromaClient: ok
    
    ChromaClient->>ChromaDB: list_collections()
    ChromaDB-->>ChromaClient: Collection[]
    
    loop For each collection
        ChromaClient->>ChromaDB: collection.count()
        ChromaDB-->>ChromaClient: count
    end
    
    ChromaClient-->>CollectionCmd: collection_info[]
    CollectionCmd-->>CLI: formatted output
```

### Error Handling Flow

```mermaid
sequenceDiagram
    participant Component
    participant ErrorHandler
    participant Logger
    participant User

    Component->>Component: operation()
    Component->>Component: exception occurs
    Component->>ErrorHandler: raise CustomError
    ErrorHandler->>Logger: log error details
    ErrorHandler->>ErrorHandler: format error message
    ErrorHandler-->>User: user-friendly error
    
    Note over Component,User: Error context preserved
    Note over Logger: Structured logging with context
```

## Module Dependencies

### Dependency Graph

```mermaid
graph TD
    subgraph "Application Layer"
        CLI[cli/main.py]
        Commands[cli/commands/*]
    end

    subgraph "Core Layer"
        Processor[core/processor.py]
        Parser[core/parser.py]
        Models[core/models.py]
        Chunking[core/chunking/*]
        Metadata[core/metadata.py]
    end

    subgraph "Integration Layer"
        ChromaClient[chromadb/client.py]
        Collections[chromadb/collections.py]
        Operations[chromadb/operations.py]
    end

    subgraph "Infrastructure Layer"
        Config[config/*]
        Utils[utils/*]
        Logging[utils/logging.py]
        Errors[utils/errors.py]
    end

    CLI --> Commands
    Commands --> Processor
    Commands --> ChromaClient
    Commands --> Config
    
    Processor --> Parser
    Processor --> Chunking
    Processor --> Metadata
    Processor --> Models
    
    ChromaClient --> Collections
    ChromaClient --> Operations
    ChromaClient --> Models
    
    All --> Utils
    All --> Logging
    All --> Errors

    style CLI fill:#e1f5fe
    style Processor fill:#f3e5f5
    style ChromaClient fill:#e8f5e8
    style Config fill:#fff3e0
```

## Key Design Patterns

### 1. Strategy Pattern (Chunking)

```mermaid
classDiagram
    class BaseChunker {
        <<abstract>>
        +chunk_document(ast: MarkdownAST) List[DocumentChunk]
        +validate_config(config: ChunkingConfig) bool
    }
    
    class FixedChunker {
        +chunk_document(ast: MarkdownAST) List[DocumentChunk]
        -_split_by_size(content: str) List[str]
    }
    
    class StructureChunker {
        +chunk_document(ast: MarkdownAST) List[DocumentChunk]
        -_chunk_by_headers(elements: List[Element]) List[DocumentChunk]
    }
    
    class ChunkingEngine {
        -strategy: BaseChunker
        +chunk_document(ast: MarkdownAST) List[DocumentChunk]
        +set_strategy(chunker: BaseChunker) void
    }

    BaseChunker <|-- FixedChunker
    BaseChunker <|-- StructureChunker
    ChunkingEngine --> BaseChunker
```

### 2. Factory Pattern (ChromaDB Client)

```mermaid
classDiagram
    class ClientFactory {
        +create_client(config: ChromaDBConfig) ChromaDBClientProtocol
        +create_mock_client() MockChromaDBClient
        -_validate_config(config: ChromaDBConfig) bool
    }
    
    class ChromaDBClientProtocol {
        <<interface>>
        +connect() bool
        +get_collection(name: str) Collection
        +bulk_insert(collection: Collection, chunks: List[DocumentChunk]) InsertResult
    }
    
    class ChromaDBClient {
        +connect() bool
        +get_collection(name: str) Collection
        +bulk_insert(collection: Collection, chunks: List[DocumentChunk]) InsertResult
    }
    
    class MockChromaDBClient {
        +connect() bool
        +get_collection(name: str) Collection
        +bulk_insert(collection: Collection, chunks: List[DocumentChunk]) InsertResult
    }

    ClientFactory --> ChromaDBClientProtocol
    ChromaDBClientProtocol <|-- ChromaDBClient
    ChromaDBClientProtocol <|-- MockChromaDBClient
```

### 3. Command Pattern (CLI Commands)

```mermaid
classDiagram
    class Command {
        <<abstract>>
        +execute(ctx: Context) Result
        +validate_args(args: Dict) bool
    }
    
    class ProcessCommand {
        +execute(ctx: Context) ProcessingResult
        -_process_files(files: List[Path]) BatchResult
    }
    
    class QueryCommand {
        +execute(ctx: Context) QueryResult
        -_search_collection(query: str) List[Result]
    }
    
    class CollectionsCommand {
        +execute(ctx: Context) CollectionResult
        -_list_collections() List[CollectionInfo]
    }

    Command <|-- ProcessCommand
    Command <|-- QueryCommand
    Command <|-- CollectionsCommand
```

## Performance Considerations

### Concurrency Architecture

```mermaid
graph TD
    subgraph "Main Thread"
        A[CLI Interface]
        B[Batch Coordinator]
    end

    subgraph "Worker Thread Pool"
        C[Worker 1]
        D[Worker 2]
        E[Worker 3]
        F[Worker N]
    end

    subgraph "I/O Operations"
        G[File Reading]
        H[ChromaDB Writes]
        I[Network Calls]
    end

    A --> B
    B --> C
    B --> D
    B --> E
    B --> F

    C --> G
    D --> G
    E --> G
    F --> G

    C --> H
    D --> H
    E --> H
    F --> H

    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e8
    style G fill:#fff3e0
    style H fill:#ffebee
```

### Memory Management

```mermaid
flowchart TD
    A[Large File Detection] --> B{File Size > 100MB?}
    B -->|Yes| C[Reject Processing]
    B -->|No| D[Stream Processing]
    
    D --> E[Chunk-by-Chunk Reading]
    E --> F[Process in Memory]
    F --> G[Immediate Storage]
    G --> H[Memory Cleanup]
    
    H --> I{More Chunks?}
    I -->|Yes| E
    I -->|No| J[Complete Processing]

    style A fill:#e1f5fe
    style C fill:#ffebee
    style F fill:#e8f5e8
    style J fill:#f3e5f5
```

## Security Architecture

### Input Validation Flow

```mermaid
flowchart TD
    A[User Input] --> B[Path Validation]
    B --> C{Valid Path?}
    C -->|No| D[Reject with Error]
    C -->|Yes| E[File Size Check]
    
    E --> F{Size OK?}
    F -->|No| G[File Too Large Error]
    F -->|Yes| H[Encoding Validation]
    
    H --> I{Valid Encoding?}
    I -->|No| J[Encoding Error]
    I -->|Yes| K[Content Validation]
    
    K --> L{Safe Content?}
    L -->|No| M[Content Security Error]
    L -->|Yes| N[Proceed with Processing]

    style A fill:#e1f5fe
    style D fill:#ffebee
    style G fill:#ffebee
    style J fill:#ffebee
    style M fill:#ffebee
    style N fill:#e8f5e8
```

### Error Boundary Architecture

```mermaid
graph TD
    subgraph "Error Boundaries"
        A[CLI Boundary]
        B[Processing Boundary]
        C[Storage Boundary]
        D[Network Boundary]
    end

    subgraph "Error Types"
        E[ValidationError]
        F[ProcessingError]
        G[ChromaDBError]
        H[NetworkError]
        I[FileSystemError]
    end

    subgraph "Error Handling"
        J[Error Logger]
        K[Error Formatter]
        L[User Notification]
    end

    A --> E
    B --> F
    C --> G
    D --> H
    D --> I

    E --> J
    F --> J
    G --> J
    H --> J
    I --> J

    J --> K
    K --> L

    style A fill:#e1f5fe
    style E fill:#ffebee
    style J fill:#fff3e0
```

This architecture documentation provides a comprehensive view of the Shard Markdown system's design, showing how components interact, data flows through the system, and key architectural patterns are implemented. The modular design ensures maintainability, testability, and extensibility while providing robust error handling and performance optimization.