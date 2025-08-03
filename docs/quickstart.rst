===========
Quick Start
===========

This guide will help you get started with shard-markdown in just a few minutes.

Prerequisites
=============

Before you begin, ensure you have:

- Python 3.11 or higher installed
- shard-markdown installed (see :doc:`installation`)
- A markdown document to process

Basic Usage
===========

1. Initialize Configuration
---------------------------

Create a default configuration:

.. code-block:: bash

   shard-md config init

This creates a configuration file at ``~/.shard-markdown/config.yaml``.

2. Process Your First Document
------------------------------

Process a markdown file using the default settings:

.. code-block:: bash

   shard-md process README.md

This will:
- Parse the markdown document
- Split it into chunks using the default strategy
- Display the results

3. Process with ChromaDB Storage
--------------------------------

If you have ChromaDB running, store the chunks in a collection:

.. code-block:: bash

   shard-md process README.md --collection my-docs --store

4. Query Your Documents
-----------------------

Search for content in your stored documents:

.. code-block:: bash

   shard-md query "installation guide" --collection my-docs

Configuration Examples
======================

Basic Configuration
-------------------

Create ``config.yaml``:

.. code-block:: yaml

   chromadb:
     host: localhost
     port: 8000

   chunking:
     strategy: structure
     max_chunk_size: 1000
     overlap: 100

Processing Options
==================

Chunking Strategies
-------------------

**Structure-aware (Recommended)**:

.. code-block:: bash

   shard-md process doc.md --chunking-strategy structure

**Fixed-size**:

.. code-block:: bash

   shard-md process doc.md --chunking-strategy fixed --max-chunk-size 500

**Custom overlap**:

.. code-block:: bash

   shard-md process doc.md --overlap 50

Batch Processing
----------------

Process multiple files:

.. code-block:: bash

   shard-md process docs/*.md --collection knowledge-base --store

Collection Management
=====================

List Collections
----------------

.. code-block:: bash

   shard-md collections list

Create Collection
-----------------

.. code-block:: bash

   shard-md collections create my-collection

Collection Info
---------------

.. code-block:: bash

   shard-md collections info my-collection

Next Steps
==========

- Read the :doc:`cli-reference` for complete command documentation
- Explore :doc:`configuration` for advanced settings
- Check out :doc:`examples` for real-world use cases
- Learn about the :doc:`api-reference` for programmatic usage

Common Workflows
================

Documentation Processing
-------------------------

.. code-block:: bash

   # Process all docs in a directory
   shard-md process docs/ --collection documentation --store --recursive

   # Query the documentation
   shard-md query "API reference" --collection documentation --limit 5

Knowledge Base Creation
-----------------------

.. code-block:: bash

   # Create a knowledge base collection
   shard-md collections create kb --description "Company knowledge base"

   # Process various document sources
   shard-md process wiki/*.md --collection kb --store
   shard-md process manuals/*.md --collection kb --store

   # Search the knowledge base
   shard-md query "deployment process" --collection kb

Tips and Best Practices
========================

1. **Choose the Right Strategy**: Use ``structure`` for well-formatted
   documents, ``fixed`` for consistent chunk sizes
2. **Tune Chunk Size**: Start with 1000 characters and adjust based on your use
   case
3. **Use Metadata**: Include custom metadata in document frontmatter for better
   searchability
4. **Monitor Performance**: Use ``--verbose`` flag to see processing details
5. **Backup Collections**: Regularly backup your ChromaDB data
