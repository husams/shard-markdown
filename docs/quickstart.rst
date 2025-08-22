===========
Quick Start
===========

This guide will help you get started with shard-markdown in just a few minutes.

Prerequisites
=============

Before you begin, ensure you have:

- Python 3.8 or higher installed
- shard-markdown installed (see :doc:`installation`)
- A markdown document to process
- (Optional) ChromaDB running for storage

Installation
============

Install shard-markdown using pip or uv:

.. code-block:: bash

   # Using pip
   pip install shard-markdown
   
   # Using uv (recommended)
   uv add shard-markdown
   
   # Or from source
   git clone https://github.com/husams/shard-markdown.git
   cd shard-markdown
   uv pip install -e .

Basic Usage
===========

1. Process Your First Document
------------------------------

The simplest way to use shard-markdown is to process a file directly:

.. code-block:: bash

   shard-md README.md

This will:
- Parse the markdown document
- Split it into chunks using structure-aware chunking
- Display the chunks to your terminal

2. Customize Chunk Settings
---------------------------

Adjust chunk size and overlap for your needs:

.. code-block:: bash

   shard-md document.md --size 500 --overlap 50

3. Store in ChromaDB
--------------------

If you have ChromaDB running, store chunks in a collection:

.. code-block:: bash

   shard-md manual.md --store --collection documentation

4. Process Multiple Files
-------------------------

Process all markdown files in a directory:

.. code-block:: bash

   # Process directory (non-recursive)
   shard-md docs/
   
   # Process directory recursively
   shard-md docs/ --recursive
   
   # Process with glob pattern
   shard-md "*.md" --store --collection my-docs

Configuration
=============

Optional: Create a configuration file for persistent settings:

.. code-block:: bash

   # Create config directory
   mkdir -p ~/.shard-md
   
   # Create config file
   cat > ~/.shard-md/config.yaml << EOF
   chunk:
     size: 1000
     overlap: 200
     strategy: structure
     
   storage:
     vectordb:
       host: localhost
       port: 8000
   
   logging:
     level: INFO
   EOF

Common Scenarios
================

Documentation Processing
------------------------

Process technical documentation with semantic chunking:

.. code-block:: bash

   shard-md technical-docs/ \
     --recursive \
     --strategy semantic \
     --size 1500 \
     --store \
     --collection tech-docs

Research Papers
---------------

Process academic papers preserving structure:

.. code-block:: bash

   shard-md paper.md \
     --strategy section \
     --preserve-structure \
     --metadata \
     --store \
     --collection research

Code Documentation
------------------

Process code documentation without splitting code blocks:

.. code-block:: bash

   shard-md api-docs.md \
     --strategy structure \
     --size 2000 \
     --store \
     --collection api-docs

Quick Tips
==========

1. **Dry Run**: Preview chunks without storing them:

   .. code-block:: bash

      shard-md document.md --dry-run --verbose

2. **Quiet Mode**: Suppress output when storing:

   .. code-block:: bash

      shard-md *.md --store --collection docs --quiet

3. **Custom Config**: Use project-specific configuration:

   .. code-block:: bash

      shard-md docs/ --config-path ./project-config.yaml

4. **Check Version**: Verify your installation:

   .. code-block:: bash

      shard-md --version

Next Steps
==========

- Learn about different :doc:`chunking strategies <chunking-strategies>`
- Explore :doc:`configuration options <configuration>`
- Read the :doc:`CLI reference <cli-reference>` for all options
- Check out :doc:`examples <examples>` for more use cases

Troubleshooting
===============

ChromaDB Connection Issues
--------------------------

If you get connection errors:

1. Ensure ChromaDB is running:

   .. code-block:: bash

      docker run -p 8000:8000 chromadb/chroma

2. Check your configuration:

   .. code-block:: bash

      # Verify ChromaDB is accessible
      curl http://localhost:8000/api/v1/heartbeat

3. Use environment variables if needed:

   .. code-block:: bash

      export CHROMA_HOST=localhost
      export CHROMA_PORT=8000
      shard-md document.md --store --collection test

File Not Found
--------------

If files aren't found:

- Use absolute paths or ensure you're in the correct directory
- Check file permissions
- Use quotes for glob patterns: ``shard-md "*.md"``

Getting Help
============

.. code-block:: bash

   # Show help message
   shard-md --help
   
   # Visit documentation
   # https://shard-markdown.readthedocs.io
   
   # Report issues
   # https://github.com/husams/shard-markdown/issues