========
Overview
========

**shard-markdown** is a powerful tool for processing markdown documents into
manageable chunks suitable for vector databases, particularly ChromaDB. It
provides intelligent chunking strategies that preserve document structure and
context.

Core Concepts
=============

Chunking Strategies
-------------------

The library supports multiple chunking strategies:

**Fixed-size Chunking**
   Split documents into chunks of a specified size with optional overlap.

**Structure-aware Chunking**
   Respect markdown structure (headers, paragraphs, lists) when creating chunks.

**Custom Chunking**
   Implement your own chunking logic using the provided interfaces.

Document Processing
-------------------

The processing pipeline includes:

1. **Parsing**: Convert markdown to structured elements
2. **Chunking**: Apply the selected chunking strategy
3. **Metadata Extraction**: Extract relevant metadata from each chunk
4. **Storage**: Store chunks in ChromaDB with metadata

Metadata
--------

Each chunk includes metadata such as:

- Source file path
- Chunk index within the document
- Structural context (e.g., parent headers)
- Processing timestamp
- Custom metadata from frontmatter

Architecture
============

The library is organized into several key modules:

- **Core**: Document parsing, processing, and models
- **Chunking**: Various chunking strategy implementations
- **ChromaDB**: Database integration and operations
- **CLI**: Command-line interface
- **Config**: Configuration management
- **Utils**: Shared utilities and error handling

Use Cases
=========

**Documentation Processing**
   Break down large documentation into searchable chunks while preserving
   structure.

**Knowledge Base Creation**
   Build searchable knowledge bases from markdown content.

**Content Analysis**
   Analyze document structure and content distribution.

**RAG Pipeline Integration**
   Prepare documents for Retrieval-Augmented Generation systems.
