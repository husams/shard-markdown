# Usage Examples

## 1. Basic Usage Scenarios

### 1.1 Single File Processing

#### 1.1.1 Process Single Markdown File

```bash
# Basic processing of a single file
shard-md process --collection my-docs document.md

# Process with custom chunk size
shard-md process --collection my-docs --chunk-size 1500 document.md

# Process and create collection if it doesn't exist
shard-md process --collection new-docs --create-collection document.md
```

**Expected Output:**

```
Processing documents... ████████████████████████████████████████ 100% (1/1)

✓ Successfully processed: 1 items
Collection: my-docs
Total chunks created: 8
Processing time: 0.45s
```

#### 1.1.2 Preview Before Processing

```bash
# Preview what chunks would be created
shard-md preview --chunk-size 1000 --chunk-overlap 200 document.md

# Preview with different chunking method
shard-md preview --chunk-method fixed --chunk-size 800 document.md
```

**Expected Output:**

```
Preview for: document.md
Chunking method: structure
Chunk size: 1000 characters
Overlap: 200 characters

Chunk 1 (987 chars):
# Introduction
This document provides an overview of...

Chunk 2 (1045 chars):
## Getting Started
To begin using this tool, first ensure...

Total chunks: 8
Average chunk size: 945 characters
```

### 1.2 Directory Processing

#### 1.2.1 Process Directory Recursively

```bash
# Process all markdown files in a directory
shard-md process --collection docs --recursive --create-collection docs/

# Process with pattern filtering
shard-md process --collection api-docs --recursive --pattern "api-*.md" docs/

# Process excluding certain patterns
shard-md process --collection clean-docs --recursive \
  --exclude-pattern "*-draft.md" docs/
```

#### 1.2.2 Batch Processing with Custom Settings

```bash
# Process large directory with optimized settings
shard-md process \
  --collection large-corpus \
  --recursive \
  --chunk-size 1200 \
  --chunk-overlap 150 \
  --batch-size 20 \
  --max-workers 8 \
  --create-collection \
  docs/
```

**Expected Output:**

```
Processing documents... ████████████████████████████████████████ 100% (247/247)

✓ Successfully processed: 245 items
✗ Failed: 2 items
  • docs/broken.md: File encoding not supported
  • docs/empty.md: Empty or whitespace-only file

Collection: large-corpus
Total chunks created: 1,847
Processing time: 12.3s
Average chunks per document: 7.5
```

## 2. Advanced Configuration Examples

### 2.1 Configuration File Usage

#### 2.1.1 Create Configuration File

```bash
# Initialize default configuration
shard-md config init

# Initialize with custom template
shard-md config init --template advanced

# Show current configuration
shard-md config show
```

**Generated Configuration (~/.shard-md/config.yaml):**

```yaml
chromadb:
  host: localhost
  port: 8000
  ssl: false
  timeout: 30

chunking:
  default_size: 1000
  default_overlap: 200
  method: structure
  respect_boundaries: true

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
  format: table

collections:
  auto_create: false
  default_metadata:
    project: "documentation"
    version: "1.0"
```

#### 2.1.2 Use Custom Configuration

```bash
# Use specific configuration file
shard-md --config ./project-config.yaml process --collection project-docs docs/

# Override configuration with environment variables
SHARD_MD_CHUNK_SIZE=1500 CHROMA_HOST=remote-server.com \
  shard-md process --collection remote-docs document.md
```

### 2.2 Metadata Management

#### 2.2.1 Custom Metadata Addition

```bash
# Add custom metadata to all chunks
shard-md process \
  --collection technical-docs \
  --custom-metadata '{"department": "engineering", "confidentiality": "internal"}' \
  --metadata-prefix "org_" \
  docs/

# Collection with metadata
shard-md process \
  --collection project-alpha \
  --create-collection \
  --collection-metadata '{"description": "Project Alpha Documentation", "version": "2.1", "team": "backend"}' \
  project-docs/
```

#### 2.2.2 Frontmatter Processing

```bash
# Include YAML frontmatter as metadata
shard-md process --collection blog-posts --include-frontmatter blog/

# Exclude frontmatter processing
shard-md process --collection plain-docs --no-frontmatter docs/
```

**Example with Frontmatter:**
Input file (`blog/post-1.md`):

```markdown
---
title: "Getting Started with CLI Tools"
author: "Jane Developer"
tags: ["cli", "tools", "productivity"]
published: 2024-01-15
---

# Getting Started with CLI Tools

This post covers the basics of building effective CLI tools...
```

Results in chunk metadata:

```json
{
  "title": "Getting Started with CLI Tools",
  "author": "Jane Developer",
  "tags": ["cli", "tools", "productivity"],
  "published": "2024-01-15",
  "source_file": "/path/to/blog/post-1.md",
  "chunk_index": 0,
  "structural_context": "# Getting Started with CLI Tools"
}
```

## 3. Collection Management Examples

### 3.1 Collection Operations

#### 3.1.1 List and Inspect Collections

```bash
# List all collections
shard-md collections list

# List with metadata
shard-md collections list --show-metadata

# Filter collections
shard-md collections list --filter "*docs*"

# Show collection details
shard-md collections info technical-docs --show-documents
```

**Expected Output:**

```
Collections:
┌─────────────────┬────────┬─────────────────┬──────────────────────┐
│ Name            │ Count  │ Created         │ Description          │
├─────────────────┼────────┼─────────────────┼──────────────────────┤
│ technical-docs  │ 1,247  │ 2024-01-15     │ Technical documentation │
│ api-reference   │ 892    │ 2024-01-10     │ API reference docs   │
│ user-guides     │ 334    │ 2024-01-08     │ User guide documents │
└─────────────────┴────────┴─────────────────┴──────────────────────┘
```

#### 3.1.2 Create and Delete Collections

```bash
# Create empty collection
shard-md collections create project-docs \
  --description "Project documentation" \
  --metadata '{"team": "engineering", "version": "1.0"}'

# Delete collection with confirmation
shard-md collections delete old-docs

# Force delete without confirmation
shard-md collections delete --force test-collection

# Delete with backup
shard-md collections delete --backup legacy-docs
```

### 3.2 Collection Backup and Migration

#### 3.2.1 Export Collection Data

```bash
# Export collection to JSON
shard-md collections export technical-docs --format json --output backup.json

# Export with filtering
shard-md collections export api-docs \
  --filter "metadata.version = '2.0'" \
  --output api-v2-backup.json
```

#### 3.2.2 Import Data to Collection

```bash
# Import from backup
shard-md collections import new-technical-docs --input backup.json

# Import with transformation
shard-md collections import migrated-docs \
  --input legacy-backup.json \
  --transform-metadata "add_field('migrated_at', '2024-01-15')"
```

## 4. Query and Search Examples

### 4.1 Document Search

#### 4.1.1 Basic Search Operations

```bash
# Search for documents
shard-md query search "machine learning algorithms" --collection technical-docs

# Search with result limit
shard-md query search "API documentation" --collection api-docs --limit 5

# Search with similarity threshold
shard-md query search "deployment guide" \
  --collection user-guides \
  --similarity-threshold 0.7
```

**Expected Output:**

```
Search Results for: "machine learning algorithms"
Collection: technical-docs

┌────────────────────┬───────────┬─────────────────────────────────────┐
│ Document ID        │ Score     │ Content Preview                     │
├────────────────────┼───────────┼─────────────────────────────────────┤
│ a1b2c3d4_0001     │ 0.95      │ # Machine Learning Algorithms       │
│                    │           │ This section covers various ML...   │
├────────────────────┼───────────┼─────────────────────────────────────┤
│ e5f6g7h8_0003     │ 0.87      │ ## Supervised Learning              │
│                    │           │ Supervised algorithms require...    │
├────────────────────┼───────────┼─────────────────────────────────────┤
│ i9j0k1l2_0002     │ 0.82      │ Popular algorithms include...       │
└────────────────────┴───────────┴─────────────────────────────────────┘

Found 3 results in 0.15s
```

#### 4.1.2 Get Specific Documents

```bash
# Get document by ID
shard-md query get a1b2c3d4_0001 --collection technical-docs

# Get with metadata
shard-md query get e5f6g7h8_0003 --collection api-docs --include-metadata

# Export search results
shard-md query search "docker deployment" \
  --collection devops-docs \
  --format json \
  --output docker-results.json
```

### 4.2 Advanced Search Patterns

#### 4.2.1 Metadata-Based Filtering

```bash
# Search with metadata filters (future feature)
shard-md query search "configuration" \
  --collection technical-docs \
  --filter "metadata.section = 'setup'" \
  --filter "metadata.difficulty = 'beginner'"

# Search by file source
shard-md query search "installation" \
  --collection docs \
  --filter "metadata.source_file contains 'getting-started'"
```

#### 4.2.2 Batch Query Operations

```bash
# Query multiple terms
shard-md query batch \
  --collection technical-docs \
  --queries "['API authentication', 'rate limiting', 'error handling']" \
  --output batch-results.json

# Query with different collections
shard-md query multi-collection \
  --collections "technical-docs,api-docs,user-guides" \
  --query "webhook configuration" \
  --limit 10
```

## 5. Monitoring and Debugging Examples

### 5.1 Verbose Output and Debugging

#### 5.1.1 Debug Processing Issues

```bash
# Verbose output
shard-md --verbose process --collection debug-docs document.md

# Maximum verbosity
shard-md -vvv process --collection debug-docs --batch-size 1 docs/

# Log to file
shard-md --log-file processing.log process --collection docs docs/
```

**Verbose Output Example:**

```
2024-01-15 10:30:15 - shard_markdown.cli - INFO - Starting processing with config: ChunkingConfig(default_size=1000, ...)
2024-01-15 10:30:15 - shard_markdown.core.processor - DEBUG - Processing file: /path/to/document.md
2024-01-15 10:30:15 - shard_markdown.core.parser - DEBUG - Parsing markdown content (2,345 characters)
2024-01-15 10:30:15 - shard_markdown.core.chunking - DEBUG - Generated 3 chunks using structure method
2024-01-15 10:30:15 - shard_markdown.chromadb.client - DEBUG - Connecting to ChromaDB at localhost:8000
2024-01-15 10:30:16 - shard_markdown.chromadb.client - INFO - Inserted 3 chunks in 0.12s
```

#### 5.1.2 Dry Run and Validation

```bash
# Dry run to see what would be processed
shard-md process --dry-run --collection test-docs docs/

# Validate files before processing
shard-md validate --recursive --check-frontmatter --check-links docs/

# Preview chunking strategy
shard-md preview --chunk-method semantic --chunk-size 1200 large-document.md
```

### 5.2 Performance Monitoring

#### 5.2.1 Benchmark Operations

```bash
# Process with timing information
time shard-md process --collection benchmark-test large-docs/

# Monitor memory usage (with external tools)
/usr/bin/time -v shard-md process --collection memory-test --max-workers 1 docs/

# Profile processing performance
shard-md process --collection perf-test --show-stats docs/
```

#### 5.2.2 Health Checks

```bash
# Check ChromaDB connectivity
shard-md collections list  # Should succeed if connection is healthy

# Validate configuration
shard-md config show --validate

# Test processing pipeline
shard-md validate --test-chunking sample-document.md
```

## 6. Integration Examples

### 6.1 CI/CD Pipeline Integration

#### 6.1.1 GitHub Actions Workflow

```yaml
# .github/workflows/docs-processing.yml
name: Process Documentation

on:
  push:
    paths: ['docs/**/*.md']

jobs:
  process-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install shard-markdown
        run: uv add shard-markdown

      - name: Start ChromaDB
        run: |
          docker run -d -p 8000:8000 chromadb/chroma
          sleep 10

      - name: Process documentation
        run: |
          shard-md process \
            --collection docs-$(date +%Y%m%d) \
            --create-collection \
            --recursive \
            --custom-metadata '{"build": "${{ github.sha }}", "branch": "${{ github.ref_name }}"}' \
            docs/
        env:
          CHROMA_HOST: localhost
          CHROMA_PORT: 8000
```

#### 6.1.2 Shell Script Automation

```bash
#!/bin/bash
# scripts/update-docs.sh

set -e

COLLECTION_NAME="docs-$(date +%Y%m%d)"
DOCS_DIR="./documentation"
BACKUP_DIR="./backups"

echo "Processing documentation updates..."

# Create backup of existing collection
if shard-md collections list | grep -q "docs-current"; then
    echo "Backing up current collection..."
    shard-md collections export docs-current \
        --output "$BACKUP_DIR/docs-backup-$(date +%Y%m%d_%H%M%S).json"
fi

# Process updated documentation
shard-md process \
    --collection "$COLLECTION_NAME" \
    --create-collection \
    --recursive \
    --chunk-size 1200 \
    --chunk-overlap 200 \
    --custom-metadata "{\"updated\": \"$(date -Iseconds)\", \"version\": \"$1\"}" \
    "$DOCS_DIR"

# Update alias to point to new collection
shard-md collections alias docs-current "$COLLECTION_NAME"

echo "Documentation processing complete!"
echo "New collection: $COLLECTION_NAME"
```

### 6.2 Watch Mode and Automated Processing

#### 6.2.1 File System Monitoring

```bash
# Watch directory for changes (requires watchdog)
shard-md watch \
    --collection live-docs \
    --auto-update \
    --debounce 5 \
    docs/

# Watch with filtering
shard-md watch \
    --collection api-docs \
    --pattern "api-*.md" \
    --exclude-pattern "*-draft.md" \
    --on-change "echo 'Processed: {}'" \
    api-documentation/
```

#### 6.2.2 Scheduled Processing

```bash
# Cron job for daily processing
# 0 2 * * * /usr/local/bin/shard-md process --collection daily-docs --recursive /data/docs

# Process with rotation
shard-md process \
    --collection "docs-$(date +%w)" \
    --clear-collection \
    --recursive \
    --batch-size 50 \
    /data/weekly-docs/
```

## 7. Troubleshooting Examples

### 7.1 Common Issues and Solutions

#### 7.1.1 Connection Problems

```bash
# Test ChromaDB connection
shard-md collections list
# If this fails, check:
# 1. ChromaDB server is running
# 2. Host/port settings are correct
# 3. Network connectivity

# Debug connection with verbose logging
shard-md --verbose collections list

# Test with different host
shard-md --chroma-host 192.168.1.100 collections list
```

#### 7.1.2 Processing Failures

```bash
# Process single file to isolate issues
shard-md process --collection test --create-collection problematic-file.md

# Validate file content
shard-md validate problematic-file.md --check-frontmatter

# Try different chunking method
shard-md process --collection test --chunk-method fixed problematic-file.md

# Check file encoding
file problematic-file.md
```

#### 7.1.3 Performance Issues

```bash
# Reduce batch size for memory-constrained environments
shard-md process \
    --collection large-docs \
    --batch-size 5 \
    --max-workers 2 \
    large-dataset/

# Monitor memory usage
shard-md process --collection test --show-memory-usage docs/

# Use smaller chunk sizes
shard-md process \
    --collection optimized \
    --chunk-size 800 \
    --chunk-overlap 100 \
    docs/
```

### 7.2 Error Recovery

#### 7.2.1 Partial Processing Recovery

```bash
# Resume processing from failure point
shard-md process \
    --collection resumed-docs \
    --skip-existing \
    --log-file recovery.log \
    docs/

# Process only failed files from previous run
grep "FAILED" previous-run.log | awk '{print $4}' | \
    xargs shard-md process --collection recovered-files
```

#### 7.2.2 Data Validation and Repair

```bash
# Validate collection integrity
shard-md collections validate technical-docs

# Check for duplicate chunks
shard-md collections deduplicate technical-docs --dry-run

# Repair metadata inconsistencies
shard-md collections repair technical-docs --fix-metadata
```

These comprehensive usage examples demonstrate the full range of capabilities and real-world scenarios for the shard-markdown CLI tool, from basic document processing to advanced automation and troubleshooting.
