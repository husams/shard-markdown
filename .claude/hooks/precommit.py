#!/usr/bin/env python3
"""Claude Code Hook: Pre-commit Auto-formatting.

============================================
This hook runs as a PostToolUse hook for Write/Edit/MultiEdit tools.
It automatically formats and lints Python files using ruff.
"""

# TOOL BEHAVIOR:
# ==============
# 1. SELF-FORMATTING: This hook automatically formats itself when edited!
#    - Any edits to this .py file trigger the hook recursively
#    - Ruff format runs and reformats the code in real-time
#
# 2. OUTPUT BEHAVIOR:
#    - stdout: Success messages only (visible to user)
#    - Never blocks edits or returns errors
#
# 3. EXIT CODE STRATEGY:
#    - Always returns 0 (success) - never blocks or fails
#
# 4. PROCESSING PIPELINE:
#    - Format (beautify) → Lint with auto-fix
#    - Both operations are non-blocking
#
# 5. DEBUGGING:
#    - All operations logged to ~/.claude_logs/precommit_hook_YYYYMMDD.log

import json
import logging
import os
import subprocess  # nosec B404
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
        result = subprocess.run(  # nosec B603
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


def _format_python_file(file_path: str, logger: logging.Logger) -> None:
    """Format a Python file using ruff formatter.

    Args:
        file_path: Path to the Python file to format
        logger: Logger instance for status tracking

    Note:
        - Uses 'uv run ruff format' command
        - Always succeeds (non-blocking)
    """
    logger.info(f"Formatting Python file: {file_path}")
    success, output = _run_command(["uv", "run", "ruff", "format", file_path], logger)

    if success:
        print(f"✓ Ruff formatted: {file_path}")
        logger.info(f"Successfully formatted: {file_path}")
    else:
        # Still log but don't show errors to user
        logger.info(f"Ruff format attempt completed for: {file_path}")


def _lint_python_file(file_path: str, logger: logging.Logger) -> None:
    """Lint and auto-fix Python file using ruff linter.

    Args:
        file_path: Path to the Python file to lint
        logger: Logger instance for status tracking

    Note:
        - Uses 'uv run ruff check --fix' command
        - Automatically fixes issues where possible
        - Always succeeds (non-blocking)
    """
    logger.info(f"Linting Python file: {file_path}")
    success, output = _run_command(
        ["uv", "run", "ruff", "check", "--fix", file_path], logger
    )

    if success:
        print(f"✓ Ruff linted: {file_path}")
        logger.info(f"Successfully linted: {file_path}")
    else:
        # Still log but don't show errors to user
        logger.info(f"Ruff check attempt completed for: {file_path}")


def main() -> None:
    """Main hook entry point that runs auto-formatting.

    This function:
    1. Sets up logging and parses hook input data
    2. Identifies the target Python file from various sources
    3. Runs format and lint operations (both non-blocking)
    4. Always exits successfully (never blocks or returns error)
    """
    # INITIALIZATION: Setup logging infrastructure first
    logger = _setup_logging()
    logger.info("=" * 60)
    logger.info("Pre-commit auto-formatting hook started")

    # PARSE INPUT: Read and validate the JSON input from Claude Code
    try:
        input_data = json.load(sys.stdin)

        # Extract and log the session ID for debugging
        session_id = input_data.get("session_id", "UNKNOWN")
        logger.info(f"SESSION ID: {session_id}")

        # Log the input data for debugging
        logger.info(f"Received hook input data: {json.dumps(input_data, indent=2)}")
    except json.JSONDecodeError as e:
        # Even on JSON error, don't block - just log and exit successfully
        logger.info(f"JSON parse issue (non-blocking): {e}")
        sys.exit(0)  # Always exit successfully

    # TOOL VALIDATION: Ensure this hook should run for this tool
    tool_name = input_data.get("tool_name", "")
    logger.info(f"Tool name: {tool_name}")

    # Exit early if not a file modification tool
    if tool_name not in ["Write", "Edit", "MultiEdit"]:
        logger.info(f"Skipping non-file tool: {tool_name}")
        sys.exit(0)  # Graceful exit

    # FILE PATH DETECTION: Multiple strategies to find the target file

    # Strategy 1: Check tool result (most common location)
    tool_result = input_data.get("tool_result", {})
    file_path = tool_result.get("file_path")
    logger.info(f"File path from tool result: {file_path}")

    # Strategy 2: Fallback to environment variable
    if not file_path:
        file_path = os.environ.get("CLAUDE_TOOL_RESULT_FILE_PATH")
        logger.info(f"File path from environment: {file_path}")

    # Strategy 3: Check tool input as final fallback
    if not file_path:
        tool_input = input_data.get("tool_input", {})
        file_path = tool_input.get("file_path")
        logger.info(f"File path from tool input: {file_path}")

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
    print(f"Auto-formatting Python file: {file_path}")

    # STEP 1: Format the file (non-blocking)
    _format_python_file(file_path, logger)

    # STEP 2: Lint and auto-fix issues (non-blocking)
    _lint_python_file(file_path, logger)

    # Always exit successfully - never block or return error
    logger.info("Hook completed successfully")
    sys.exit(0)  # Always success


if __name__ == "__main__":
    # Entry point: Execute the main hook logic when run as a script
    # This is called by Claude Code when the hook is triggered
    main()
