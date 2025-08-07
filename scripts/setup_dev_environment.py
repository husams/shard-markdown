#!/usr/bin/env python3
"""Development environment setup and verification script for shard-markdown.

This script ensures that all required development tools and hooks are properly
installed and configured to prevent CI/CD failures.
"""

import os
import shutil
import subprocess  # noqa: S404
import sys
from pathlib import Path


# Colors for output
class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    ENDC = "\033[0m"


class DevEnvironmentSetup:
    """Main development environment setup class."""

    def __init__(self) -> None:
        """Initialize the setup."""
        self.project_root = Path(__file__).parent.parent
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def _print_step(self, step: str) -> None:
        """Print a setup step."""
        print(f"{Colors.BLUE}▶ {step}{Colors.ENDC}")

    def _print_success(self, message: str) -> None:
        """Print a success message."""
        print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")

    def _print_error(self, message: str) -> None:
        """Print an error message."""
        print(f"{Colors.RED}❌ {message}{Colors.ENDC}")
        self.errors.append(message)

    def _print_warning(self, message: str) -> None:
        """Print a warning message."""
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.ENDC}")
        self.warnings.append(message)

    def _run_command(
        self, command: list[str], description: str, check: bool = True
    ) -> tuple[bool, str]:
        """Run a command and return success status and output."""
        try:
            result = subprocess.run(  # noqa: S603
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=check,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.CalledProcessError as e:
            return False, str(e)
        except FileNotFoundError:
            return False, f"Command not found: {command[0]}"

    def check_python_version(self) -> None:
        """Verify Python version meets requirements."""
        self._print_step("Checking Python version")

        version_info = sys.version_info
        if version_info >= (3, 12):
            self._print_success(
                f"Python {version_info.major}.{version_info.minor}.{version_info.micro}"
            )
        else:
            self._print_error(
                f"Python {version_info.major}.{version_info.minor}."
                f"{version_info.micro} is too old. Requires Python 3.12+"
            )

    def check_uv_installation(self) -> None:
        """Check if uv is installed and working."""
        self._print_step("Checking uv package manager")

        if shutil.which("uv"):
            success, output = self._run_command(["uv", "--version"], "uv version")
            if success:
                version = output.strip()
                self._print_success(f"uv {version}")
            else:
                self._print_error("uv is installed but not working correctly")
        else:
            self._print_error(
                "uv not found. Install with: "
                "curl -LsSf https://astral.sh/uv/install.sh | sh"
            )

    def install_dependencies(self) -> None:
        """Install project dependencies."""
        self._print_step("Installing project dependencies")

        success, output = self._run_command(
            ["uv", "sync", "--dev"], "install dependencies", check=False
        )

        if success:
            self._print_success("Dependencies installed successfully")
        else:
            self._print_error(f"Failed to install dependencies: {output}")

    def setup_pre_commit_hooks(self) -> None:
        """Install and configure pre-commit hooks."""
        self._print_step("Setting up pre-commit hooks")

        # Check if pre-commit is available
        success, _ = self._run_command(
            ["uv", "run", "pre-commit", "--version"], "pre-commit version"
        )
        if not success:
            self._print_error(
                "pre-commit not available. Check dependency installation."
            )
            return

        # Install pre-commit hooks
        success, output = self._run_command(
            ["uv", "run", "pre-commit", "install"],
            "install pre-commit hooks",
            check=False,
        )

        if success:
            self._print_success("Pre-commit hooks installed")
        else:
            self._print_error(f"Failed to install pre-commit hooks: {output}")
            return

        # Install pre-push hook
        success, output = self._run_command(
            ["uv", "run", "pre-commit", "install", "--hook-type", "pre-push"],
            "install pre-push hooks",
            check=False,
        )

        if success:
            self._print_success("Pre-push hooks installed")
        else:
            self._print_warning(f"Pre-push hooks installation had issues: {output}")

    def verify_git_hooks(self) -> None:
        """Verify that git hooks are properly installed."""
        self._print_step("Verifying git hooks installation")

        hooks_dir = self.project_root / ".git" / "hooks"

        # Check pre-commit hook
        pre_commit_hook = hooks_dir / "pre-commit"
        if pre_commit_hook.exists() and pre_commit_hook.is_file():
            self._print_success("Pre-commit hook installed")
        else:
            self._print_error("Pre-commit hook not found")

        # Check our custom pre-push hook
        pre_push_hook = hooks_dir / "pre-push"
        if pre_push_hook.exists() and pre_push_hook.is_file():
            # Verify it's executable
            if os.access(pre_push_hook, os.X_OK):
                self._print_success("Pre-push hook installed and executable")
            else:
                self._print_error("Pre-push hook exists but is not executable")
        else:
            self._print_warning("Custom pre-push hook not found")

    def verify_development_tools(self) -> None:
        """Verify that all required development tools work correctly."""
        self._print_step("Verifying development tools")

        tools = [
            (["uv", "run", "ruff", "--version"], "Ruff linter/formatter"),
            (["uv", "run", "mypy", "--version"], "MyPy type checker"),
            (["uv", "run", "pytest", "--version"], "Pytest testing framework"),
            (["uv", "run", "pre-commit", "--version"], "Pre-commit hooks"),
        ]

        for command, tool_name in tools:
            success, output = self._run_command(
                command, f"{tool_name} version", check=False
            )
            if success:
                version = output.strip().split("\n")[
                    0
                ]  # First line usually contains version
                self._print_success(f"{tool_name}: {version}")
            else:
                self._print_error(f"{tool_name} not working: {output}")

    def run_initial_quality_checks(self) -> None:
        """Run initial quality checks to ensure everything works."""
        self._print_step("Running initial quality checks")

        # Run type checking
        success, output = self._run_command(
            ["uv", "run", "mypy", "src/"], "type checking", check=False
        )
        if success:
            self._print_success("Type checking passed")
        else:
            self._print_error(f"Type checking failed: {output}")

        # Run linting
        success, output = self._run_command(
            ["uv", "run", "ruff", "check", "src/"], "linting", check=False
        )
        if success:
            self._print_success("Linting passed")
        else:
            self._print_error(f"Linting failed: {output}")

        # Run formatting check
        success, output = self._run_command(
            ["uv", "run", "ruff", "format", "--check", "src/"],
            "format check",
            check=False,
        )
        if success:
            self._print_success("Formatting check passed")
        else:
            self._print_error(f"Formatting check failed: {output}")

    def test_pre_commit_hooks(self) -> None:
        """Test that pre-commit hooks work correctly."""
        self._print_step("Testing pre-commit hooks")

        success, output = self._run_command(
            ["uv", "run", "pre-commit", "run", "--all-files"],
            "pre-commit test",
            check=False,
        )
        if success:
            self._print_success("Pre-commit hooks passed")
        else:
            self._print_warning(f"Pre-commit hooks had issues: {output}")

    def create_vscode_settings(self) -> None:
        """Ensure VS Code settings are present for team consistency."""
        self._print_step("Checking VS Code settings")

        vscode_dir = self.project_root / ".vscode"
        settings_file = vscode_dir / "settings.json"

        if settings_file.exists():
            self._print_success("VS Code settings found")
        else:
            self._print_warning(
                "VS Code settings not found. IDE configuration may not be optimal."
            )

    def print_setup_summary(self) -> None:
        """Print a summary of the setup process."""
        print(f"\n{Colors.BOLD}🎯 Development Environment Setup Summary{Colors.ENDC}")
        print("=" * 60)

        if not self.errors:
            print(
                f"{Colors.GREEN}{Colors.BOLD}✅ Setup completed successfully!"
                f"{Colors.ENDC}"
            )
            print("\nYour development environment is ready. You can now:")
            print("- Make changes to the codebase")
            print("- Commit changes (pre-commit hooks will run automatically)")
            print("- Push changes (pre-push hooks will run type checking)")
            print("- Run manual checks with: python scripts/verify.py")
        else:
            print(
                f"{Colors.RED}{Colors.BOLD}❌ Setup completed with "
                f"{len(self.errors)} error(s){Colors.ENDC}"
            )
            print("\nPlease fix the following issues:")
            for error in self.errors:
                print(f"  • {error}")

        if self.warnings:
            print(f"\n{Colors.YELLOW}⚠️  {len(self.warnings)} warning(s):{Colors.ENDC}")
            for warning in self.warnings:
                print(f"  • {warning}")

        print(f"\n{Colors.BLUE}📚 Next steps:{Colors.ENDC}")
        print("1. Read CLAUDE.md for development guidelines")
        print("2. Check .vscode/ settings if using VS Code")
        print("3. Run tests: uv run pytest")
        print("4. Make a test commit to verify hooks work")

    def run_full_setup(self) -> int:
        """Run the complete development environment setup."""
        print(
            f"{Colors.BOLD}{Colors.BLUE}🚀 Setting up shard-markdown "
            f"development environment{Colors.ENDC}\n"
        )

        self.check_python_version()
        self.check_uv_installation()

        if not self.errors:  # Only continue if basic requirements are met
            self.install_dependencies()
            self.setup_pre_commit_hooks()
            self.verify_git_hooks()
            self.verify_development_tools()
            self.create_vscode_settings()
            self.run_initial_quality_checks()
            self.test_pre_commit_hooks()

        self.print_setup_summary()

        return 1 if self.errors else 0


def main() -> int:
    """Main entry point."""
    setup = DevEnvironmentSetup()
    return setup.run_full_setup()


if __name__ == "__main__":
    sys.exit(main())
