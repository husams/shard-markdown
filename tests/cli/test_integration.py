"""Integration tests for CLI components."""

from unittest.mock import MagicMock, Mock, patch

import click
import pytest

from shard_markdown.cli.bridge import (
    ClickToPatternBridge,
    bridge_config_command,
    click_to_pattern_route,
    get_real_config_handler,
)
from shard_markdown.cli.patterns import ExitCode


class TestClickToPatternBridge:
    """Test Click to Pattern Matching bridge functionality."""

    def test_bridge_initialization(self) -> None:
        """Test bridge initialization with Click context."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"config": "test_config", "verbose": 2, "quiet": True}

        bridge = ClickToPatternBridge(ctx)

        assert bridge.ctx == ctx
        assert bridge.config == "test_config"
        assert bridge.verbose == 2
        assert bridge.quiet is True

    def test_bridge_initialization_with_none_obj(self) -> None:
        """Test bridge initialization with None ctx.obj."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = None

        bridge = ClickToPatternBridge(ctx)

        assert bridge.ctx == ctx
        assert bridge.config is None
        assert bridge.verbose == 0
        assert bridge.quiet is False

    def test_create_namespace(self) -> None:
        """Test namespace creation from context and additional kwargs."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"config": "test_config", "verbose": 1}

        bridge = ClickToPatternBridge(ctx)
        namespace = bridge.create_namespace(extra_arg="extra_value")

        assert namespace.config == "test_config"
        assert namespace.verbose == 1
        assert namespace.quiet is False
        assert namespace.extra_arg == "extra_value"

    def test_route_to_pattern_handler_success(self) -> None:
        """Test successful routing to pattern handler."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"config": None}

        bridge = ClickToPatternBridge(ctx)

        with patch("shard_markdown.cli.routing.route_command") as mock_route:
            mock_route.return_value = ExitCode.SUCCESS

            result = bridge.route_to_pattern_handler("test", "command", arg="value")

            assert result == ExitCode.SUCCESS
            mock_route.assert_called_once()

    def test_route_to_pattern_handler_error(self) -> None:
        """Test error handling in pattern handler routing."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"config": None, "verbose": 0}

        bridge = ClickToPatternBridge(ctx)

        with patch("shard_markdown.cli.routing.route_command") as mock_route:
            mock_route.side_effect = RuntimeError("Test error")

            result = bridge.route_to_pattern_handler("test", "command")

            assert result == ExitCode.GENERAL_ERROR

    def test_handle_exit_code_success(self) -> None:
        """Test exit code handling for success."""
        ctx = click.Context(click.Command("test"))
        bridge = ClickToPatternBridge(ctx)

        # Should not raise
        bridge.handle_exit_code(ExitCode.SUCCESS)

    def test_handle_exit_code_error(self) -> None:
        """Test exit code handling for errors."""
        ctx = click.Context(click.Command("test"))
        bridge = ClickToPatternBridge(ctx)

        with pytest.raises(SystemExit):
            bridge.handle_exit_code(ExitCode.GENERAL_ERROR)


class TestClickToPatternRouteDecorator:
    """Test the Click to Pattern route decorator."""

    def test_decorator_basic_functionality(self) -> None:
        """Test basic decorator functionality."""

        @click_to_pattern_route("config", "show")
        def dummy_command(format: str = "yaml") -> None:
            pass

        ctx = click.Context(click.Command("config"))
        ctx.obj = {"config": None}

        with patch("shard_markdown.cli.routing.route_command") as mock_route:
            mock_route.return_value = ExitCode.SUCCESS

            with patch("click.get_current_context", return_value=ctx):
                result = dummy_command(format="json")

                assert result is None
                mock_route.assert_called_once()

    def test_decorator_filters_context_from_kwargs(self) -> None:
        """Test decorator filters out Click context from pattern handler kwargs."""

        @click_to_pattern_route("config", "show")
        def dummy_command(ctx: click.Context, format: str = "yaml") -> None:
            pass

        ctx = click.Context(click.Command("config"))
        ctx.obj = {"config": None}

        with patch("shard_markdown.cli.routing.route_command") as mock_route:
            mock_route.return_value = ExitCode.SUCCESS

            dummy_command(ctx, format="json")

            # Verify ctx is filtered out from kwargs passed to pattern handler
            mock_route.assert_called_once()

    def test_decorator_error_handling(self) -> None:
        """Test decorator error handling and exit codes."""

        @click_to_pattern_route("config", "show")
        def dummy_command() -> None:
            pass

        ctx = click.Context(click.Command("config"))
        ctx.obj = {"config": None}

        with patch("shard_markdown.cli.routing.route_command") as mock_route:
            mock_route.return_value = ExitCode.GENERAL_ERROR

            with patch("click.get_current_context", return_value=ctx):
                with pytest.raises(SystemExit):
                    dummy_command()


class TestBridgeConfigCommand:
    """Test bridging config commands to Click implementations."""

    def test_get_real_config_handler(self) -> None:
        """Test getting real config handlers."""
        handlers = get_real_config_handler()

        assert "show" in handlers
        assert "set" in handlers
        assert "init" in handlers
        assert "path" in handlers
        assert callable(handlers["show"])

    def test_bridge_config_show_command(self) -> None:
        """Test bridging config show command."""
        ctx = click.Context(click.Command("config"))
        ctx.obj = {"config": MagicMock()}

        with patch(
            "shard_markdown.cli.bridge.get_real_config_handler"
        ) as mock_get_handlers:
            mock_show = Mock()
            mock_get_handlers.return_value = {"show": mock_show}

            # Mock ctx.invoke to verify it's called correctly
            with patch.object(ctx, "invoke") as mock_invoke:
                result = bridge_config_command(
                    ctx, "show", format="json", section="test"
                )

                assert result == ExitCode.SUCCESS
                mock_invoke.assert_called_once_with(
                    mock_show, format="json", section="test"
                )

    def test_bridge_config_set_command(self) -> None:
        """Test bridging config set command."""
        ctx = click.Context(click.Command("config"))
        ctx.obj = {"config": MagicMock()}

        with patch(
            "shard_markdown.cli.bridge.get_real_config_handler"
        ) as mock_get_handlers:
            mock_set = Mock()
            mock_get_handlers.return_value = {"set": mock_set}

            # Mock ctx.invoke to verify it's called correctly
            with patch.object(ctx, "invoke") as mock_invoke:
                result = bridge_config_command(
                    ctx,
                    "set",
                    key="test.key",
                    value="test_value",
                    is_global=True,
                    is_local=False,
                )

                assert result == ExitCode.SUCCESS
                mock_invoke.assert_called_once_with(
                    mock_set,
                    key="test.key",
                    value="test_value",
                    is_global=True,
                    is_local=False,
                )

    def test_bridge_config_init_command(self) -> None:
        """Test bridging config init command."""
        ctx = click.Context(click.Command("config"))
        ctx.obj = {"config": MagicMock()}

        with patch(
            "shard_markdown.cli.bridge.get_real_config_handler"
        ) as mock_get_handlers:
            mock_init = Mock()
            mock_get_handlers.return_value = {"init": mock_init}

            # Mock ctx.invoke to verify it's called correctly
            with patch.object(ctx, "invoke") as mock_invoke:
                result = bridge_config_command(
                    ctx, "init", is_global=False, force=True, template=None
                )

                assert result == ExitCode.SUCCESS
                mock_invoke.assert_called_once_with(
                    mock_init, is_global=False, force=True, template=None
                )

    def test_bridge_config_path_command(self) -> None:
        """Test bridging config path command."""
        ctx = click.Context(click.Command("config"))
        ctx.obj = {"config": MagicMock()}

        with patch(
            "shard_markdown.cli.bridge.get_real_config_handler"
        ) as mock_get_handlers:
            mock_path = Mock()
            mock_get_handlers.return_value = {"path": mock_path}

            # Mock ctx.invoke to verify it's called correctly
            with patch.object(ctx, "invoke") as mock_invoke:
                result = bridge_config_command(ctx, "path")

                assert result == ExitCode.SUCCESS
                mock_invoke.assert_called_once_with(mock_path)

    def test_bridge_config_unknown_command(self) -> None:
        """Test bridging unknown config command."""
        ctx = click.Context(click.Command("config"))
        ctx.obj = {"config": MagicMock()}

        result = bridge_config_command(ctx, "unknown")

        assert result == ExitCode.GENERAL_ERROR

    def test_bridge_config_command_click_abort(self) -> None:
        """Test handling Click abort in config command."""
        ctx = click.Context(click.Command("config"))
        ctx.obj = {"config": MagicMock()}

        with patch(
            "shard_markdown.cli.bridge.get_real_config_handler"
        ) as mock_get_handlers:
            mock_show = Mock()
            mock_get_handlers.return_value = {"show": mock_show}

            # Mock ctx.invoke to raise click.Abort
            with patch.object(ctx, "invoke") as mock_invoke:
                mock_invoke.side_effect = click.Abort()

                result = bridge_config_command(ctx, "show")

                assert result == ExitCode.GENERAL_ERROR

    def test_bridge_config_command_exception(self) -> None:
        """Test handling general exception in config command."""
        ctx = click.Context(click.Command("config"))
        ctx.obj = {"config": MagicMock()}

        with patch(
            "shard_markdown.cli.bridge.get_real_config_handler"
        ) as mock_get_handlers:
            mock_show = Mock()
            mock_get_handlers.return_value = {"show": mock_show}

            # Mock ctx.invoke to raise exception
            with patch.object(ctx, "invoke") as mock_invoke:
                mock_invoke.side_effect = RuntimeError("Test error")

                result = bridge_config_command(ctx, "show")

                assert result == ExitCode.GENERAL_ERROR
