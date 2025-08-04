"""Main entry point for shard-markdown CLI."""

import sys

from .cli.main import cli


if __name__ == "__main__":
    sys.exit(cli())
