"""ChromaDB version detection and API compatibility utilities."""

import time
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel

from shard_markdown.utils.errors import ChromaDBConnectionError
from shard_markdown.utils.logging import get_logger


logger = get_logger(__name__)


class APIVersionInfo(BaseModel):
    """Information about detected ChromaDB API version."""

    version: str  # "v1", "v2", or "root"
    heartbeat_endpoint: str
    version_endpoint: str
    chromadb_version: str | None = None
    detection_time: float
    is_available: bool = True


class ChromaDBVersionDetector:
    """Detects ChromaDB version and API endpoints with intelligent fallback logic."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        timeout: float = 30.0,
        max_retries: int = 5,
        retry_delay: float = 2.0,
    ) -> None:
        """Initialize the version detector.

        Args:
            host: ChromaDB host
            port: ChromaDB port
            timeout: Connection timeout in seconds
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.base_url = f"http://{host}:{port}"

        # Cache for detected version info
        self._cached_version_info: APIVersionInfo | None = None
        self._cache_timestamp: float = 0
        self._cache_ttl: float = 300.0  # 5 minutes

    def _make_request(self, url: str) -> tuple[bool, str | None]:
        """Make HTTP request with retries.

        Args:
            url: URL to request

        Returns:
            Tuple of (success, response_text)
        """
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url)

                    # Handle 410 (Gone) specifically - API endpoint is deprecated
                    if response.status_code == 410:
                        logger.debug(
                            f"Endpoint {url} returned 410 (Gone) - API deprecated"
                        )
                        # Return False but include the deprecation message
                        return False, response.text

                    response.raise_for_status()
                    return True, response.text
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.debug(
                        f"Request to {url} failed "
                        f"(attempt {attempt + 1}/{self.max_retries}): {e}"
                    )
                    time.sleep(self.retry_delay)
                else:
                    logger.debug(
                        f"Request to {url} failed after "
                        f"{self.max_retries} attempts: {e}"
                    )

        return False, None

    def _test_endpoint(self, endpoint: str) -> bool:
        """Test if an endpoint is available.

        Args:
            endpoint: Endpoint path (e.g., "/api/v2/heartbeat")

        Returns:
            True if endpoint is available
        """
        url = urljoin(self.base_url, endpoint)
        success, _ = self._make_request(url)
        return success

    def _get_version_info(self, version_endpoint: str) -> str | None:
        """Get ChromaDB version from version endpoint.

        Args:
            version_endpoint: Version endpoint path

        Returns:
            ChromaDB version string or None
        """
        url = urljoin(self.base_url, version_endpoint)
        success, response_text = self._make_request(url)

        if not success or not response_text:
            return None

        try:
            import json

            data = json.loads(response_text)

            # Try different possible version fields
            version_fields = ["version", "chroma_version", "chromadb_version"]
            for field in version_fields:
                if field in data and data[field]:
                    return str(data[field])
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.debug(f"Could not parse version from response: {e}")

        return None

    def detect_api_version(self, use_cache: bool = True) -> APIVersionInfo:
        """Detect ChromaDB API version and endpoints.

        Args:
            use_cache: Whether to use cached result if available

        Returns:
            API version information

        Raises:
            ChromaDBConnectionError: If no compatible API is found
        """
        # Check cache
        current_time = time.time()
        if (
            use_cache
            and self._cached_version_info
            and (current_time - self._cache_timestamp) < self._cache_ttl
        ):
            logger.debug("Using cached API version info")
            return self._cached_version_info

        logger.info(f"Detecting ChromaDB API version at {self.base_url}")
        detection_start = time.time()

        # Test endpoints in order of preference
        test_cases = [
            # v2 API (ChromaDB 1.0+)
            {
                "version": "v2",
                "heartbeat": "/api/v2/heartbeat",
                "version_endpoint": "/api/v2/version",
                "description": "ChromaDB v2 API (1.0+)",
            },
            # v1 API (ChromaDB 0.5.x and earlier)
            {
                "version": "v1",
                "heartbeat": "/api/v1/heartbeat",
                "version_endpoint": "/api/v1/version",
                "description": "ChromaDB v1 API (0.5.x)",
            },
            # Root API (older versions)
            {
                "version": "root",
                "heartbeat": "/heartbeat",
                "version_endpoint": "/version",
                "description": "ChromaDB root API (older versions)",
            },
        ]

        for test_case in test_cases:
            logger.debug(f"Testing {test_case['description']}...")

            if self._test_endpoint(test_case["heartbeat"]):
                logger.info(f"✅ {test_case['description']} detected")

                # Get version information (non-critical)
                chromadb_version = self._get_version_info(test_case["version_endpoint"])
                if chromadb_version:
                    logger.info(f"ChromaDB version: {chromadb_version}")
                else:
                    logger.debug("Could not determine ChromaDB version")

                # Create version info
                version_info = APIVersionInfo(
                    version=test_case["version"],
                    heartbeat_endpoint=urljoin(self.base_url, test_case["heartbeat"]),
                    version_endpoint=urljoin(
                        self.base_url, test_case["version_endpoint"]
                    ),
                    chromadb_version=chromadb_version,
                    detection_time=time.time() - detection_start,
                    is_available=True,
                )

                # Update cache
                self._cached_version_info = version_info
                self._cache_timestamp = current_time

                return version_info

        # No compatible API found
        error_msg = (
            f"No compatible ChromaDB API endpoints found at {self.base_url}. "
            "Tested v2, v1, and root APIs. Please check that ChromaDB is "
            "running and accessible."
        )
        logger.error(error_msg)
        raise ChromaDBConnectionError(error_msg)

    def test_connection(self, version_info: APIVersionInfo | None = None) -> bool:
        """Test connection to ChromaDB using detected API version.

        Args:
            version_info: Pre-detected version info, or None to detect automatically

        Returns:
            True if connection is successful
        """
        if not version_info:
            try:
                version_info = self.detect_api_version()
            except ChromaDBConnectionError:
                return False

        success, _ = self._make_request(version_info.heartbeat_endpoint)
        return success

    def get_recommended_client_settings(
        self, version_info: APIVersionInfo | None = None
    ) -> dict[str, str]:
        """Get recommended client settings based on detected API version.

        Args:
            version_info: Pre-detected version info, or None to detect automatically

        Returns:
            Dict of recommended settings
        """
        if not version_info:
            version_info = self.detect_api_version()

        settings = {
            "host": self.host,
            "port": str(self.port),
            "api_version": version_info.version,
            "heartbeat_endpoint": version_info.heartbeat_endpoint,
            "version_endpoint": version_info.version_endpoint,
        }

        if version_info.chromadb_version:
            settings["chromadb_version"] = version_info.chromadb_version

        # Add version-specific recommendations
        if version_info.version == "v2":
            settings["recommended_features"] = "all"
        elif version_info.version == "v1":
            settings["recommended_features"] = "legacy_compatible"
        else:
            settings["recommended_features"] = "basic"

        return settings

    def clear_cache(self) -> None:
        """Clear cached version information."""
        self._cached_version_info = None
        self._cache_timestamp = 0
        logger.debug("Cleared API version cache")


def detect_chromadb_version(
    host: str = "localhost",
    port: int = 8000,
    timeout: float = 30.0,
    max_retries: int = 5,
) -> APIVersionInfo:
    """Convenience function to detect ChromaDB API version.

    Args:
        host: ChromaDB host
        port: ChromaDB port
        timeout: Connection timeout in seconds
        max_retries: Maximum retry attempts

    Returns:
        API version information

    Raises:
        ChromaDBConnectionError: If no compatible API is found
    """
    detector = ChromaDBVersionDetector(
        host=host,
        port=port,
        timeout=timeout,
        max_retries=max_retries,
    )
    return detector.detect_api_version()


def test_chromadb_connection(
    host: str = "localhost",
    port: int = 8000,
    timeout: float = 30.0,
) -> bool:
    """Test ChromaDB connection with automatic version detection.

    Args:
        host: ChromaDB host
        port: ChromaDB port
        timeout: Connection timeout in seconds

    Returns:
        True if connection is successful
    """
    try:
        detector = ChromaDBVersionDetector(host=host, port=port, timeout=timeout)
        return detector.test_connection()
    except Exception as e:
        logger.debug(f"ChromaDB connection test failed: {e}")
        return False
