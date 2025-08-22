import runpy
from unittest.mock import MagicMock, patch

import pytest


@patch("shard_markdown.cli.main.shard_md")
@pytest.mark.unit
def test_main_invokes_cli(mock_shard_md: MagicMock) -> None:
    """Test that __main__ module executes the CLI."""
    runpy.run_module("shard_markdown.__main__", run_name="__main__")
    mock_shard_md.assert_called_once()
