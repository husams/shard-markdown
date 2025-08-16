"""Tests for CLI pattern matching utilities."""


# Pattern matching tests require Python 3.10+

from shard_markdown.cli.patterns import (
    CommandPattern,
    ConfigPattern,
    ErrorPattern,
    ExitCode,
    create_command_pattern,
    create_config_pattern,
    create_error_pattern,
    match_config_type,
    match_error_category,
)
from shard_markdown.utils.errors import (
    ChromaDBError,
    ConfigurationError,
    InputValidationError,
    NetworkError,
    ProcessingError,
)


class TestCommandPattern:
    """Test command pattern matching utilities."""

    def test_create_process_file_pattern(self) -> None:
        """Test creating process file command pattern."""
        pattern = create_command_pattern("process", "file")

        assert isinstance(pattern, CommandPattern)
        assert pattern.command == "process"
        assert pattern.subcommand == "file"
        assert pattern.handler_name == "handle_file_processing"

    def test_create_collections_list_pattern(self) -> None:
        """Test creating collections list command pattern."""
        pattern = create_command_pattern("collections", "list")

        assert isinstance(pattern, CommandPattern)
        assert pattern.command == "collections"
        assert pattern.subcommand == "list"
        assert pattern.handler_name == "handle_collection_listing"

    def test_create_query_search_pattern(self) -> None:
        """Test creating query search command pattern."""
        pattern = create_command_pattern("query", "search")

        assert isinstance(pattern, CommandPattern)
        assert pattern.command == "query"
        assert pattern.subcommand == "search"
        assert pattern.handler_name == "handle_search_query"

    def test_create_config_show_pattern(self) -> None:
        """Test creating config show command pattern."""
        pattern = create_command_pattern("config", "show")

        assert isinstance(pattern, CommandPattern)
        assert pattern.command == "config"
        assert pattern.subcommand == "show"
        assert pattern.handler_name == "handle_config_display"

    def test_create_unknown_pattern_returns_none(self) -> None:
        """Test creating unknown command pattern returns None."""
        pattern = create_command_pattern("unknown", "command")

        assert pattern is None

    def test_command_pattern_equality(self) -> None:
        """Test command pattern equality comparison."""
        pattern1 = create_command_pattern("process", "file")
        pattern2 = create_command_pattern("process", "file")
        pattern3 = create_command_pattern("process", "directory")

        assert pattern1 == pattern2
        assert pattern1 != pattern3

    def test_command_pattern_repr(self) -> None:
        """Test command pattern string representation."""
        pattern = create_command_pattern("process", "file")

        repr_str = repr(pattern)
        assert "process" in repr_str
        assert "file" in repr_str


class TestConfigPattern:
    """Test configuration pattern matching utilities."""

    def test_create_integer_config_pattern(self) -> None:
        """Test creating integer configuration pattern."""
        pattern = create_config_pattern("chunk_size")

        assert isinstance(pattern, ConfigPattern)
        assert pattern.key == "chunk_size"
        assert pattern.type_name == "integer"
        assert pattern.validator is not None

    def test_create_float_config_pattern(self) -> None:
        """Test creating float configuration pattern."""
        pattern = create_config_pattern("overlap_percentage")

        assert isinstance(pattern, ConfigPattern)
        assert pattern.key == "overlap_percentage"
        assert pattern.type_name == "float"
        assert pattern.validator is not None

    def test_create_boolean_config_pattern(self) -> None:
        """Test creating boolean configuration pattern."""
        pattern = create_config_pattern("enable_async")

        assert isinstance(pattern, ConfigPattern)
        assert pattern.key == "enable_async"
        assert pattern.type_name == "boolean"
        assert pattern.validator is not None

    def test_create_string_config_pattern(self) -> None:
        """Test creating string configuration pattern."""
        pattern = create_config_pattern("chromadb_host")

        assert isinstance(pattern, ConfigPattern)
        assert pattern.key == "chromadb_host"
        assert pattern.type_name == "string"
        assert pattern.validator is not None

    def test_create_unknown_config_pattern(self) -> None:
        """Test creating unknown configuration pattern."""
        pattern = create_config_pattern("unknown_key")

        assert isinstance(pattern, ConfigPattern)
        assert pattern.key == "unknown_key"
        assert pattern.type_name == "string"
        assert pattern.validator is not None

    def test_match_config_type_integer(self) -> None:
        """Test matching integer configuration type."""
        type_name = match_config_type("chunk_size")
        assert type_name == "integer"

    def test_match_config_type_float(self) -> None:
        """Test matching float configuration type."""
        type_name = match_config_type("similarity_threshold")
        assert type_name == "float"

    def test_match_config_type_boolean(self) -> None:
        """Test matching boolean configuration type."""
        type_name = match_config_type("debug_mode")
        assert type_name == "boolean"

    def test_match_config_type_string(self) -> None:
        """Test matching string configuration type."""
        type_name = match_config_type("log_level")
        assert type_name == "string"

    def test_match_config_type_unknown(self) -> None:
        """Test matching unknown configuration type."""
        type_name = match_config_type("unknown_config")
        assert type_name == "string"


class TestErrorPattern:
    """Test error pattern matching utilities."""

    def test_create_file_access_error_pattern(self) -> None:
        """Test creating file access error pattern."""
        error = FileNotFoundError("File not found")
        pattern = create_error_pattern(error)

        assert isinstance(pattern, ErrorPattern)
        assert pattern.category == "FILE_ACCESS"
        assert pattern.exit_code == ExitCode.FILE_ACCESS_ERROR
        assert pattern.recovery_strategy == "skip_and_continue"

    def test_create_permission_error_pattern(self) -> None:
        """Test creating permission error pattern."""
        error = PermissionError("Permission denied")
        pattern = create_error_pattern(error)

        assert isinstance(pattern, ErrorPattern)
        assert pattern.category == "PERMISSION"
        assert pattern.exit_code == ExitCode.PERMISSION_ERROR
        assert pattern.recovery_strategy == "suggest_fix"

    def test_create_processing_error_pattern(self) -> None:
        """Test creating processing error pattern."""
        error = ProcessingError("Processing failed")
        pattern = create_error_pattern(error)

        assert isinstance(pattern, ErrorPattern)
        assert pattern.category == "PROCESSING"
        assert pattern.exit_code == ExitCode.PROCESSING_ERROR
        assert pattern.recovery_strategy == "retry_with_backoff"

    def test_create_database_error_pattern(self) -> None:
        """Test creating database error pattern."""
        error = ChromaDBError("Database connection failed")
        pattern = create_error_pattern(error)

        assert isinstance(pattern, ErrorPattern)
        assert pattern.category == "DATABASE"
        assert pattern.exit_code == ExitCode.DATABASE_ERROR
        assert pattern.recovery_strategy == "retry_with_backoff"

    def test_create_validation_error_pattern(self) -> None:
        """Test creating validation error pattern."""
        error = InputValidationError("Invalid input")
        pattern = create_error_pattern(error)

        assert isinstance(pattern, ErrorPattern)
        assert pattern.category == "VALIDATION"
        assert pattern.exit_code == ExitCode.VALIDATION_ERROR
        assert pattern.recovery_strategy == "suggest_fix"

    def test_create_config_error_pattern(self) -> None:
        """Test creating configuration error pattern."""
        error = ConfigurationError("Invalid configuration")
        pattern = create_error_pattern(error)

        assert isinstance(pattern, ErrorPattern)
        assert pattern.category == "CONFIG"
        assert pattern.exit_code == ExitCode.CONFIG_ERROR
        assert pattern.recovery_strategy == "reset_to_defaults"

    def test_create_unknown_error_pattern(self) -> None:
        """Test creating unknown error pattern."""
        error = RuntimeError("Unknown error")
        pattern = create_error_pattern(error)

        assert isinstance(pattern, ErrorPattern)
        assert pattern.category == "UNKNOWN"
        assert pattern.exit_code == ExitCode.GENERAL_ERROR
        assert pattern.recovery_strategy == "abort"

    def test_match_error_category_file_errors(self) -> None:
        """Test matching file-related error categories."""
        assert match_error_category(FileNotFoundError()) == "FILE_ACCESS"
        assert match_error_category(IsADirectoryError()) == "FILE_ACCESS"
        assert match_error_category(PermissionError()) == "PERMISSION"

    def test_match_error_category_system_errors(self) -> None:
        """Test matching system-related error categories."""
        assert match_error_category(ProcessingError("test")) == "PROCESSING"
        assert match_error_category(ChromaDBError("test")) == "DATABASE"
        assert match_error_category(NetworkError("test")) == "DATABASE"

    def test_match_error_category_validation_errors(self) -> None:
        """Test matching validation error categories."""
        assert match_error_category(InputValidationError("test")) == "VALIDATION"
        assert match_error_category(ValueError("test")) == "VALIDATION"

    def test_match_error_category_config_errors(self) -> None:
        """Test matching configuration error categories."""
        assert match_error_category(ConfigurationError("test")) == "CONFIG"

    def test_match_error_category_unknown_errors(self) -> None:
        """Test matching unknown error categories."""
        assert match_error_category(RuntimeError("test")) == "UNKNOWN"
        assert match_error_category(Exception("test")) == "UNKNOWN"


class TestExitCode:
    """Test exit code enumeration."""

    def test_exit_code_values(self) -> None:
        """Test exit code integer values."""
        assert int(ExitCode.SUCCESS) == 0
        assert int(ExitCode.GENERAL_ERROR) == 1
        assert int(ExitCode.FILE_ACCESS_ERROR) == 2
        assert int(ExitCode.PERMISSION_ERROR) == 3
        assert int(ExitCode.PROCESSING_ERROR) == 4
        assert int(ExitCode.DATABASE_ERROR) == 5
        assert int(ExitCode.VALIDATION_ERROR) == 6
        assert int(ExitCode.CONFIG_ERROR) == 7

    def test_exit_code_uniqueness(self) -> None:
        """Test that all exit codes are unique."""
        exit_codes = [
            ExitCode.SUCCESS,
            ExitCode.GENERAL_ERROR,
            ExitCode.FILE_ACCESS_ERROR,
            ExitCode.PERMISSION_ERROR,
            ExitCode.PROCESSING_ERROR,
            ExitCode.DATABASE_ERROR,
            ExitCode.VALIDATION_ERROR,
            ExitCode.CONFIG_ERROR,
        ]

        assert len(exit_codes) == len(set(exit_codes))


class TestPatternMatching:
    """Test comprehensive pattern matching scenarios."""

    def test_complex_command_pattern_matching(self) -> None:
        """Test complex command pattern matching scenarios."""
        # Test all valid command combinations
        valid_patterns = [
            ("process", "file"),
            ("process", "directory"),
            ("collections", "list"),
            ("collections", "create"),
            ("collections", "delete"),
            ("query", "search"),
            ("query", "similar"),
            ("config", "show"),
            ("config", "set"),
        ]

        for command, subcommand in valid_patterns:
            pattern = create_command_pattern(command, subcommand)
            assert pattern is not None
            assert pattern.command == command
            assert pattern.subcommand == subcommand

    def test_exhaustive_config_type_matching(self) -> None:
        """Test exhaustive configuration type matching."""
        # Integer config keys
        integer_keys = [
            "chunk_size",
            "max_chunk_size",
            "min_chunk_size",
            "batch_size",
            "timeout",
            "port",
            "max_retries",
        ]
        for key in integer_keys:
            assert match_config_type(key) == "integer"

        # Float config keys
        float_keys = [
            "overlap_percentage",
            "similarity_threshold",
            "confidence_threshold",
            "retry_backoff",
            "timeout_multiplier",
        ]
        for key in float_keys:
            assert match_config_type(key) == "float"

        # Boolean config keys
        boolean_keys = [
            "enable_async",
            "preserve_headers",
            "debug_mode",
            "auto_retry",
            "verbose",
            "recursive",
            "ssl",
        ]
        for key in boolean_keys:
            assert match_config_type(key) == "boolean"

        # String config keys
        string_keys = [
            "chromadb_host",
            "log_level",
            "output_format",
            "embedding_model",
            "auth_token",
            "collection_name",
        ]
        for key in string_keys:
            assert match_config_type(key) == "string"

    def test_comprehensive_error_pattern_matching(self) -> None:
        """Test comprehensive error pattern matching."""
        # Test all error types have proper patterns
        error_classes = [
            (FileNotFoundError, "FILE_ACCESS"),
            (PermissionError, "PERMISSION"),
            (ProcessingError, "PROCESSING"),
            (ChromaDBError, "DATABASE"),
            (InputValidationError, "VALIDATION"),
            (ConfigurationError, "CONFIG"),
            (RuntimeError, "UNKNOWN"),
        ]

        for error_class, expected_category in error_classes:
            if error_class in [
                ProcessingError,
                ChromaDBError,
                InputValidationError,
                ConfigurationError,
            ]:
                error = error_class("test message")
            else:
                error = error_class("test message")

            pattern = create_error_pattern(error)
            assert pattern.category == expected_category
            assert isinstance(pattern.exit_code, int)
            assert pattern.recovery_strategy in [
                "skip_and_continue",
                "suggest_fix",
                "retry_with_backoff",
                "reset_to_defaults",
                "abort",
            ]
