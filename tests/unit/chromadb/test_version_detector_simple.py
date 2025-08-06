"""Simple tests for ChromaDBVersionDetector to get basic coverage."""

import time
from unittest.mock import MagicMock, patch

import httpx

from shard_markdown.chromadb.version_detector import (
    APIVersionInfo,
    ChromaDBVersionDetector,
    detect_chromadb_version,
)


class TestBasicVersionDetector:
    """Basic tests for ChromaDBVersionDetector."""

    def test_detector_initialization(self):
        """Test detector initialization with default values."""
        detector = ChromaDBVersionDetector()

        assert detector.host == "localhost"
        assert detector.port == 8000
        assert detector.base_url == "http://localhost:8000"

    def test_detector_custom_initialization(self):
        """Test detector initialization with custom values."""
        detector = ChromaDBVersionDetector(
            host="custom-host",
            port=9000,
        )

        assert detector.host == "custom-host"
        assert detector.port == 9000
        assert detector.base_url == "http://custom-host:9000"

    @patch("httpx.Client")
    def test_make_request_success(self, mock_client_class):
        """Test successful HTTP request."""
        # Use MagicMock to automatically support context manager protocol
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = "OK"
        mock_client.get.return_value = mock_response
        # MagicMock automatically handles __enter__ and __exit__
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client

        detector = ChromaDBVersionDetector()
        success, content = detector._make_request("http://test.com/api")

        assert success is True
        assert content == "OK"

    @patch("httpx.Client")
    def test_make_request_failure(self, mock_client_class):
        """Test HTTP request failure."""
        # Use MagicMock for proper context manager support
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.RequestError("Connection failed")
        # MagicMock automatically handles context manager protocol
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client

        detector = ChromaDBVersionDetector(max_retries=1)

        with patch("time.sleep"):
            success, content = detector._make_request("http://test.com/api")

        assert success is False
        assert content is None

    @patch("httpx.Client")
    def test_test_endpoint(self, mock_client_class):
        """Test endpoint testing."""
        # Use MagicMock for proper context manager support
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        # MagicMock automatically handles context manager protocol
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client

        detector = ChromaDBVersionDetector()
        result = detector._test_endpoint("/api/v2/heartbeat")

        assert result is True

    @patch("httpx.Client")
    def test_get_version_info_success(self, mock_client_class):
        """Test successful version info retrieval."""
        # Use MagicMock for proper context manager support
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = '{"version": "1.0.15"}'
        mock_client.get.return_value = mock_response
        # MagicMock automatically handles context manager protocol
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client

        detector = ChromaDBVersionDetector()
        version = detector._get_version_info("/api/v2/version")

        assert version == "1.0.15"

    @patch("httpx.Client")
    def test_get_version_info_invalid_json(self, mock_client_class):
        """Test version info with invalid JSON response."""
        # Use MagicMock for proper context manager support
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = "invalid json"
        mock_client.get.return_value = mock_response
        # MagicMock automatically handles context manager protocol
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_class.return_value = mock_client

        detector = ChromaDBVersionDetector()
        version = detector._get_version_info("/api/v2/version")

        assert version is None

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        detector = ChromaDBVersionDetector()

        # Set cached version info
        detector._cached_version_info = APIVersionInfo(
            version="v2",
            heartbeat_endpoint="http://localhost:8000/api/v2/heartbeat",
            version_endpoint="http://localhost:8000/api/v2/version",
            detection_time=time.time(),
        )

        # Clear cache
        detector.clear_cache()

        assert detector._cached_version_info is None

    @patch("shard_markdown.chromadb.version_detector.ChromaDBVersionDetector")
    def test_detect_chromadb_version_function(self, mock_detector_class):
        """Test the detect_chromadb_version convenience function."""
        mock_detector = MagicMock()
        mock_info = APIVersionInfo(
            version="v2",
            heartbeat_endpoint="http://localhost:8000/api/v2/heartbeat",
            version_endpoint="http://localhost:8000/api/v2/version",
            detection_time=time.time(),
        )
        mock_detector.detect_api_version.return_value = mock_info
        mock_detector_class.return_value = mock_detector

        result = detect_chromadb_version(host="test-host", port=9000)

        mock_detector_class.assert_called_once_with(host="test-host", port=9000)
        mock_detector.detect_api_version.assert_called_once()
        assert result == mock_info


class TestAPIVersionInfo:
    """Test APIVersionInfo model."""

    def test_api_version_info_creation(self):
        """Test creating APIVersionInfo instance."""
        info = APIVersionInfo(
            version="v2",
            heartbeat_endpoint="http://localhost:8000/api/v2/heartbeat",
            version_endpoint="http://localhost:8000/api/v2/version",
            chromadb_version="1.0.15",
            detection_time=1234567890.0,
        )

        assert info.version == "v2"
        assert info.heartbeat_endpoint == "http://localhost:8000/api/v2/heartbeat"
        assert info.version_endpoint == "http://localhost:8000/api/v2/version"
        assert info.chromadb_version == "1.0.15"
        assert info.detection_time == 1234567890.0
        assert info.is_available is True  # Default value

    def test_api_version_info_minimal(self):
        """Test APIVersionInfo with minimal required fields."""
        info = APIVersionInfo(
            version="v1",
            heartbeat_endpoint="http://localhost:8000/api/v1/heartbeat",
            version_endpoint="http://localhost:8000/api/v1/version",
            detection_time=time.time(),
        )

        assert info.version == "v1"
        assert info.chromadb_version is None
        assert info.is_available is True
