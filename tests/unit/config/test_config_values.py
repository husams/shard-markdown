"""Tests for configuration value handling, especially IP addresses."""

import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml

from shard_markdown.config.settings import (
    AppConfig,
    ChromaDBConfig,
    load_config,
    save_config,
    set_nested_value,
)


class TestConfigValueHandling:
    """Test configuration value handling without custom parsing."""

    def test_ip_address_preservation(self) -> None:
        """Test that IP addresses are preserved correctly."""
        test_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "255.255.255.255",
        ]

        for ip in test_ips:
            config = ChromaDBConfig(host=ip)
            assert config.host == ip, f"IP address {ip} was not preserved"

    def test_ipv6_address_preservation(self) -> None:
        """Test that IPv6 addresses are preserved correctly."""
        test_ips = [
            "::1",
            "2001:db8::1",
            "fe80::1",
        ]

        for ip in test_ips:
            config = ChromaDBConfig(host=ip)
            assert config.host == ip, f"IPv6 address {ip} was not preserved"

    def test_hostname_preservation(self) -> None:
        """Test that hostnames are preserved correctly."""
        test_hosts = [
            "localhost",
            "example.com",
            "db.internal.network",
            "api-server.local",
        ]

        for host in test_hosts:
            config = ChromaDBConfig(host=host)
            assert config.host == host, f"Hostname {host} was not preserved"

    def test_environment_variable_ip_address(self) -> None:
        """Test IP addresses from environment variables."""
        test_ip = "192.168.100.50"

        with patch.dict(os.environ, {"CHROMA_HOST": test_ip}, clear=False):
            config = load_config()
            assert config.chromadb.host == test_ip

    def test_environment_variable_types(self) -> None:
        """Test various types from environment variables."""
        env_vars = {
            "CHROMA_HOST": "10.20.30.40",
            "CHROMA_PORT": "9000",
            "CHROMA_SSL": "true",
            "SHARD_MD_CHUNK_SIZE": "1500",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = load_config()

            # IP address should be preserved as string
            assert config.chromadb.host == "10.20.30.40"
            assert isinstance(config.chromadb.host, str)

            # Port should be converted to int by Pydantic
            assert config.chromadb.port == 9000
            assert isinstance(config.chromadb.port, int)

            # Boolean should be converted by Pydantic
            assert config.chromadb.ssl is True
            assert isinstance(config.chromadb.ssl, bool)

            # Chunk size should be converted to int
            assert config.chunking.default_size == 1500
            assert isinstance(config.chunking.default_size, int)

    def test_yaml_config_ip_address(self) -> None:
        """Test IP addresses in YAML configuration files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Write config with IP address
            config_data = {
                "chromadb": {
                    "host": "172.31.0.1",
                    "port": 8080,
                }
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Load and verify - clear environment variables that might interfere
            clean_env = {
                k: v
                for k, v in os.environ.items()
                if not k.startswith(("CHROMA_", "SHARD_MD_"))
            }
            with patch.dict(os.environ, clean_env, clear=True):
                config = load_config(config_path)
                assert config.chromadb.host == "172.31.0.1"
                assert config.chromadb.port == 8080

    def test_set_nested_value_preserves_types(self) -> None:
        """Test that set_nested_value preserves value types."""
        data: dict[str, Any] = {}

        # Set various types
        set_nested_value(data, "chromadb.host", "192.168.1.1")
        set_nested_value(data, "chromadb.port", "8000")
        set_nested_value(data, "chromadb.ssl", "false")

        # Values should be preserved as provided
        assert data["chromadb"]["host"] == "192.168.1.1"
        assert data["chromadb"]["port"] == "8000"  # Still string
        assert data["chromadb"]["ssl"] == "false"  # Still string

        # Pydantic will handle conversion
        config = AppConfig(**data)
        assert config.chromadb.host == "192.168.1.1"
        assert config.chromadb.port == 8000  # Converted by Pydantic
        assert config.chromadb.ssl is False  # Converted by Pydantic

    def test_config_roundtrip_preserves_ip(self) -> None:
        """Test that saving and loading config preserves IP addresses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create config with IP address
            original_config = AppConfig(
                chromadb=ChromaDBConfig(host="10.10.10.10", port=8001)
            )

            # Save config
            save_config(original_config, config_path)

            # Load config - clear environment variables that might interfere
            clean_env = {
                k: v
                for k, v in os.environ.items()
                if not k.startswith(("CHROMA_", "SHARD_MD_"))
            }
            with patch.dict(os.environ, clean_env, clear=True):
                loaded_config = load_config(config_path)

                # Verify IP is preserved
                assert loaded_config.chromadb.host == "10.10.10.10"
                assert loaded_config.chromadb.port == 8001

    def test_edge_case_values(self) -> None:
        """Test edge case configuration values."""
        # Test with "0" as string
        config_dict: dict[str, Any] = {"chromadb": {"host": "0.0.0.0"}}  # noqa: S104
        config = AppConfig(**config_dict)
        assert config.chromadb.host == "0.0.0.0"  # noqa: S104

        # Test with numeric-looking hostnames
        config_dict = {"chromadb": {"host": "8.8.8.8"}}
        config = AppConfig(**config_dict)
        assert config.chromadb.host == "8.8.8.8"
