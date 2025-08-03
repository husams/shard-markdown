# CLI Interface Specification

## 1. Command Structure Overview

The Shard Markdown CLI follows a hierarchical command structure with the main command `shard-md` and several subcommands for different operations.

```
shard-md [GLOBAL-OPTIONS] COMMAND [COMMAND-OPTIONS] [ARGUMENTS]
```

## 2. Global Options

### 2.1 Common Global Options
```bash
--config, -c PATH          Configuration file path [default: ~/.shard-md/config.yaml]
--verbose, -v              Increase verbosity (can be repeated: -v, -vv, -vvv)
--quiet, -q               Suppress non-error output
--log-file PATH           Write logs to specified file
--help, -h                Show help message and exit
--version                 Show version information and exit
```

### 2.2 ChromaDB Connection Options
```bash
--chroma-host HOST        ChromaDB host [default: localhost]
--chroma-port PORT        ChromaDB port [default: 8000]
--chroma-ssl              Use SSL for ChromaDB connection
--chroma-auth-token TOKEN Authentication token for ChromaDB
--chroma-timeout SECONDS  Connection timeout [default: 30]
```

## 3. Primary Commands

### 3.1 Process Command
Primary command for processing markdown files into ChromaDB collections.

```bash
shard-md process [OPTIONS] INPUT [INPUT...]
```

#### Arguments
- `INPUT`: Path to markdown file(s) or directory(ies) to process

#### Options
```bash
# Collection Management
--collection, -c NAME     Target ChromaDB collection name [required]
--create-collection       Create collection if it doesn't exist
--clear-collection        Clear existing collection before processing
--collection-metadata JSON  Additional metadata for new collections

# Chunking Options
--chunk-size, -s SIZE     Maximum chunk size in characters [default: 1000]
--chunk-overlap, -o SIZE  Overlap between chunks in characters [default: 200]
--chunk-method METHOD     Chunking method: structure|fixed|semantic [default: structure]
--max-tokens TOKEN_COUNT  Maximum tokens per chunk (alternative to char count)
--respect-boundaries      Respect markdown structure boundaries [default: true]

# Processing Options
--recursive, -r           Process directories recursively
--pattern GLOB            File pattern for filtering [default: "*.md"]
--exclude-pattern GLOB    Exclude files matching pattern
--batch-size SIZE         Number of documents to process in batch [default: 10]
--max-workers COUNT       Maximum worker threads [default: 4]

# Metadata Options
--include-frontmatter     Extract YAML frontmatter as metadata [default: true]
--include-path-metadata   Include file path information in metadata [default: true]
--custom-metadata JSON    Additional custom metadata for all chunks
--metadata-prefix PREFIX  Prefix for custom metadata keys

# Output Options
--dry-run                 Show what would be processed without executing
--progress                Show progress bar [default: true]
--summary                 Show processing summary
```

#### Examples
```bash
# Basic processing
shard-md process --collection my-docs document.md

# Batch process with custom settings
shard-md process \
  --collection technical-docs \
  --chunk-size 1500 \
  --chunk-overlap 300 \
  --recursive \
  --pattern "*.md" \
  docs/

# Create new collection with metadata
shard-md process \
  --collection new-collection \
  --create-collection \
  --collection-metadata '{"description": "Technical documentation", "version": "1.0"}' \
  --custom-metadata '{"source": "internal", "team": "engineering"}' \
  *.md
```

### 3.2 Collection Management Commands

#### 3.2.1 List Collections
```bash
shard-md collections list [OPTIONS]
```

Options:
```bash
--format FORMAT          Output format: table|json|yaml [default: table]
--show-metadata          Include collection metadata in output
--filter PATTERN         Filter collections by name pattern
```

#### 3.2.2 Create Collection
```bash
shard-md collections create [OPTIONS] NAME
```

Options:
```bash
--metadata JSON          Collection metadata as JSON
--embedding-function     Embedding function to use [default: default]
--description TEXT       Collection description
```

#### 3.2.3 Delete Collection
```bash
shard-md collections delete [OPTIONS] NAME
```

Options:
```bash
--force, -f              Force deletion without confirmation
--backup                 Create backup before deletion
```

#### 3.2.4 Collection Info
```bash
shard-md collections info [OPTIONS] NAME
```

Options:
```bash
--format FORMAT          Output format: table|json|yaml [default: table]
--show-documents         Include document count and sample documents
--show-metadata          Include detailed metadata
```

### 3.3 Query Commands

#### 3.3.1 Search Documents
```bash
shard-md query search [OPTIONS] QUERY
```

Options:
```bash
--collection, -c NAME     Collection to search [required]
--limit, -n COUNT         Maximum results to return [default: 10]
--similarity-threshold    Minimum similarity score [default: 0.0]
--include-metadata        Include metadata in results [default: true]
--format FORMAT           Output format: table|json|yaml [default: table]
```

#### 3.3.2 Get Document
```bash
shard-md query get [OPTIONS] DOCUMENT_ID
```

Options:
```bash
--collection, -c NAME     Collection name [required]
--format FORMAT           Output format: table|json|yaml [default: table]
--include-metadata        Include metadata in results [default: true]
```

### 3.4 Configuration Commands

#### 3.4.1 Show Configuration
```bash
shard-md config show [OPTIONS]
```

Options:
```bash
--format FORMAT          Output format: yaml|json [default: yaml]
--section SECTION        Show specific configuration section
```

#### 3.4.2 Set Configuration
```bash
shard-md config set [OPTIONS] KEY VALUE
```

Options:
```bash
--global                 Set global configuration (user-level)
--local                  Set local configuration (project-level)
```

#### 3.4.3 Initialize Configuration
```bash
shard-md config init [OPTIONS]
```

Options:
```bash
--global                 Initialize global configuration
--force                  Overwrite existing configuration
--template TEMPLATE      Use configuration template
```

### 3.5 Utility Commands

#### 3.5.1 Validate Documents
```bash
shard-md validate [OPTIONS] INPUT [INPUT...]
```

Options:
```bash
--recursive, -r          Validate directories recursively
--pattern GLOB           File pattern for filtering [default: "*.md"]
--check-frontmatter      Validate YAML frontmatter
--check-links            Validate internal links
--format FORMAT          Output format: table|json [default: table]
```

#### 3.5.2 Preview Chunking
```bash
shard-md preview [OPTIONS] INPUT
```

Options:
```bash
--chunk-size, -s SIZE    Maximum chunk size [default: 1000]
--chunk-overlap, -o SIZE Overlap between chunks [default: 200]
--chunk-method METHOD    Chunking method [default: structure]
--show-metadata          Include metadata in preview
--output-file PATH       Save preview to file
```

## 4. Exit Codes

The CLI uses standard exit codes to indicate operation status:

- `0`: Success
- `1`: General error
- `2`: Invalid arguments or configuration
- `3`: File I/O error
- `4`: ChromaDB connection error
- `5`: Processing error (partial failure)
- `130`: Interrupted by user (Ctrl+C)

## 5. Environment Variables

### 5.1 Configuration Override
```bash
SHARD_MD_CONFIG_FILE        Override default config file location
SHARD_MD_LOG_LEVEL          Set logging level (DEBUG|INFO|WARNING|ERROR)
SHARD_MD_LOG_FILE           Set log file location
```

### 5.2 ChromaDB Connection
```bash
CHROMA_HOST                 ChromaDB host
CHROMA_PORT                 ChromaDB port
CHROMA_AUTH_TOKEN           Authentication token
CHROMA_SSL                  Use SSL (true|false)
```

### 5.3 Processing Defaults
```bash
SHARD_MD_CHUNK_SIZE         Default chunk size
SHARD_MD_CHUNK_OVERLAP      Default chunk overlap
SHARD_MD_BATCH_SIZE         Default batch size
SHARD_MD_MAX_WORKERS        Default worker count
```

## 6. Configuration File Format

### 6.1 YAML Configuration Example
```yaml
# ~/.shard-md/config.yaml
chromadb:
  host: localhost
  port: 8000
  ssl: false
  timeout: 30
  auth_token: null

chunking:
  default_size: 1000
  default_overlap: 200
  method: structure
  respect_boundaries: true
  max_tokens: null

processing:
  batch_size: 10
  max_workers: 4
  recursive: false
  pattern: "*.md"
  include_frontmatter: true
  include_path_metadata: true

output:
  progress: true
  verbose: false
  log_file: null
  format: table

collections:
  default_embedding_function: default
  auto_create: false
  default_metadata: {}
```

## 7. Help System

### 7.1 Built-in Help
```bash
# General help
shard-md --help
shard-md -h

# Command-specific help
shard-md process --help
shard-md collections --help

# Subcommand help
shard-md collections list --help
```

### 7.2 Man Page Support
```bash
man shard-md                # Main manual page
man shard-md-process        # Process command manual
man shard-md-collections    # Collections manual
```

## 8. Shell Completion

### 8.1 Bash Completion
```bash
# Add to ~/.bashrc
eval "$(_SHARD_MD_COMPLETE=bash_source shard-md)"
```

### 8.2 Zsh Completion
```bash
# Add to ~/.zshrc
eval "$(_SHARD_MD_COMPLETE=zsh_source shard-md)"
```

### 8.3 Fish Completion
```bash
# Add to ~/.config/fish/completions/shard-md.fish
eval (env _SHARD_MD_COMPLETE=fish_source shard-md)
```

## 9. Error Handling and User Feedback

### 9.1 Error Message Format
```
Error: [ERROR_CODE] Brief description
Details: Detailed explanation of the error
Suggestion: Recommended action to resolve the issue
```

### 9.2 Progress Indicators
- Spinner for quick operations
- Progress bar for long-running operations
- Batch processing progress with ETA
- Real-time operation status updates

### 9.3 Confirmation Prompts
```bash
# Destructive operations require confirmation
shard-md collections delete my-collection
> This will permanently delete collection 'my-collection' and all its documents.
> Are you sure? [y/N]:
```
