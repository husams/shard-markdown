#!/bin/bash

# ChromaDB Version Detection and API Endpoint Discovery Script
# This script detects ChromaDB version and determines the correct API endpoints to use.
# It supports both v1 and v2 API endpoints with intelligent fallback logic.

set -euo pipefail

# Configuration
HOST="${CHROMA_HOST:-localhost}"
PORT="${CHROMA_PORT:-8000}"
TIMEOUT="${CHROMA_TIMEOUT:-30}"
MAX_RETRIES="${CHROMA_MAX_RETRIES:-5}"
RETRY_DELAY="${CHROMA_RETRY_DELAY:-2}"

# Color output functions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Show usage information
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Detects ChromaDB version and API endpoints with intelligent fallback logic.

Options:
    --host HOST         ChromaDB host (default: localhost)
    --port PORT         ChromaDB port (default: 8000)
    --timeout TIMEOUT   Connection timeout in seconds (default: 30)
    --retries RETRIES   Maximum retry attempts (default: 5)
    --delay DELAY       Retry delay in seconds (default: 2)
    --quiet             Suppress informational output
    --json              Output results in JSON format
    --help              Show this help message

Environment Variables:
    CHROMA_HOST         ChromaDB host (overrides --host)
    CHROMA_PORT         ChromaDB port (overrides --port)
    CHROMA_TIMEOUT      Connection timeout (overrides --timeout)
    CHROMA_MAX_RETRIES  Maximum retry attempts (overrides --retries)
    CHROMA_RETRY_DELAY  Retry delay (overrides --delay)

Exit Codes:
    0    Success - ChromaDB is accessible
    1    Connection failed - ChromaDB not accessible
    2    Invalid arguments
    3    Version detection failed

Examples:
    $0                                    # Use defaults
    $0 --host localhost --port 8001      # Custom host/port
    $0 --json --quiet                     # JSON output without logs
    $0 --retries 10 --delay 5             # Custom retry settings

EOF
}

# Parse command line arguments
QUIET=false
JSON_OUTPUT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --retries)
            MAX_RETRIES="$2"
            shift 2
            ;;
        --delay)
            RETRY_DELAY="$2"
            shift 2
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 2
            ;;
    esac
done

# Suppress logs if quiet mode is enabled
if [[ "$QUIET" == "true" ]]; then
    log_info() { :; }
    log_warning() { :; }
fi

# Validate inputs
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [[ "$PORT" -lt 1 ]] || [[ "$PORT" -gt 65535 ]]; then
    log_error "Invalid port: $PORT"
    exit 2
fi

if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]] || [[ "$TIMEOUT" -lt 1 ]]; then
    log_error "Invalid timeout: $TIMEOUT"
    exit 2
fi

if ! [[ "$MAX_RETRIES" =~ ^[0-9]+$ ]] || [[ "$MAX_RETRIES" -lt 1 ]]; then
    log_error "Invalid retries: $MAX_RETRIES"
    exit 2
fi

# Global variables for results
API_VERSION=""
HEARTBEAT_ENDPOINT=""
VERSION_ENDPOINT=""
CHROMADB_VERSION=""
CONNECTION_SUCCESS=false

# Function to make HTTP request with retries
make_request() {
    local url="$1"
    local retry_count=0

    while [[ $retry_count -lt $MAX_RETRIES ]]; do
        if curl -f -s --max-time "$TIMEOUT" --connect-timeout 10 "$url" >/dev/null 2>&1; then
            return 0
        fi

        retry_count=$((retry_count + 1))
        if [[ $retry_count -lt $MAX_RETRIES ]]; then
            log_info "Request to $url failed, retrying in ${RETRY_DELAY}s (attempt $retry_count/$MAX_RETRIES)"
            sleep "$RETRY_DELAY"
        fi
    done

    return 1
}

# Function to get response content with retries
get_response() {
    local url="$1"
    local retry_count=0

    while [[ $retry_count -lt $MAX_RETRIES ]]; do
        local response
        if response=$(curl -f -s --max-time "$TIMEOUT" --connect-timeout 10 "$url" 2>/dev/null); then
            echo "$response"
            return 0
        fi

        retry_count=$((retry_count + 1))
        if [[ $retry_count -lt $MAX_RETRIES ]]; then
            log_info "Request to $url failed, retrying in ${RETRY_DELAY}s (attempt $retry_count/$MAX_RETRIES)"
            sleep "$RETRY_DELAY"
        fi
    done

    return 1
}

# Function to detect API version and endpoints
detect_api_version() {
    local base_url="http://${HOST}:${PORT}"

    log_info "Detecting ChromaDB API version at $base_url"

    # Try v2 API first (ChromaDB 1.0+)
    log_info "Trying v2 API endpoints..."
    if make_request "${base_url}/api/v2/heartbeat"; then
        API_VERSION="v2"
        HEARTBEAT_ENDPOINT="${base_url}/api/v2/heartbeat"
        VERSION_ENDPOINT="${base_url}/api/v2/version"
        log_success "ChromaDB v2 API detected"
        return 0
    fi

    # Fall back to v1 API (ChromaDB 0.5.x and earlier)
    log_info "v2 API not available, trying v1 API endpoints..."
    if make_request "${base_url}/api/v1/heartbeat"; then
        API_VERSION="v1"
        HEARTBEAT_ENDPOINT="${base_url}/api/v1/heartbeat"
        VERSION_ENDPOINT="${base_url}/api/v1/version"
        log_success "ChromaDB v1 API detected"
        return 0
    fi

    # Try root heartbeat (some older versions)
    log_info "Standard API endpoints not available, trying root heartbeat..."
    if make_request "${base_url}/heartbeat"; then
        API_VERSION="root"
        HEARTBEAT_ENDPOINT="${base_url}/heartbeat"
        VERSION_ENDPOINT="${base_url}/version"
        log_warning "ChromaDB root API detected (older version)"
        return 0
    fi

    log_error "No compatible ChromaDB API endpoints found"
    return 1
}

# Function to get ChromaDB version information
get_version_info() {
    if [[ -z "$VERSION_ENDPOINT" ]]; then
        log_warning "Version endpoint not determined"
        return 1
    fi

    log_info "Fetching version information from $VERSION_ENDPOINT"

    local version_response
    if version_response=$(get_response "$VERSION_ENDPOINT"); then
        # Try to extract version from JSON response
        if command -v jq >/dev/null 2>&1; then
            CHROMADB_VERSION=$(echo "$version_response" | jq -r '.version // .chroma_version // empty' 2>/dev/null || echo "")
        else
            # Fallback: simple grep for version patterns
            CHROMADB_VERSION=$(echo "$version_response" | grep -oE '"(version|chroma_version)"\s*:\s*"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
        fi

        if [[ -n "$CHROMADB_VERSION" ]]; then
            log_success "ChromaDB version: $CHROMADB_VERSION"
        else
            log_warning "Could not parse version from response: $version_response"
            CHROMADB_VERSION="unknown"
        fi
        return 0
    else
        log_warning "Failed to fetch version information"
        CHROMADB_VERSION="unknown"
        return 1
    fi
}

# Function to test connectivity
test_connectivity() {
    log_info "Testing ChromaDB connectivity..."

    if make_request "$HEARTBEAT_ENDPOINT"; then
        CONNECTION_SUCCESS=true
        log_success "ChromaDB is accessible and responding"
        return 0
    else
        CONNECTION_SUCCESS=false
        log_error "ChromaDB connectivity test failed"
        return 1
    fi
}

# Function to output results
output_results() {
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        cat << EOF
{
  "host": "$HOST",
  "port": $PORT,
  "api_version": "$API_VERSION",
  "heartbeat_endpoint": "$HEARTBEAT_ENDPOINT",
  "version_endpoint": "$VERSION_ENDPOINT",
  "chromadb_version": "$CHROMADB_VERSION",
  "connection_success": $CONNECTION_SUCCESS,
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
    else
        echo "ChromaDB Detection Results:"
        echo "=========================="
        echo "Host: $HOST"
        echo "Port: $PORT"
        echo "API Version: $API_VERSION"
        echo "Heartbeat Endpoint: $HEARTBEAT_ENDPOINT"
        echo "Version Endpoint: $VERSION_ENDPOINT"
        echo "ChromaDB Version: $CHROMADB_VERSION"
        echo "Connection Success: $CONNECTION_SUCCESS"
        echo "Detection Time: $(date)"
    fi
}

# Main execution
main() {
    log_info "Starting ChromaDB version detection"
    log_info "Target: $HOST:$PORT (timeout: ${TIMEOUT}s, retries: $MAX_RETRIES)"

    # Step 1: Detect API version and endpoints
    if ! detect_api_version; then
        log_error "Failed to detect ChromaDB API version"
        output_results
        exit 1
    fi

    # Step 2: Test connectivity
    if ! test_connectivity; then
        log_error "ChromaDB connectivity test failed"
        output_results
        exit 1
    fi

    # Step 3: Get version information (non-critical)
    get_version_info || true

    # Step 4: Output results
    output_results

    if [[ "$CONNECTION_SUCCESS" == "true" ]]; then
        log_success "ChromaDB detection completed successfully"
        exit 0
    else
        log_error "ChromaDB detection failed"
        exit 1
    fi
}

# Handle script interruption
trap 'log_error "Script interrupted"; exit 130' INT TERM

# Execute main function
main "$@"
