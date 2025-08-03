=============
Configuration
=============

This section covers configuration options and settings for shard-markdown.

Configuration File
==================

The configuration file is typically located at ``~/.shard-markdown/config.yaml``.

Basic Structure
---------------

.. code-block:: yaml

   chromadb:
     host: localhost
     port: 8000
     ssl: false
     timeout: 30
   
   chunking:
     strategy: structure
     max_chunk_size: 1000
     overlap: 100
   
   processing:
     preserve_structure: true
     extract_metadata: true
   
   logging:
     level: INFO
     format: detailed

Configuration Sections
======================

ChromaDB Settings
-----------------

.. code-block:: yaml

   chromadb:
     host: localhost              # ChromaDB server host
     port: 8000                   # ChromaDB server port
     ssl: false                   # Use SSL connection
     auth_token: null             # Authentication token
     timeout: 30                  # Connection timeout

Chunking Settings
-----------------

.. code-block:: yaml

   chunking:
     strategy: structure          # Chunking strategy (fixed, structure)
     max_chunk_size: 1000        # Maximum chunk size in characters
     overlap: 100                # Overlap between chunks
     preserve_headers: true       # Keep headers with content

Environment Variables
=====================

Override configuration with environment variables:

- ``SHARD_MD_CONFIG_PATH``: Configuration file path
- ``SHARD_MD_CHROMADB_HOST``: ChromaDB host
- ``SHARD_MD_CHROMADB_PORT``: ChromaDB port
- ``SHARD_MD_LOG_LEVEL``: Logging level

Command Line Options
====================

Most configuration options can be overridden via command line flags.

See :doc:`cli-reference` for complete details.