# Shard Markdown CLI Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying and using the shard-markdown CLI utility in various environments.

## Installation

### Prerequisites

- Python 3.8 or higher
- uv package manager (recommended) or pip
- Optional: ChromaDB server for production use

### Core Installation

#### From PyPI (when published)

```bash
# Core functionality with mock ChromaDB
uv add shard-markdown

# With full ChromaDB support
uv add shard-markdown[chromadb]
```

#### Development Installation

```bash
# Clone repository
git clone https://github.com/shard-markdown/shard-markdown.git
cd shard-markdown

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
uv pip install -e .

# With full ChromaDB support
uv pip install -e .[chromadb]

# With development dependencies
uv pip install -e .[dev]
```

#### Docker Installation (Future)

```bash
docker run -v $(pwd):/workspace shard-markdown/cli:latest process --collection docs /workspace/*.md
```

## Configuration

### Configuration File

Create a configuration file at one of these locations:

- `~/.shard-md/config.yaml`
- `./shard-md.yaml`
- Custom location via `--config` flag

#### Example Configuration

```yaml
# ChromaDB Configuration
chromadb:
  host: localhost
  port: 8000
  ssl: false
  timeout: 30
  auth_token: null

# Chunking Configuration
chunking:
  default_size: 1000
  default_overlap: 200
  method: structure
  respect_boundaries: true
  max_tokens: null

# Processing Configuration
processing:
  batch_size: 10
  max_workers: 4
  recursive: false
  pattern: "*.md"
  include_frontmatter: true
  include_path_metadata: true

# Logging Configuration
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file_path: null
  max_file_size: 10485760
  backup_count: 5

# Custom metadata
custom_metadata: {}
plugins: []
```

### Environment Variables

Override configuration with environment variables:

```bash
export CHROMA_HOST=localhost
export CHROMA_PORT=8000
export CHROMA_SSL=false
export CHROMA_AUTH_TOKEN=your-token
export SHARD_MD_CHUNK_SIZE=1500
export SHARD_MD_CHUNK_OVERLAP=300
export SHARD_MD_BATCH_SIZE=20
export SHARD_MD_MAX_WORKERS=8
export SHARD_MD_LOG_LEVEL=DEBUG
export SHARD_MD_USE_MOCK_CHROMADB=true
```

## Basic Usage

### Processing Documents

#### Single File

```bash
shard-md process --collection my-docs document.md
```

#### Multiple Files

```bash
shard-md process --collection tech-docs *.md
```

#### Directory Processing

```bash
shard-md process --collection all-docs --recursive ./docs/
```

#### Custom Chunking

```bash
shard-md process \
  --collection custom-docs \
  --chunk-size 1500 \
  --chunk-overlap 300 \
  --chunk-method structure \
  *.md
```

#### Dry Run

```bash
shard-md process --collection test --dry-run *.md
```

### Collection Management

#### List Collections

```bash
shard-md collections list
shard-md collections list --format json
shard-md collections list --show-metadata
```

#### Create Collection

```bash
shard-md collections create my-docs --description "Documentation collection"
shard-md collections create api-docs --metadata '{"version": "1.0", "source": "api"}'
```

#### Collection Information

```bash
shard-md collections info my-docs
shard-md collections info my-docs --format json
```

#### Delete Collection

```bash
shard-md collections delete my-docs
shard-md collections delete my-docs --force
```

### Querying Documents

#### Search Documents

```bash
shard-md query search --collection my-docs "search term"
shard-md query search --collection my-docs "Python code" --limit 5
shard-md query search --collection my-docs "API" --format json
```

#### Get Specific Document

```bash
shard-md query get --collection my-docs document-id-123
shard-md query get --collection my-docs document-id-123 --format yaml
```

### Configuration Management

#### Show Configuration

```bash
shard-md config show
shard-md config show --format yaml
```

#### Initialize Configuration

```bash
shard-md config init
shard-md config init --force
```

#### Set Configuration Values

```bash
shard-md config set chunking.default_size 1500
shard-md config set chromadb.host production-server
```

## Deployment Scenarios

### Development Environment

#### Local Development with Mock ChromaDB

```bash
# No additional setup required
shard-md process --collection dev-docs *.md
```

#### Local Development with Real ChromaDB

```bash
# Start ChromaDB server
docker run -p 8000:8000 chromadb/chroma:latest

# Configure and use
export CHROMA_HOST=localhost
export CHROMA_PORT=8000
shard-md process --collection dev-docs *.md
```

### Production Environment

#### Production ChromaDB Setup

```bash
# Environment configuration
export CHROMA_HOST=chromadb.production.com
export CHROMA_PORT=8000
export CHROMA_SSL=true
export CHROMA_AUTH_TOKEN=production-token

# Process documents
shard-md process --collection production-docs /path/to/docs/*.md
```

#### Batch Processing Script

```bash
#!/bin/bash
# batch-process.sh

# Configuration
COLLECTION_NAME="docs-$(date +%Y%m%d)"
DOCS_PATH="/data/markdown-docs"
LOG_FILE="/var/log/shard-md/processing.log"

# Create collection
shard-md collections create "$COLLECTION_NAME" \
  --description "Daily documentation update $(date)"

# Process documents
shard-md process \
  --collection "$COLLECTION_NAME" \
  --recursive \
  --max-workers 8 \
  --log-file "$LOG_FILE" \
  "$DOCS_PATH"

# Report results
shard-md collections info "$COLLECTION_NAME"
```

### Container Deployment

#### Dockerfile Example

```dockerfile
FROM python:3.11-slim

# Install dependencies
RUN uv pip install shard-markdown[chromadb]

# Copy configuration
COPY config.yaml /app/config.yaml

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV SHARD_MD_CONFIG=/app/config.yaml

# Entry point
ENTRYPOINT ["shard-md"]
```

#### Docker Compose Example

```yaml
version: '3.8'

services:
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chromadb_data:/chroma/chroma

  shard-md:
    build: .
    depends_on:
      - chromadb
    environment:
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
    volumes:
      - ./docs:/workspace/docs
    command: process --collection docs --recursive /workspace/docs

volumes:
  chromadb_data:
```

### CI/CD Integration

#### GitHub Actions Example

```yaml
name: Process Documentation

on:
  push:
    paths: ['docs/**/*.md']

jobs:
  process-docs:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install shard-markdown
      run: uv add shard-markdown[chromadb]

    - name: Process documentation
      env:
        CHROMA_HOST: ${{ secrets.CHROMA_HOST }}
        CHROMA_AUTH_TOKEN: ${{ secrets.CHROMA_AUTH_TOKEN }}
      run: |
        shard-md process \
          --collection "docs-${{ github.sha }}" \
          --create-collection \
          --recursive \
          docs/
```

## Monitoring and Logging

### Log Configuration

```yaml
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file_path: /var/log/shard-md/application.log
  max_file_size: 10485760  # 10MB
  backup_count: 5
```

### Log Analysis

```bash
# Monitor processing
tail -f /var/log/shard-md/application.log

# Search for errors
grep ERROR /var/log/shard-md/application.log

# Processing statistics
grep "Processing completed" /var/log/shard-md/application.log | wc -l
```

### Health Checks

```bash
# Check ChromaDB connectivity
shard-md collections list > /dev/null && echo "ChromaDB OK" || echo "ChromaDB Error"

# Validate configuration
shard-md config show > /dev/null && echo "Config OK" || echo "Config Error"
```

## Performance Tuning

### Processing Optimization

```bash
# Increase worker threads for large batches
shard-md process --max-workers 16 --collection large-docs *.md

# Optimize chunk size for your use case
shard-md process --chunk-size 2000 --chunk-overlap 400 *.md

# Use fixed chunking for consistent performance
shard-md process --chunk-method fixed *.md
```

### Memory Management

```bash
# Process large directories in smaller batches
find docs/ -name "*.md" | head -100 | xargs shard-md process --collection batch1
find docs/ -name "*.md" | tail -n +101 | head -100 | xargs shard-md process --collection batch2
```

## Troubleshooting

### Common Issues

#### ChromaDB Connection Failed

```bash
# Check ChromaDB server status
curl http://localhost:8000/api/v1/heartbeat

# Use mock client for testing
shard-md process --use-mock --collection test *.md
```

#### Permission Denied

```bash
# Check file permissions
ls -la document.md

# Ensure proper directory access
chmod 755 /path/to/docs/
chmod 644 /path/to/docs/*.md
```

#### Out of Memory

```bash
# Reduce worker threads
shard-md process --max-workers 2 *.md

# Use smaller chunk sizes
shard-md process --chunk-size 500 *.md

# Process files individually
for file in *.md; do
  shard-md process --collection docs "$file"
done
```

### Debug Mode

```bash
# Enable verbose logging
shard-md -vvv process --collection debug-docs *.md

# Use debug log level
export SHARD_MD_LOG_LEVEL=DEBUG
shard-md process --collection debug-docs *.md
```

## Security Considerations

### Authentication

```bash
# Use environment variables for sensitive data
export CHROMA_AUTH_TOKEN="$(cat /path/to/token)"

# Avoid command-line secrets
# Bad: shard-md process --auth-token secret123
# Good: Use environment variables or config files
```

### File Permissions

```bash
# Secure configuration file
chmod 600 ~/.shard-md/config.yaml

# Secure log files
chmod 640 /var/log/shard-md/application.log
chown app:app /var/log/shard-md/application.log
```

### Network Security

```yaml
# Use SSL in production
chromadb:
  ssl: true
  host: secure-chromadb.example.com
  port: 443
```

## Backup and Recovery

### Collection Backup

```bash
# Export collection data (future feature)
shard-md collections export my-docs --output backup.json

# Import collection data (future feature)
shard-md collections import backup.json --collection restored-docs
```

### Configuration Backup

```bash
# Backup configuration
cp ~/.shard-md/config.yaml config-backup-$(date +%Y%m%d).yaml

# Version control configuration
git add config.yaml
git commit -m "Update shard-md configuration"
```

## Support and Maintenance

### Regular Maintenance

- Monitor log files for errors
- Update shard-markdown regularly: `uv add shard-markdown` (automatically gets latest)
- Clean up old log files: `logrotate /etc/logrotate.d/shard-md`
- Monitor ChromaDB server health

### Getting Help

- GitHub Issues: <https://github.com/shard-markdown/shard-markdown/issues>
- Documentation: <https://shard-markdown.readthedocs.io>
- CLI Help: `shard-md --help`, `shard-md COMMAND --help`

This deployment guide covers all major deployment scenarios and provides practical examples for getting started with shard-markdown CLI in any environment.
