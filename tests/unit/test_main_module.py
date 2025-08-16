import runpy
from unittest.mock import MagicMock, patch

import pytest


@patch("shard_markdown.cli.main.cli")
@patch("sys.exit")
@pytest.mark.unit
def test_main_invokes_cli(mock_exit: MagicMock, mock_cli: MagicMock) -> None:
    """Test that __main__ module executes the CLI and exits."""
    mock_cli.return_value = 123
    runpy.run_module("shard_markdown.__main__", run_name="__main__")
    mock_cli.assert_called_once()
    mock_exit.assert_called_once_with(123)
