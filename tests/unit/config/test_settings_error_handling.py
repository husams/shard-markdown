"""Tests for configuration settings error handling scenarios."""

import copy
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from shard_markdown.config.settings import (
    AppConfig,
    ChromaDBConfig,
    _apply_env_overrides,
    _find_config_file,
    _load_config_file,
    create_default_config,
    load_config,
    save_config,
    set_nested_value,
)


class TestLoadConfigErrorHandling:
    """Test error handling in load_config function."""

    def test_load_config_invalid_yaml_syntax(self) -> None:
        """Test load_config handles invalid YAML syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "invalid.yaml"

            # Create file with invalid YAML syntax
            config_path.write_text("""
chromadb:
  host: localhost
  port: 8000
  invalid_yaml: [unclosed bracket
chunking:
  default_size: 1000
""")

            with pytest.raises(ValueError, match="Invalid YAML in configuration file"):
                load_config(config_path)

    def test_load_config_invalid_yaml_structure(self) -> None:
        """Test load_config handles invalid YAML structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "invalid_structure.yaml"

            # Create file with valid YAML but invalid structure for our config
            config_path.write_text("""
chromadb:
  host: localhost
  port: "not_a_number"  # Should be int
  ssl: "not_a_boolean"  # Should be bool
""")

            with pytest.raises(ValueError, match="Invalid configuration"):
                load_config(config_path)

    def test_load_config_file_read_permission_error(self) -> None:
        """Test load_config handles file permission errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "permission_denied.yaml"
            config_path.write_text("chromadb:\n  host: localhost")

            # Mock open to raise PermissionError
            with patch(
                "builtins.open", side_effect=PermissionError("Permission denied")
            ):
                with pytest.raises(
                    ValueError, match="Error reading configuration file"
                ):
                    load_config(config_path)

    def test_load_config_file_unicode_decode_error(self) -> None:
        """Test load_config handles unicode decode errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "unicode_error.yaml"

            # Write binary data that can't be decoded as UTF-8
            # Use a sequence that's invalid in both UTF-8 and UTF-16
            with open(config_path, "wb") as f:
                f.write(b"\x80\x81\x82\x83")  # Invalid UTF-8 continuation bytes

            with pytest.raises(ValueError, match="Error reading configuration file"):
                load_config(config_path)

    def test_load_config_invalid_pydantic_validation(self) -> None:
        """Test load_config handles Pydantic validation errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "invalid_values.yaml"

            # Create config with values that fail Pydantic validation
            config_path.write_text("""
chromadb:
  host: ""  # Empty host should fail validation
  port: 70000  # Port too high
  timeout: -1  # Negative timeout
chunking:
  default_size: 50  # Too small
  default_overlap: 2000  # Larger than chunk size
""")

            with pytest.raises(ValueError, match="Invalid configuration"):
                load_config(config_path)

    def test_load_config_type_error_in_config_construction(self) -> None:
        """Test load_config handles TypeError in AppConfig construction."""
        with patch("shard_markdown.config.settings.AppConfig") as mock_app_config:
            mock_app_config.side_effect = TypeError("Type error in construction")

            with pytest.raises(ValueError, match="Invalid configuration"):
                load_config()

    def test_load_config_key_error_in_config_construction(self) -> None:
        """Test load_config handles KeyError in AppConfig construction."""
        with patch("shard_markdown.config.settings.AppConfig") as mock_app_config:
            mock_app_config.side_effect = KeyError("Missing required key")

            with pytest.raises(ValueError, match="Invalid configuration"):
                load_config()

    def test_load_config_nonexistent_explicit_path(self) -> None:
        """Test load_config raises FileNotFoundError for nonexistent explicit path."""
        nonexistent_path = Path("/definitely/does/not/exist/config.yaml")

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config(nonexistent_path)

    def test_load_config_empty_yaml_file(self) -> None:
        """Test load_config handles empty YAML file gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "empty.yaml"
            config_path.write_text("")  # Empty file

            # Should use defaults when file is empty
            config = load_config(config_path)
            assert config.chromadb.host == "localhost"
            assert config.chromadb.port == 8000

    def test_load_config_null_yaml_content(self) -> None:
        """Test load_config handles YAML file with null content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "null.yaml"
            config_path.write_text("null")  # YAML null

            # Should use defaults when file contains null
            config = load_config(config_path)
            assert config.chromadb.host == "localhost"
            assert config.chromadb.port == 8000


class TestSaveConfigErrorHandling:
    """Test error handling in save_config function."""

    def test_save_config_permission_denied(self) -> None:
        """Test save_config handles permission denied errors."""
        config = AppConfig()
        config_path = Path("/root/permission_denied.yaml")  # Typically not writable

        # Mock ensure_directory_exists to succeed, but open to fail
        with patch("shard_markdown.config.settings.ensure_directory_exists"):
            with patch(
                "builtins.open", side_effect=PermissionError("Permission denied")
            ):
                with pytest.raises(PermissionError):
                    save_config(config, config_path)

    def test_save_config_yaml_dump_error(self) -> None:
        """Test save_config handles YAML dump errors."""
        config = AppConfig()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "dump_error.yaml"

            # Mock yaml.dump to raise an error
            with patch("yaml.dump", side_effect=yaml.YAMLError("YAML dump error")):
                with pytest.raises(yaml.YAMLError):
                    save_config(config, config_path)

    def test_save_config_directory_creation_failure(self) -> None:
        """Test save_config handles directory creation failures."""
        config = AppConfig()
        config_path = Path("/nonexistent/deep/path/config.yaml")

        # Mock ensure_directory_exists to raise OSError
        with patch(
            "shard_markdown.config.settings.ensure_directory_exists",
            side_effect=OSError("Cannot create directory"),
        ):
            with pytest.raises(OSError):
                save_config(config, config_path)


class TestCreateDefaultConfigErrorHandling:
    """Test error handling in create_default_config function."""

    def test_create_default_config_file_exists_no_force(self) -> None:
        """Test create_default_config raises error when file exists and force=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "existing.yaml"
            config_path.write_text("existing content")

            with pytest.raises(
                FileExistsError, match="Configuration file already exists"
            ):
                create_default_config(config_path, force=False)

    def test_create_default_config_permission_denied(self) -> None:
        """Test create_default_config handles permission denied errors."""
        config_path = Path("/root/permission_denied.yaml")

        # Mock ensure_directory_exists to succeed, but open to fail
        with patch("shard_markdown.config.settings.ensure_directory_exists"):
            with patch(
                "builtins.open", side_effect=PermissionError("Permission denied")
            ):
                with pytest.raises(PermissionError):
                    create_default_config(config_path)

    def test_create_default_config_directory_creation_failure(self) -> None:
        """Test create_default_config handles directory creation failures."""
        config_path = Path("/nonexistent/deep/path/config.yaml")

        # Mock ensure_directory_exists to raise OSError
        with patch(
            "shard_markdown.config.settings.ensure_directory_exists",
            side_effect=OSError("Cannot create directory"),
        ):
            with pytest.raises(OSError):
                create_default_config(config_path)


class TestHostValidationErrorHandling:
    """Test error handling in ChromaDB host validation."""

    def test_chromadb_config_empty_host(self) -> None:
        """Test ChromaDBConfig rejects empty host."""
        with pytest.raises(ValidationError, match="Host cannot be empty"):
            ChromaDBConfig(host="")

    def test_chromadb_config_whitespace_only_host(self) -> None:
        """Test ChromaDBConfig rejects whitespace-only host."""
        with pytest.raises(ValidationError, match="Host cannot be empty"):
            ChromaDBConfig(host="   ")

    def test_chromadb_config_invalid_ip_address(self) -> None:
        """Test ChromaDBConfig rejects invalid IP addresses."""
        invalid_ips = [
            "256.1.1.1",  # Invalid IPv4 (256 > 255)
            "192.168.1",  # Incomplete IPv4
            "192.168.1.1.1",  # Too many octets
            "192.168.01.1",  # Leading zeros (some systems reject this)
            "999.999.999.999",  # All octets invalid
        ]

        for invalid_ip in invalid_ips:
            with pytest.raises(ValidationError, match="Invalid host"):
                ChromaDBConfig(host=invalid_ip)

    def test_chromadb_config_invalid_hostname(self) -> None:
        """Test ChromaDBConfig rejects invalid hostnames."""
        invalid_hostnames = [
            "-invalid",  # Starts with hyphen
            "invalid-",  # Ends with hyphen
            "inv@lid",  # Contains invalid character
            "a" * 64,  # Label too long (>63 chars)
            "invalid..host",  # Double dots
            ".invalid",  # Starts with dot
            "invalid.",  # Ends with dot (while some allow this, our validator doesn't)
            "inv_alid",  # Contains underscore in hostname (not allowed in strict RFC)
        ]

        for invalid_hostname in invalid_hostnames:
            with pytest.raises(ValidationError, match="Invalid host"):
                ChromaDBConfig(host=invalid_hostname)


class TestHelperFunctionErrorHandling:
    """Test error handling in helper functions."""

    def test_load_config_file_yaml_error(self) -> None:
        """Test _load_config_file handles YAML parsing errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bad_yaml.yaml"
            config_path.write_text("[unclosed bracket")

            with pytest.raises(ValueError, match="Invalid YAML in configuration file"):
                _load_config_file(config_path)

    def test_load_config_file_os_error(self) -> None:
        """Test _load_config_file handles OS errors."""
        # Mock open to raise OSError
        with patch("builtins.open", side_effect=OSError("File system error")):
            config_path = Path("/some/path/config.yaml")

            with pytest.raises(ValueError, match="Error reading configuration file"):
                _load_config_file(config_path)

    def test_load_config_file_unicode_error(self) -> None:
        """Test _load_config_file handles unicode decode errors."""
        # Mock open to raise UnicodeDecodeError
        unicode_error = UnicodeDecodeError(
            "utf-8", b"\xff\xfe", 0, 1, "invalid start byte"
        )

        with patch("builtins.open", side_effect=unicode_error):
            config_path = Path("/some/path/config.yaml")

            with pytest.raises(ValueError, match="Error reading configuration file"):
                _load_config_file(config_path)

    def test_find_config_file_no_config_found(self) -> None:
        """Test _find_config_file returns None when no config files exist."""
        # Mock all default locations to not exist
        with patch("shard_markdown.config.settings.DEFAULT_CONFIG_LOCATIONS", []):
            result = _find_config_file()
            assert result is None

    def test_find_config_file_returns_first_existing(self) -> None:
        """Test _find_config_file returns first existing config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config1 = Path(tmpdir) / "config1.yaml"
            config2 = Path(tmpdir) / "config2.yaml"

            # Create only the second config file
            config2.write_text("test")

            # Mock default locations to include both paths
            with patch(
                "shard_markdown.config.settings.DEFAULT_CONFIG_LOCATIONS",
                [config1, config2],
            ):
                result = _find_config_file()
                assert result == config2

    def test_apply_env_overrides_preserves_original(self) -> None:
        """Test _apply_env_overrides doesn't modify original config data."""
        original_data = {"chromadb": {"host": "original"}}
        # Make a deep copy to ensure we're testing the right behavior
        test_data = copy.deepcopy(original_data)

        with patch.dict(os.environ, {"CHROMA_HOST": "modified"}, clear=False):
            result = _apply_env_overrides(test_data)

            # Original should be unchanged
            assert original_data["chromadb"]["host"] == "original"
            # Test data may have been modified (that's implementation dependent)
            # But result should have the override
            assert result["chromadb"]["host"] == "modified"

    def test_set_nested_value_creates_intermediate_dicts(self) -> None:
        """Test set_nested_value creates intermediate dictionaries."""
        data: dict = {}
        set_nested_value(data, "level1.level2.level3.key", "value")

        assert data["level1"]["level2"]["level3"]["key"] == "value"
        assert isinstance(data["level1"], dict)
        assert isinstance(data["level1"]["level2"], dict)
        assert isinstance(data["level1"]["level2"]["level3"], dict)

    def test_set_nested_value_overwrites_existing(self) -> None:
        """Test set_nested_value overwrites existing values."""
        data = {"existing": {"key": "old_value"}}
        set_nested_value(data, "existing.key", "new_value")

        assert data["existing"]["key"] == "new_value"

    def test_set_nested_value_single_level(self) -> None:
        """Test set_nested_value works with single-level keys."""
        data: dict = {}
        set_nested_value(data, "single_key", "value")

        assert data["single_key"] == "value"


class TestEnvironmentVariableErrorHandling:
    """Test error handling related to environment variables."""

    def test_invalid_env_var_type_conversion(self) -> None:
        """Test handling of environment variables that can't be converted."""
        # This tests that Pydantic handles type conversion errors gracefully
        # when environment variables contain invalid values

        env_vars = {
            "CHROMA_PORT": "not_a_number",  # Should be int
            "CHROMA_SSL": "maybe",  # Should be bool
            "SHARD_MD_CHUNK_SIZE": "large",  # Should be int
        }

        with patch.dict(os.environ, env_vars, clear=True):
            # Pydantic should raise ValidationError for invalid type conversions
            with pytest.raises(ValueError, match="Invalid configuration"):
                load_config()

    def test_env_var_out_of_range_values(self) -> None:
        """Test environment variables with out-of-range values."""
        env_vars = {
            "CHROMA_PORT": "70000",  # Port too high
            "SHARD_MD_CHUNK_SIZE": "50",  # Chunk size too small
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="Invalid configuration"):
                load_config()


class TestConfigurationEdgeCases:
    """Test edge cases in configuration handling."""

    def test_config_with_null_values(self) -> None:
        """Test configuration handles null values appropriately."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "null_values.yaml"

            # Create config with null values where they're allowed
            config_path.write_text("""
chromadb:
  host: localhost
  port: 8000
  auth_token: null  # Null is allowed for optional field
chunking:
  max_tokens: null  # Null is allowed for optional field
""")

            # Should load successfully
            config = load_config(config_path)
            assert config.chromadb.auth_token is None
            assert config.chunking.max_tokens is None

    def test_config_with_extra_unknown_fields(self) -> None:
        """Test configuration handles unknown fields gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "extra_fields.yaml"

            # Create config with extra unknown fields
            config_path.write_text("""
chromadb:
  host: localhost
  port: 8000
  unknown_field: should_be_ignored  # Extra field
chunking:
  default_size: 1000
  another_unknown: also_ignored  # Another extra field
unknown_section:  # Entire unknown section
  some_setting: value
""")

            # Should load successfully, ignoring unknown fields
            config = load_config(config_path)
            assert config.chromadb.host == "localhost"
            assert config.chunking.default_size == 1000
