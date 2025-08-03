============
Installation
============

Requirements
============

- Python 3.11 or higher
- ChromaDB server (optional, for database features)

Installation Methods
====================

From PyPI (Recommended)
-----------------------

.. code-block:: bash

   pip install shard-markdown

With ChromaDB Support
---------------------

.. code-block:: bash

   pip install shard-markdown[chromadb]

Development Installation
------------------------

For development, clone the repository and install in editable mode:

.. code-block:: bash

   git clone https://github.com/shard-markdown/shard-markdown.git
   cd shard-markdown
   uv sync --dev

Using uv (Recommended for Development)
---------------------------------------

`uv <https://github.com/astral-sh/uv>`_ is the recommended package manager
for development:

.. code-block:: bash

   # Install uv first
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Clone and install
   git clone https://github.com/shard-markdown/shard-markdown.git
   cd shard-markdown
   uv sync --dev

Verification
============

Verify the installation:

.. code-block:: bash

   shard-md --version

Optional Dependencies
=====================

ChromaDB Integration
--------------------

For ChromaDB integration, install the optional dependencies:

.. code-block:: bash

   pip install chromadb tiktoken

Docker
------

A Docker image is available for containerized deployments:

.. code-block:: bash

   docker pull shard-markdown/shard-markdown:latest

Configuration
=============

After installation, create a configuration file:

.. code-block:: bash

   shard-md config init

This creates a default configuration file at ``~/.shard-markdown/config.yaml``.

Troubleshooting
===============

Common Issues
-------------

**Import Errors**
   Ensure all dependencies are installed. For ChromaDB features, install the
   optional dependencies.

**Permission Errors**
   Use ``--user`` flag with pip or consider using a virtual environment.

**Version Conflicts**
   Use a fresh virtual environment to avoid dependency conflicts.

Environment Variables
=====================

Set these environment variables if needed:

- ``SHARD_MD_CONFIG_PATH``: Custom configuration file path
- ``SHARD_MD_CHROMADB_HOST``: ChromaDB server host
- ``SHARD_MD_CHROMADB_PORT``: ChromaDB server port
- ``SHARD_MD_LOG_LEVEL``: Logging level (DEBUG, INFO, WARNING, ERROR)
