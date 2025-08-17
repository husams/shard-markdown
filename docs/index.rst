.. shard-markdown documentation master file

=================================
shard-markdown Documentation
=================================

**shard-markdown** is an intelligent markdown document chunking tool designed for
ChromaDB collections. It provides sophisticated chunking strategies, metadata
extraction, and seamless integration with vector databases.

.. toctree::
   :maxdepth: 2
   :caption: User Guide:

   overview
   installation
   quickstart
   cli-reference
   configuration
   examples

.. toctree::
   :maxdepth: 2
   :caption: Reference:

   api-reference
   architecture
   technical-specification

.. toctree::
   :maxdepth: 1
   :caption: Development:

   contributing
   changelog

Features
========

* **Intelligent Chunking**: Multiple chunking strategies including fixed-size,
  structure-aware, and custom implementations
* **Metadata Extraction**: Automatic extraction of structural context and document
  metadata
* **ChromaDB Integration**: Native support for ChromaDB with optimized bulk
  operations
* **CLI Interface**: Comprehensive command-line interface for document processing
* **Flexible Configuration**: YAML-based configuration with environment variable
  support
* **Type Safety**: Full type hints and validation using Pydantic

Quick Start
===========

Installation
------------

.. code-block:: bash

   pip install shard-markdown

Basic Usage
-----------

Process a markdown document and store it in ChromaDB:

.. code-block:: bash

   shard-md process document.md --collection my-docs --chunking-strategy structure

Configuration
-------------

Create a configuration file:

.. code-block:: yaml

   chromadb:
     host: localhost
     port: 8000

   chunking:
     strategy: structure
     max_chunk_size: 1000
     overlap: 100

API Reference
=============

For detailed API documentation, see the :doc:`api-reference` section.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
