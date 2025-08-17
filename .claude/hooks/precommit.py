#!/usr/bin/env python3
"""Claude Code Hook: Pre-commit Quality Checks.

============================================
This hook runs as a PostToolUse hook for Write/Edit/MultiEdit tools.
It automatically formats, lints, and type-checks Python files using ruff and mypy.
"""

# TOOL BEHAVIOR OBSERVATIONS & REFLECTIONS:
# ==========================================
# 1. SELF-FORMATTING: This hook automatically formats itself when edited!
#    - Any edits to this .py file trigger the hook recursively
#    - Ruff format runs and reformats the code in real-time
#    - Docstrings get reformatted, spacing adjusted, line breaks changed
#    - This creates a "living document" that maintains consistent style
#
# 2. OUTPUT STREAMS BEHAVIOR:
#    - stdout: Success messages, informational output (visible to user)
#    - stderr: Error messages, failures, warnings (visible to user)
#    - JSON: Edit blocking via {"decision": "block", "reason": "..."} (parsed by Claude)
#
# 3. EXIT CODE STRATEGY:
#    - 0: All checks passed successfully - edit proceeds
#    - 1: Errors occurred - signals failure to calling process
#
# 4. PROCESSING PIPELINE:
#    - Format (beautify) → Lint (fix issues) → Security check (bandit) → Type check (enforce safety)
#    - Only type check failures block edits completely with JSON response
#    - Format/lint/security failures cause exit code 1 but don't block via JSON
#
# 5. DEBUGGING CAPABILITIES:
#    - All operations logged to ~/.claude_logs/precommit_hook_YYYYMMDD.log
#    - Session ID prominently displayed for correlation
#    - Complete hook input data dumped for transparency
#    - Environment variables captured for context

import json
import logging
import os
import subprocess  # noqa: S404
import sys
from datetime import datetime
from pathlib import Path


def _setup_logging() -> logging.Logger:
    """Setup logging to file in ~/.claude_logs directory."""
    # Create logs directory in user's home directory
    # This ensures all hook executions are logged in a consistent location
    logs_dir = Path.home() / ".claude_logs"
    logs_dir.mkdir(exist_ok=True)  # Create if doesn't exist, ignore if it does

    # Create a named logger for this specific hook
    # Using a unique name prevents conflicts with other loggers
    logger = logging.getLogger("precommit_hook")
    logger.setLevel(logging.INFO)  # INFO level for production use

    # Remove any existing handlers to prevent duplicate logging
    # This is important when the hook runs multiple times in one session
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create file handler with daily rotation using timestamp
    # Format: precommit_hook_YYYYMMDD.log (one file per day)
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = logs_dir / f"precommit_hook_{timestamp}.log"

    # Setup file handler to write to our daily log file
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)

    # Create detailed formatter for log entries
    # Includes timestamp, logger name, level, and message
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Attach the configured handler to our logger
    logger.addHandler(file_handler)

    return logger


def _run_command(command: list[str], logger: logging.Logger) -> tuple[bool, str]:
    """Execute a shell command and capture its output.

    Args:
        command: List of command parts (e.g., ["uv", "run", "ruff", "format",
                 "file"])
        logger: Logger instance for debugging

    Returns:
        Tuple of (success: bool, combined_output: str)
        - success: True if command exited with code 0
        - combined_output: Combined stdout and stderr from the command
    """
    cmd_str = " ".join(command)
    logger.debug(f"Executing command: {cmd_str}")

    try:
        # Run command with captured output, don't raise on non-zero exit
        # Security note: command list is constructed from trusted sources only
        result = subprocess.run(  # noqa: S603
            command,
            capture_output=True,  # Capture both stdout and stderr
            text=True,  # Return strings, not bytes
            check=False,  # Don't raise CalledProcessError on non-zero exit
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr  # Combine both streams

        logger.debug(f"Command exit code: {result.returncode}")
        if output.strip():
            logger.debug(f"Command output: {output.strip()}")

        return success, output
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return False, str(e)


def _format_python_file(file_path: str, logger: logging.Logger) -> bool:
    """Format a Python file using ruff formatter.

    Args:
        file_path: Path to the Python file to format
        logger: Logger instance for status tracking

    Returns:
        True if formatting succeeded, False otherwise

    Note:
        - Uses 'uv run ruff format' command
        - Prints success/failure messages to stdout/stderr
        - Non-blocking: formatting failures don't stop the hook
    """
    logger.info(f"Formatting Python file: {file_path}")
    success, output = _run_command(["uv", "run", "ruff", "format", file_path], logger)

    if success:
        print(f"✓ Ruff formatted: {file_path}")
        logger.info(f"Successfully formatted: {file_path}")
    else:
        # Format failures go to stderr but don't block the hook
        print(f"⚠ Ruff format failed for: {file_path}", file=sys.stderr)
        logger.error(f"Ruff format failed for: {file_path}")
        if output.strip():
            print(f"  Error: {output.strip()}", file=sys.stderr)
            logger.error(f"Format error output: {output.strip()}")
    return success


def _lint_python_file(file_path: str, logger: logging.Logger) -> bool:
    """Lint and auto-fix Python file using ruff linter.

    Args:
        file_path: Path to the Python file to lint
        logger: Logger instance for status tracking

    Returns:
        True if linting succeeded (no unfixable issues), False otherwise

    Note:
        - Uses 'uv run ruff check --fix' command
        - Automatically fixes issues where possible
        - Prints success/failure messages to stdout/stderr
        - Non-blocking: lint failures don't stop the hook
    """
    logger.info(f"Linting Python file: {file_path}")
    success, output = _run_command(
        ["uv", "run", "ruff", "check", "--fix", file_path], logger
    )

    if success:
        print(f"✓ Ruff linted: {file_path}")
        logger.info(f"Successfully linted: {file_path}")
    else:
        # Lint failures go to stderr but don't block the hook
        print(f"⚠ Ruff lint failed for: {file_path}", file=sys.stderr)
        logger.error(f"Ruff lint failed for: {file_path}")
        if output.strip():
            print(f"  Error: {output.strip()}", file=sys.stderr)
            logger.error(f"Lint error output: {output.strip()}")
    return success


def _check_bandit(file_path: str, logger: logging.Logger) -> tuple[bool, str]:
    """Security check Python file using bandit security linter.

    Args:
        file_path: Path to the Python file to security check
        logger: Logger instance for status tracking

    Returns:
        Tuple of (success: bool, output: str)
        - success: True if no security issues found, False otherwise
        - output: Combined bandit output (messages, findings, etc.)

    Note:
        - Uses 'uv run bandit' command with quiet mode
        - Non-blocking: Security warnings don't reject edits
        - Success messages go to stdout, warnings to stderr
        - Returns both status and output for information
    """
    logger.info(f"Security checking Python file: {file_path}")
    success, output = _run_command(["uv", "run", "bandit", "-q", file_path], logger)

    if success:
        print(f"✓ Bandit passed: {file_path}")
        logger.info(f"Bandit security check passed: {file_path}")
    else:
        # Security warnings are informational - send to stderr but don't block
        print(f"⚠ Bandit found security issues in: {file_path}", file=sys.stderr)
        logger.warning(f"Bandit security check found issues in: {file_path}")
        if output.strip():
            print(f"Security warnings: {output.strip()}", file=sys.stderr)
            logger.warning(f"Bandit output: {output.strip()}")

    return success, output.strip()


def _check_mypy(file_path: str, logger: logging.Logger) -> tuple[bool, str]:
    """Type check Python file using mypy static type checker.

    Args:
        file_path: Path to the Python file to type check
        logger: Logger instance for status tracking

    Returns:
        Tuple of (success: bool, output: str)
        - success: True if no type errors found, False otherwise
        - output: Combined mypy output (messages, errors, etc.)

    Note:
        - Uses 'uv run mypy' command (no unsafe fixes)
        - BLOCKING: Type check failures will reject the edit
        - Success messages go to stdout, errors to stderr
        - Returns both status and output for decision making
    """
    logger.info(f"Type checking Python file: {file_path}")
    success, output = _run_command(["uv", "run", "mypy", file_path], logger)

    if success:
        print(f"✓ MyPy passed: {file_path}")
        logger.info(f"MyPy type check passed: {file_path}")
        # Print any informational output to stdout
        if output.strip():
            print(f"MyPy output: {output.strip()}")
            logger.info(f"MyPy output: {output.strip()}")
    else:
        # Type errors are critical - send to stderr and will block the edit
        print(f"✗ MyPy failed for: {file_path}", file=sys.stderr)
        logger.error(f"MyPy type check failed for: {file_path}")
        if output.strip():
            print(f"Type errors: {output.strip()}", file=sys.stderr)
            logger.error(f"MyPy error output: {output.strip()}")

    return success, output.strip()


def main() -> None:
    """Main hook entry point that orchestrates the quality checks pipeline.

    This function:
    1. Sets up logging and parses hook input data
    2. Identifies the target Python file from various sources
    3. Runs format, lint, security check, and type check operations in sequence
    4. Blocks edits if type checking fails, allows with warnings otherwise
    """
    # INITIALIZATION: Setup logging infrastructure first
    # This must be done before any other operations to capture all activity
    logger = _setup_logging()
    logger.info("=" * 60)
    logger.info("Pre-commit quality checks hook started")

    # PARSE INPUT: Read and validate the JSON input from Claude Code
    # Claude Code passes hook data via stdin in JSON format
    try:
        input_data = json.load(sys.stdin)

        # Extract and prominently log the session ID for debugging correlation
        # Each Claude Code session has a unique ID for tracking across
        # tools/hooks
        session_id = input_data.get("session_id", "UNKNOWN")
        logger.info("=" * 60)
        logger.info(f"SESSION ID: {session_id}")
        logger.info("=" * 60)

        # Log the complete input data for debugging and transparency
        # This helps understand exactly what Claude Code is sending to the hook
        logger.info("=" * 40 + " HOOK INPUT DATA " + "=" * 40)
        logger.info(f"Received hook input data: {json.dumps(input_data, indent=2)}")
        logger.info("=" * 97)
    except json.JSONDecodeError as e:
        # Handle malformed JSON input gracefully
        error_msg = f"Invalid JSON input: {e}"
        logger.error(error_msg)
        print(f"Error: {error_msg}", file=sys.stderr)
        sys.exit(1)  # Exit with error code for invalid input

    # Log all environment variables for debugging hook context
    claude_env_vars = {k: v for k, v in os.environ.items() if k.startswith("CLAUDE_")}
    if claude_env_vars:
        logger.info(
            f"Claude environment variables: {json.dumps(claude_env_vars, indent=2)}"
        )
    else:
        logger.warning("No Claude environment variables found")

    # Also log some key system environment variables that might be relevant
    system_env_vars = {
        k: v for k, v in os.environ.items() if k in ["PWD", "HOME", "USER", "PATH"]
    }
    logger.info(f"Relevant system environment: {json.dumps(system_env_vars, indent=2)}")

    # TOOL VALIDATION: Ensure this hook should run for this tool
    # We only want to process file operations that modify code
    tool_name = input_data.get("tool_name", "")
    logger.info(f"Tool name: {tool_name}")

    # Exit early if not a file modification tool
    if tool_name not in ["Write", "Edit", "MultiEdit"]:
        logger.info(f"Skipping non-file tool: {tool_name}")
        sys.exit(0)  # Graceful exit, not an error

    # FILE PATH DETECTION: Multiple strategies to find the target file
    # Claude Code may provide the file path in different locations depending
    # on context

    # Strategy 1: Check tool result (most common location)
    tool_result = input_data.get("tool_result", {})
    file_path = tool_result.get("file_path")
    logger.info(f"File path from tool result: {file_path}")

    # Log complete tool result for debugging purposes
    logger.info(f"Complete tool result: {json.dumps(tool_result, indent=2)}")

    # Strategy 2: Fallback to environment variable (alternative location)
    if not file_path:
        file_path = os.environ.get("CLAUDE_TOOL_RESULT_FILE_PATH")
        logger.info(f"File path from environment: {file_path}")

    # Strategy 3: Check tool input as final fallback (rare but possible)
    if not file_path:
        tool_input = input_data.get("tool_input", {})
        file_path = tool_input.get("file_path")
        logger.info(f"File path from tool input: {file_path}")
        if tool_input:
            logger.info(f"Complete tool input: {json.dumps(tool_input, indent=2)}")

    # EXIT CONDITIONS: Determine if we should process this file

    # No file path found - nothing to process
    if not file_path:
        logger.info("No file path found, exiting gracefully")
        sys.exit(0)  # Not an error, just nothing to do

    # Only process Python files - skip everything else
    if not file_path.endswith(".py"):
        logger.info(f"Skipping non-Python file: {file_path}")
        sys.exit(0)  # Not an error, just not our target file type

    logger.info(f"Processing Python file: {file_path}")
    print(f"Processing Python file: {file_path}")

    # STEP 1: Format the file (non-blocking - beautify code)
    format_success = _format_python_file(file_path, logger)

    # STEP 2: Lint and auto-fix issues (non-blocking - improve code quality)
    lint_success = _lint_python_file(file_path, logger)

    # STEP 3: Security check with bandit (non-blocking - security awareness)
    bandit_success, bandit_output = _check_bandit(file_path, logger)

    # STEP 4: Type check with mypy (BLOCKING - enforce type safety)
    mypy_success, mypy_output = _check_mypy(file_path, logger)

    # CRITICAL DECISION POINT: Type safety enforcement
    # MyPy failures are blocking - they prevent the edit from being saved
    if not mypy_success:
        # Construct detailed error message for Claude to understand and fix
        error_message = (
            f"Type checking failed for {file_path}. "
            "The file contains type errors that must be fixed before "
            "proceeding."
        )
        if mypy_output:
            # Include specific type errors so Claude can address them
            error_message += f"\n\nType errors:\n{mypy_output}"

        logger.error("Rejecting edit due to mypy type check failure")

        # EDIT BLOCKING: Use Claude Code's JSON protocol to reject the edit
        # The "decision": "block" tells Claude Code to:
        # 1. Not save the file changes
        # 2. Show the error message to Claude for correction
        # 3. Allow Claude to retry with fixes
        rejection_output = {"decision": "block", "reason": error_message}

        # Send JSON response to stdout for Claude Code to parse
        print(json.dumps(rejection_output))
        logger.info(f"Sent rejection JSON: {json.dumps(rejection_output)}")
        sys.exit(1)  # Exit with error code to signal failure

    # SUCCESS EVALUATION: Determine final hook result
    # All four checks completed - evaluate overall success
    if format_success and lint_success and bandit_success and mypy_success:
        # Perfect outcome: all quality checks passed
        logger.info("Hook completed successfully - all checks passed")
        sys.exit(0)  # Success: edit proceeds with clean code
    else:
        # Partial success: type safety maintained but style/security issues remain
        # Format/lint/bandit failures are warnings only since mypy passed
        logger.warning("Hook completed with some warnings (but mypy passed)")
        sys.exit(1)  # Warning: signals issues but allows edit to proceed


if __name__ == "__main__":
    # Entry point: Execute the main hook logic when run as a script
    # This is called by Claude Code when the hook is triggered
    main()
