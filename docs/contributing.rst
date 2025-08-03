============
Contributing
============

We welcome contributions to shard-markdown!

Development Setup
=================

.. code-block:: bash

   git clone https://github.com/shard-markdown/shard-markdown.git
   cd shard-markdown
   uv sync --dev

Running Tests
=============

.. code-block:: bash

   uv run pytest

Code Quality
============

Run formatting and linting:

.. code-block:: bash

   uv run black src/ tests/
   uv run isort src/ tests/
   uv run flake8 src/ tests/
   uv run mypy src/

Submitting Changes
==================

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

Guidelines
==========

- Follow PEP 8 style guidelines
- Add tests for new functionality
- Update documentation as needed
- Keep commits focused and descriptive