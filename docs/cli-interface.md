# CLI Interface Specification

## 1. Command Structure Overview

Shard Markdown follows the Unix philosophy of "do one thing well". The CLI operates as a simple, direct-action tool without subcommands:

```
shard-md [OPTIONS] INPUT
```

Where INPUT is a markdown file, directory, or glob pattern.

## 2. Core Philosophy

- **No subcommands**: Direct action on input files
- **Smart defaults**: Works out of the box with `shard-md document.md`
- **Progressive disclosure**: Advanced features available via options
- **Unix-style**: Composable with pipes and other tools

## 3. Command-Line Options

### 3.1 Chunking Options

Control how documents are split into chunks:

```bash
-s, --size INTEGER         Chunk size in tokens/characters [default: 1000]
-o, --overlap INTEGER      Overlap between chunks [default: 200]
--strategy [STRATEGY]      Chunking strategy [default: structure]
                          Options: token, sentence, paragraph, 
                                  section, semantic, structure, fixed
```

### 3.2 Storage Options

Control where and how chunks are stored:

```bash
--store                   Store chunks in vector database
--collection TEXT         Collection name for vectordb storage
```

### 3.3 Processing Options

Control how files are processed:

```bash
-r, --recursive           Process directories recursively
-m, --metadata           Include metadata in chunks
--preserve-structure      Maintain markdown structure
```

### 3.4 Utility Options

Control output and behavior:

```bash
--dry-run                Preview chunks without storing
--config-path PATH       Use alternate configuration file
-q, --quiet              Suppress output (useful when storing)
-v, --verbose            Verbose output for debugging
--version               Show version and exit
--help                  Show help message and exit
```

## 4. Usage Examples

### 4.1 Basic Usage

```bash
# Display chunks from a single file
shard-md README.md

# Display chunks with custom size
shard-md document.md --size 500 --overlap 50
```

### 4.2 Storage Operations

```bash
# Store chunks in ChromaDB
shard-md manual.md --store --collection documentation

# Process and store multiple files quietly
shard-md *.md --store --collection my-docs --quiet
```

### 4.3 Directory Processing

```bash
# Process directory non-recursively
shard-md docs/

# Process directory recursively
shard-md docs/ --recursive --store --collection tech-docs
```

### 4.4 Advanced Usage

```bash
# Dry run with verbose output
shard-md large-doc.md --dry-run --verbose

# Use custom configuration
shard-md book.md --config-path ./project-config.yaml

# Semantic chunking with metadata
shard-md research.md --strategy semantic --metadata --store
```

## 5. Configuration

### 5.1 Configuration Files

Configuration uses simple YAML files, loaded in order of precedence:

1. `~/.shard-md/config.yaml` (global configuration)
2. `./.shard-md/config.yaml` (project-local configuration)
3. `./shard-md.yaml` (project root configuration)
4. File specified with `--config-path`

### 5.2 Configuration Format

```yaml
# ~/.shard-md/config.yaml
chunk:
  size: 1000
  overlap: 200
  strategy: structure
  
storage:
  vectordb:
    host: localhost
    port: 8000
    collection: default

processing:
  recursive: false
  metadata: true
  preserve_structure: true

logging:
  level: INFO
  quiet: false
```

### 5.3 Environment Variables

Override configuration with environment variables:

```bash
export SHARD_MD_CHUNK_SIZE=1500
export SHARD_MD_CHUNK_OVERLAP=300
export SHARD_MD_CHUNK_STRATEGY=semantic
export CHROMA_HOST=localhost
export CHROMA_PORT=8000
export SHARD_MD_LOG_LEVEL=DEBUG
```

## 6. Output Formats

### 6.1 Default Output (Display Mode)

When no `--store` flag is provided, chunks are displayed to stdout:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Chunk 1/5 (Size: 987 tokens)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Introduction

This is the beginning of the document...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 6.2 Quiet Mode

With `--quiet`, only essential information is shown:

```bash
shard-md docs/ --store --collection my-docs --quiet
✓ Processed 15 files, created 127 chunks
```

### 6.3 Verbose Mode

With `--verbose`, detailed processing information is shown:

```bash
shard-md document.md --verbose
[INFO] Loading configuration from ~/.shard-md/config.yaml
[INFO] Processing: document.md (15.2 KB)
[INFO] Using strategy: structure
[INFO] Chunk size: 1000, Overlap: 200
[DEBUG] Parsing markdown structure...
[DEBUG] Found 5 headers, 3 code blocks, 2 lists
[INFO] Created 7 chunks
```

## 7. Exit Codes

- `0`: Success
- `1`: General error
- `2`: Configuration error
- `3`: Connection error (ChromaDB)
- `4`: File not found
- `5`: Permission denied

## 8. Chunking Strategies

### 8.1 Strategy Descriptions

- **structure**: (Default) Respects markdown structure, never splits code blocks
- **token**: Token-based chunking optimized for LLMs
- **sentence**: Splits on sentence boundaries
- **paragraph**: Preserves paragraph integrity
- **section**: Splits on markdown headers
- **semantic**: Context-aware splitting based on meaning
- **fixed**: Simple character-based splitting with overlap

### 8.2 Strategy Selection

```bash
# Use semantic chunking
shard-md document.md --strategy semantic

# Use token-based chunking for LLM compatibility
shard-md document.md --strategy token --size 4096
```

## 9. Future Extensions

The CLI is designed for future extensibility while maintaining simplicity:

- Additional storage backends (json, yaml, directory)
- Pipeline integration via stdout
- Custom chunking strategies via plugins
- Batch processing optimizations

## 10. Migration from v1.x

Users migrating from v1.x should note these changes:

- **Removed**: All subcommands (`process`, `collections`, `query`, `config`)
- **Removed**: Collection management features
- **Removed**: Query and search features
- **Simplified**: Direct file processing is now the default action
- **Configuration**: Edit YAML files directly (no `config` commands)

Example migration:
```bash
# Old (v1.x)
shard-md process --collection my-docs document.md
shard-md collections list
shard-md query search "topic" --collection my-docs

# New (v2.0+)
shard-md document.md --store --collection my-docs
# Collection management: Use ChromaDB tools directly
# Search: Use ChromaDB tools or other search utilities
```