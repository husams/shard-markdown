=============
CLI Reference
=============

This section provides detailed documentation for all command-line interface
options.

.. note::
   The CLI documentation is auto-generated from the actual command help text.
   For the most up-to-date information, run ``shard-md --help`` or see the
   auto-generated CLI documentation.

Main Command
============

.. code-block:: text

   Usage: shard-md [OPTIONS] COMMAND [ARGS]...

   Intelligent markdown document chunking for ChromaDB collections.

   Options:
     --config PATH          Path to configuration file
     --verbose, -v          Enable verbose output
     --quiet, -q           Suppress all output except errors
     --version             Show version and exit
     --help                Show this message and exit

   Commands:
     process      Process markdown documents
     collections  Manage ChromaDB collections
     query        Query documents in collections
     config       Configuration management

Commands
========

process
-------

Process markdown documents and optionally store them in ChromaDB.

collections
-----------

Manage ChromaDB collections (create, list, delete, etc.).

query
-----

Search for content in stored document collections.

config
------

Initialize and manage configuration files.

For detailed help on any command, run:

.. code-block:: bash

   shard-md COMMAND --help

Examples
========

See :doc:`examples` for practical usage examples.
