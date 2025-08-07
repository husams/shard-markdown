#!/usr/bin/env python3
"""Comprehensive test verification script for shard-markdown project.

This script runs all necessary checks before committing or creating PR to prevent
CI failures and ensure code quality.
"""

import argparse
import json
import shutil
import subprocess  # noqa: S404
import sys
import time
from pathlib import Path
from typing import Any


# ANSI color codes for output
class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


class CheckResult:
    """Result of a check operation."""

    def __init__(
        self,
        name: str,
        success: bool,
        duration: float,
        output: str = "",
        error: str = "",
    ):
        """Initialize check result.

        Args:
            name: Name of the check
            success: Whether the check passed
            duration: Time taken for the check in seconds
            output: Standard output from the check
            error: Error output from the check
        """
        self.name = name
        self.success = success
        self.duration = duration
        self.output = output
        self.error = error


class ProgressIndicator:
    """Simple progress indicator for long-running operations."""

    def __init__(self, message: str) -> None:
        """Initialize progress indicator.

        Args:
            message: Message to display during progress
        """
        self.message = message
        self.running = False

    def __enter__(self) -> "ProgressIndicator":
        """Start progress indicator."""
        print(f"{Colors.OKBLUE}⏳ {self.message}...{Colors.ENDC}", end="", flush=True)
        self.running = True
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop progress indicator."""
        if self.running:
            print()
            self.running = False


class VerificationRunner:
    """Main verification runner class."""

    def __init__(
        self,
        fix: bool = False,
        fast: bool = False,
        coverage: bool = False,
        exit_early: bool = False,
        verbose: bool = False,
    ):
        """Initialize verification runner.

        Args:
            fix: Whether to automatically fix formatting/linting issues
            fast: Whether to skip slow tests
            coverage: Whether to enforce coverage thresholds
            exit_early: Whether to exit on first failure
            verbose: Whether to show detailed output
        """
        self.fix = fix
        self.fast = fast
        self.coverage = coverage
        self.exit_early = exit_early
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        self.results: list[CheckResult] = []

    def _run_command(
        self,
        command: list[str],
        check_name: str,
        cwd: Path | None = None,
        capture_output: bool = True,
    ) -> CheckResult:
        """Run a command and return the result.

        Args:
            command: Command to run as list of strings
            check_name: Name of the check for reporting
            cwd: Working directory for the command
            capture_output: Whether to capture stdout/stderr

        Returns:
            CheckResult object with the outcome
        """
        start_time = time.time()
        cwd = cwd or self.project_root

        try:
            if capture_output:
                result = subprocess.run(  # noqa: S603
                    command,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                success = result.returncode == 0
                output = result.stdout
                error = result.stderr
            else:
                # For commands that need to show output in real-time
                result = subprocess.run(command, cwd=cwd, check=False, text=True)  # noqa: S603
                success = result.returncode == 0
                output = ""
                error = ""

            duration = time.time() - start_time

            return CheckResult(
                name=check_name,
                success=success,
                duration=duration,
                output=output,
                error=error,
            )

        except Exception as e:
            duration = time.time() - start_time
            return CheckResult(
                name=check_name,
                success=False,
                duration=duration,
                error=str(e),
            )

    def _print_result(self, result: CheckResult) -> None:
        """Print the result of a check.

        Args:
            result: CheckResult to print
        """
        status_symbol = "✅" if result.success else "❌"
        status_color = Colors.OKGREEN if result.success else Colors.FAIL

        print(
            f"{status_symbol} {Colors.BOLD}{result.name}{Colors.ENDC} "
            f"({result.duration:.2f}s) - {status_color}"
            f"{'PASSED' if result.success else 'FAILED'}{Colors.ENDC}"
        )

        if not result.success and (self.verbose or result.error):
            if result.error:
                print(f"   {Colors.FAIL}Error: {result.error.strip()}{Colors.ENDC}")
            if result.output and self.verbose:
                print(
                    f"   {Colors.WARNING}Output: {result.output.strip()}{Colors.ENDC}"
                )

    def _check_ruff_format(self) -> CheckResult:
        """Check code formatting with ruff."""
        command = ["ruff", "format"]
        if not self.fix:
            command.append("--check")
        command.extend(["src/", "tests/", "scripts/"])

        with ProgressIndicator("Checking code formatting"):
            return self._run_command(command, "Code Formatting (ruff format)")

    def _check_ruff_lint(self) -> CheckResult:
        """Check linting with ruff."""
        command = ["ruff", "check"]
        if self.fix:
            command.append("--fix")
        command.extend(["src/", "tests/", "scripts/"])

        with ProgressIndicator("Running linter"):
            return self._run_command(command, "Linting (ruff check)")

    def _check_mypy(self) -> CheckResult:
        """Check type annotations with mypy."""
        command = ["mypy", "src/"]

        with ProgressIndicator("Running type checking"):
            return self._run_command(command, "Type Checking (mypy)")

    def _check_bandit_security(self) -> CheckResult | None:
        """Run security checks with bandit."""
        # Check if bandit is available
        if not shutil.which("bandit"):
            return CheckResult(
                name="Security Scanning (bandit)",
                success=True,  # Skip if not available
                duration=0.0,
                error="Bandit not installed - skipping security scan",
            )

        command = ["bandit", "-r", "src/", "-f", "json"]

        with ProgressIndicator("Running security checks"):
            result = self._run_command(command, "Security Scanning (bandit)")

            # Bandit returns non-zero for security issues
            if not result.success and result.output:
                try:
                    bandit_data = json.loads(result.output)
                    if bandit_data.get("results"):
                        num_issues = len(bandit_data["results"])
                        result.error = f"Found {num_issues} security issues"
                except json.JSONDecodeError:
                    pass

            return result

    def _run_tests(self) -> CheckResult:
        """Run the test suite."""
        command = ["python3", "-m", "pytest"]

        if self.fast:
            command.extend(["-m", "not slow"])

        if self.coverage:
            command.extend(["--cov=shard_markdown", "--cov-report=term-missing"])
            if not self.verbose:
                command.append("--cov-report=term:skip-covered")

        command.extend(["-v", "--tb=short"])

        test_name = "Tests" + (" (fast mode)" if self.fast else "")
        if self.coverage:
            test_name += " with Coverage"

        with ProgressIndicator("Running test suite"):
            return self._run_command(
                command, test_name, capture_output=not self.verbose
            )

    def _check_coverage_threshold(self) -> CheckResult | None:
        """Check if coverage meets minimum threshold."""
        if not self.coverage:
            return None

        # Run coverage report to get percentage
        command = ["python3", "-m", "coverage", "report", "--format=total"]

        with ProgressIndicator("Checking coverage threshold"):
            result = self._run_command(command, "Coverage Threshold Check")

            if result.success and result.output.strip():
                try:
                    coverage_pct = float(result.output.strip())
                    minimum_coverage = 85.0  # From CLAUDE.md requirements

                    if coverage_pct < minimum_coverage:
                        result.success = False
                        result.error = (
                            f"Coverage {coverage_pct:.1f}% is below minimum "
                            f"threshold of {minimum_coverage}%"
                        )
                    else:
                        result.error = f"Coverage: {coverage_pct:.1f}%"

                except ValueError:
                    result.success = False
                    result.error = "Could not parse coverage percentage"

            return result

    def run_all_checks(self) -> bool:
        """Run all verification checks.

        Returns:
            True if all checks passed, False otherwise
        """
        print(
            f"{Colors.HEADER}{Colors.BOLD}"
            "🚀 Running shard-markdown verification checks"
            f"{Colors.ENDC}\n"
        )

        checks = [
            ("format", self._check_ruff_format),
            ("lint", self._check_ruff_lint),
            ("typecheck", self._check_mypy),
            ("security", self._check_bandit_security),
            ("tests", self._run_tests),
        ]

        # Add coverage check if requested
        if self.coverage:
            checks.append(("coverage", self._check_coverage_threshold))

        all_passed = True

        for _check_id, check_func in checks:
            result = check_func()
            if result is None:  # Skip coverage check if not requested
                continue

            self.results.append(result)
            self._print_result(result)

            if not result.success:
                all_passed = False
                if self.exit_early:
                    print(
                        f"\n{Colors.FAIL}Exiting early due to failure in "
                        f"{result.name}{Colors.ENDC}"
                    )
                    break

        # Print summary
        self._print_summary()
        return all_passed

    def _print_summary(self) -> None:
        """Print a summary of all check results."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}📊 Summary{Colors.ENDC}")
        print("=" * 50)

        passed = sum(1 for r in self.results if r.success)
        total = len(self.results)
        total_time = sum(r.duration for r in self.results)

        if passed == total:
            print(f"{Colors.OKGREEN}✅ All {total} checks passed!{Colors.ENDC}")
        else:
            failed = total - passed
            print(f"{Colors.FAIL}❌ {failed} out of {total} checks failed{Colors.ENDC}")

        print(f"⏱️  Total time: {total_time:.2f}s")

        # Show failed checks
        failed_checks = [r for r in self.results if not r.success]
        if failed_checks:
            print(f"\n{Colors.FAIL}Failed checks:{Colors.ENDC}")
            for result in failed_checks:
                print(f"  - {result.name}")
                if result.error:
                    print(f"    {result.error}")


def main() -> int:
    """Main entry point for the verification script."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive verification checks for shard-markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/verify.py                    # Run all checks
  python scripts/verify.py --fix              # Fix formatting/linting issues
  python scripts/verify.py --fast             # Skip slow tests
  python scripts/verify.py --coverage         # Include coverage validation
  python scripts/verify.py --exit-early       # Exit on first failure
  python scripts/verify.py --verbose          # Show detailed output
        """,
    )

    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix formatting and linting issues",
    )

    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip slow tests (use -m 'not slow')",
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Enforce coverage thresholds and show coverage report",
    )

    parser.add_argument(
        "--exit-early",
        action="store_true",
        help="Exit immediately on first failure",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output for all checks",
    )

    args = parser.parse_args()

    runner = VerificationRunner(
        fix=args.fix,
        fast=args.fast,
        coverage=args.coverage,
        exit_early=args.exit_early,
        verbose=args.verbose,
    )

    try:
        success = runner.run_all_checks()
        return 0 if success else 1
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}❌ Verification interrupted by user{Colors.ENDC}")
        return 1
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ Unexpected error: {e}{Colors.ENDC}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
