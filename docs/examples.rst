========
Examples
========

Practical examples of using shard-markdown.

Basic Document Processing
=========================

Process a single document:

.. code-block:: bash

   shard-md process README.md --chunking-strategy structure

Batch Processing
================

Process multiple documents:

.. code-block:: bash

   shard-md process docs/*.md --collection documentation --store

Advanced Workflows
==================

Building a Knowledge Base
-------------------------

.. code-block:: bash

   # Create collection
   shard-md collections create knowledge-base
   
   # Process documents
   shard-md process wiki/ --collection knowledge-base --store --recursive
   
   # Query the knowledge base
   shard-md query "installation" --collection knowledge-base

API Usage Examples
==================

Programmatic usage examples will be added here.

Integration Examples
====================

Examples of integrating with other tools and systems.