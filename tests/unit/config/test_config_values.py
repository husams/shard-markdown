"""Tests for configuration value handling, especially IP addresses."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from shard_markdown.config import Settings, load_config, save_config


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
            config = Settings(chroma_host=ip)
            assert config.chroma_host == ip, f"IP address {ip} was not preserved"

    def test_ipv6_address_preservation(self) -> None:
        """Test that IPv6 addresses are preserved correctly."""
        test_ips = [
            "::1",
            "2001:db8::1",
            "fe80::1",
        ]

        for ip in test_ips:
            config = Settings(chroma_host=ip)
            assert config.chroma_host == ip, f"IPv6 address {ip} was not preserved"

    def test_hostname_preservation(self) -> None:
        """Test that hostnames are preserved correctly."""
        test_hosts = [
            "localhost",
            "example.com",
            "db.internal.network",
            "api-server.local",
        ]

        for host in test_hosts:
            config = Settings(chroma_host=host)
            assert config.chroma_host == host, f"Hostname {host} was not preserved"

    def test_environment_variable_ip_address(self) -> None:
        """Test IP addresses from environment variables."""
        test_ip = "192.168.100.50"

        with patch.dict(os.environ, {"SHARD_MD_CHROMA_HOST": test_ip}, clear=False):
            config = load_config()
            assert config.chroma_host == test_ip

    def test_environment_variable_types(self) -> None:
        """Test various types from environment variables."""
        env_vars = {
            "SHARD_MD_CHROMA_HOST": "10.20.30.40",
            "SHARD_MD_CHROMA_PORT": "9000",
            "SHARD_MD_CHROMA_SSL": "true",
            "SHARD_MD_CHUNK_SIZE": "1500",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = load_config()

            # IP address should be preserved as string
            assert config.chroma_host == "10.20.30.40"
            assert isinstance(config.chroma_host, str)

            # Port should be converted to int
            assert config.chroma_port == 9000
            assert isinstance(config.chroma_port, int)

            # Boolean should be converted
            assert config.chroma_ssl is True
            assert isinstance(config.chroma_ssl, bool)

            # Chunk size should be converted to int
            assert config.chunk_size == 1500
            assert isinstance(config.chunk_size, int)

    def test_yaml_config_ip_address(self) -> None:
        """Test IP addresses in YAML configuration files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Write config with IP address
            config_data = """
chroma_host: 172.31.0.1
chroma_port: 8080
chunk_size: 2000
"""
            config_path.write_text(config_data.strip())

            # Load and verify - clear environment variables that might interfere
            clean_env = {
                k: v for k, v in os.environ.items() if not k.startswith("SHARD_MD_")
            }
            with patch.dict(os.environ, clean_env, clear=True):
                config = load_config(config_path)
                assert config.chroma_host == "172.31.0.1"
                assert config.chroma_port == 8080

    def test_flat_config_values(self) -> None:
        """Test that flat configuration values work correctly."""
        config = Settings(
            chroma_host="192.168.1.1",
            chroma_port=8000,
            chroma_ssl=False,
            chunk_size=1500,
            chunk_overlap=300,
        )

        assert config.chroma_host == "192.168.1.1"
        assert config.chroma_port == 8000
        assert config.chroma_ssl is False
        assert config.chunk_size == 1500
        assert config.chunk_overlap == 300

    def test_config_roundtrip_preserves_ip(self) -> None:
        """Test that saving and loading config preserves IP addresses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create config with IP address
            original_config = Settings(
                chroma_host="10.10.10.10",
                chroma_port=8001,
            )

            # Save config
            save_config(original_config, config_path)

            # Load config - clear environment variables that might interfere
            clean_env = {
                k: v for k, v in os.environ.items() if not k.startswith("SHARD_MD_")
            }
            with patch.dict(os.environ, clean_env, clear=True):
                loaded_config = load_config(config_path)

                # Verify IP is preserved
                assert loaded_config.chroma_host == "10.10.10.10"
                assert loaded_config.chroma_port == 8001

    def test_edge_case_values(self) -> None:
        """Test edge case configuration values."""
        # Test with "0.0.0.0" as string
        config = Settings(chroma_host="0.0.0.0")  # noqa: S104
        assert config.chroma_host == "0.0.0.0"  # noqa: S104

        # Test with numeric-looking hostnames
        config = Settings(chroma_host="8.8.8.8")
        assert config.chroma_host == "8.8.8.8"
