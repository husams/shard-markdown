"""Pattern matching utilities for CLI commands and error handling."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from ..utils.errors import (
    ChromaDBError,
    ConfigurationError,
    FileSystemError,
    InputValidationError,
    NetworkError,
    ProcessingError,
)


class ExitCode(IntEnum):
    """Exit codes for CLI operations."""

    SUCCESS = 0
    GENERAL_ERROR = 1
    FILE_ACCESS_ERROR = 2
    PERMISSION_ERROR = 3
    PROCESSING_ERROR = 4
    DATABASE_ERROR = 5
    VALIDATION_ERROR = 6
    CONFIG_ERROR = 7


@dataclass(frozen=True)
class CommandPattern:
    """Represents a command pattern for routing."""

    command: str
    subcommand: str
    handler_name: str

    def __eq__(self, other: object) -> bool:
        """Check equality with another CommandPattern."""
        if not isinstance(other, CommandPattern):
            return False
        return (
            self.command == other.command
            and self.subcommand == other.subcommand
            and self.handler_name == other.handler_name
        )

    def __repr__(self) -> str:
        """String representation of the pattern."""
        return (
            f"CommandPattern(command='{self.command}', subcommand='{self.subcommand}')"
        )


class ConfigValidator(ABC):
    """Abstract base class for configuration validators."""

    @abstractmethod
    def validate(self, value: str) -> Any:
        """Validate and convert configuration value.

        Args:
            value: String value to validate and convert

        Returns:
            Converted value with appropriate type

        Raises:
            ValueError: If value cannot be validated/converted
        """


class IntegerValidator(ConfigValidator):
    """Validator for integer configuration values."""

    def validate(self, value: str) -> int:
        """Validate and convert string to integer."""
        try:
            return int(value)
        except ValueError as e:
            raise ValueError(f"Invalid integer value: '{value}'") from e


class FloatValidator(ConfigValidator):
    """Validator for float configuration values."""

    def validate(self, value: str) -> float:
        """Validate and convert string to float."""
        try:
            return float(value)
        except ValueError as e:
            raise ValueError(f"Invalid float value: '{value}'") from e


class BooleanValidator(ConfigValidator):
    """Validator for boolean configuration values."""

    def validate(self, value: str) -> bool:
        """Validate and convert string to boolean."""
        lower_value = value.lower()
        if lower_value in ("true", "yes", "1", "on", "enable", "enabled"):
            return True
        elif lower_value in ("false", "no", "0", "off", "disable", "disabled"):
            return False
        else:
            raise ValueError(f"Invalid boolean value: '{value}'")


class StringValidator(ConfigValidator):
    """Validator for string configuration values."""

    def validate(self, value: str) -> str:
        """Validate and return string value."""
        return value


@dataclass(frozen=True)
class ConfigPattern:
    """Represents a configuration pattern for type validation."""

    key: str
    type_name: str
    validator: ConfigValidator

    def validate(self, value: str) -> Any:
        """Validate and convert the configuration value."""
        return self.validator.validate(value)


@dataclass(frozen=True)
class ErrorPattern:
    """Represents an error pattern for categorization and recovery."""

    category: str
    exit_code: ExitCode
    recovery_strategy: str
    message_template: str


def create_command_pattern(command: str, subcommand: str) -> CommandPattern | None:
    """Create a command pattern using pattern matching.

    Args:
        command: The main command name
        subcommand: The subcommand name

    Returns:
        CommandPattern instance or None if unknown pattern
    """
    match (command, subcommand):
        case ("process", "file"):
            return CommandPattern(command, subcommand, "handle_file_processing")
        case ("process", "directory"):
            return CommandPattern(command, subcommand, "handle_directory_processing")
        case ("collections", "list"):
            return CommandPattern(command, subcommand, "handle_collection_listing")
        case ("collections", "create"):
            return CommandPattern(command, subcommand, "handle_collection_creation")
        case ("collections", "delete"):
            return CommandPattern(command, subcommand, "handle_collection_deletion")
        case ("query", "search"):
            return CommandPattern(command, subcommand, "handle_search_query")
        case ("query", "similar"):
            return CommandPattern(command, subcommand, "handle_similarity_search")
        case ("config", "show"):
            return CommandPattern(command, subcommand, "handle_config_display")
        case ("config", "set"):
            return CommandPattern(command, subcommand, "handle_config_update")
        case _:
            return None


def create_config_pattern(key: str) -> ConfigPattern:
    """Create a configuration pattern using pattern matching.

    Args:
        key: The configuration key

    Returns:
        ConfigPattern instance with appropriate validator
    """
    type_name = match_config_type(key)
    validator = _get_config_validator(type_name)
    return ConfigPattern(key, type_name, validator)


def match_config_type(key: str) -> str:
    """Match configuration type using pattern matching.

    Args:
        key: The configuration key

    Returns:
        Type name as string
    """
    match key:
        # Integer configurations
        case (
            "chunk_size"
            | "max_chunk_size"
            | "min_chunk_size"
            | "batch_size"
            | "timeout"
            | "port"
            | "max_retries"
            | "backup_count"
            | "max_file_size"
        ):
            return "integer"

        # Float configurations
        case (
            "overlap_percentage"
            | "similarity_threshold"
            | "confidence_threshold"
            | "retry_backoff"
            | "timeout_multiplier"
        ):
            return "float"

        # Boolean configurations
        case (
            "enable_async"
            | "preserve_headers"
            | "debug_mode"
            | "auto_retry"
            | "verbose"
            | "recursive"
            | "ssl"
            | "respect_boundaries"
            | "include_frontmatter"
            | "include_path_metadata"
        ):
            return "boolean"

        # String configurations
        case (
            "chromadb_host"
            | "log_level"
            | "output_format"
            | "embedding_model"
            | "auth_token"
            | "collection_name"
            | "method"
            | "pattern"
            | "format"
        ):
            return "string"

        case _:
            return "string"  # Default to string for unknown keys


def create_error_pattern(error: Exception) -> ErrorPattern:
    """Create an error pattern using pattern matching.

    Args:
        error: The exception to categorize

    Returns:
        ErrorPattern instance with appropriate categorization
    """
    category = match_error_category(error)

    match category:
        case "FILE_ACCESS":
            return ErrorPattern(
                category,
                ExitCode.FILE_ACCESS_ERROR,
                "skip_and_continue",
                "File access error: {message}. Skipping file and continuing.",
            )
        case "PERMISSION":
            return ErrorPattern(
                category,
                ExitCode.PERMISSION_ERROR,
                "suggest_fix",
                "Permission error: {message}. Check file permissions.",
            )
        case "PROCESSING":
            return ErrorPattern(
                category,
                ExitCode.PROCESSING_ERROR,
                "retry_with_backoff",
                "Processing error: {message}. Retrying with backoff.",
            )
        case "DATABASE":
            return ErrorPattern(
                category,
                ExitCode.DATABASE_ERROR,
                "retry_with_backoff",
                "Database error: {message}. Retrying connection.",
            )
        case "VALIDATION":
            return ErrorPattern(
                category,
                ExitCode.VALIDATION_ERROR,
                "suggest_fix",
                "Validation error: {message}. Check input parameters.",
            )
        case "CONFIG":
            return ErrorPattern(
                category,
                ExitCode.CONFIG_ERROR,
                "reset_to_defaults",
                "Configuration error: {message}. Resetting to defaults.",
            )
        case _:
            return ErrorPattern(
                category,
                ExitCode.GENERAL_ERROR,
                "abort",
                "Unknown error: {message}. Aborting operation.",
            )


def match_error_category(error: Exception) -> str:
    """Match error category using pattern matching.

    Args:
        error: The exception to categorize

    Returns:
        Error category as string
    """
    match error:
        case FileNotFoundError() | IsADirectoryError() | FileExistsError():
            return "FILE_ACCESS"
        case PermissionError():
            return "PERMISSION"
        case ProcessingError() | FileSystemError():
            return "PROCESSING"
        case ChromaDBError() | NetworkError():
            return "DATABASE"
        case InputValidationError() | ValueError() | TypeError():
            return "VALIDATION"
        case ConfigurationError():
            return "CONFIG"
        case _:
            return "UNKNOWN"


def _get_config_validator(type_name: str) -> ConfigValidator:
    """Get validator instance for configuration type.

    Args:
        type_name: The type name

    Returns:
        Validator instance
    """
    match type_name:
        case "integer":
            return IntegerValidator()
        case "float":
            return FloatValidator()
        case "boolean":
            return BooleanValidator()
        case "string":
            return StringValidator()
        case _:
            return StringValidator()


# Legacy functions for backward compatibility with existing tests
def _validate_integer(value: str) -> int:
    """Legacy integer validator function."""
    return IntegerValidator().validate(value)


def _validate_float(value: str) -> float:
    """Legacy float validator function."""
    return FloatValidator().validate(value)


def _validate_boolean(value: str) -> bool:
    """Legacy boolean validator function."""
    return BooleanValidator().validate(value)


def _validate_string(value: str) -> str:
    """Legacy string validator function."""
    return StringValidator().validate(value)
