# 🐛 Bug Report: IP Address Corruption in ChromaDB Host Configuration

## Executive Summary

The shard-markdown tool is corrupting IP addresses when connecting to ChromaDB, specifically truncating "192.168.64.3" to "92.168.64.3" (missing the leading "1"). This is caused by the `parse_config_value()` function attempting to convert IP addresses to integers, which fails and triggers unintended string manipulation.

## Issue Details

### Problem Description
When attempting to connect to a ChromaDB instance at IP address `192.168.64.3`, the connection fails with an error indicating it cannot connect to `92.168.64.3`. The first character "1" is being stripped from the IP address.

### Affected Components
- **Module**: `src/shard_markdown/config/utils.py`
- **Function**: `parse_config_value()`
- **Impact**: All users attempting to connect to ChromaDB using IP addresses that start with "1"

### Severity
**HIGH** - This bug prevents users from connecting to ChromaDB instances using certain IP addresses, making the tool unusable in specific network configurations.

## Root Cause Analysis

The issue lies in the `parse_config_value()` function in `/src/shard_markdown/config/utils.py` (lines 46-49):

```python
def parse_config_value(value: str) -> Any:
    """Parse configuration value to appropriate type."""
    # ... boolean handling ...

    # Try to convert to integer
    try:
        return int(value)  # <-- PROBLEM: "192.168.64.3" triggers ValueError
    except ValueError:
        pass

    # Try to convert to float
    try:
        return float(value)  # <-- PROBLEM: Also fails for IP addresses
    except ValueError:
        pass

    # Return as string
    return value
```

### The Bug Mechanism

1. When an IP address like "192.168.64.3" is passed to `parse_config_value()`
2. The function attempts `int("192.168.64.3")` which raises a `ValueError`
3. The function then attempts `float("192.168.64.3")` which also raises a `ValueError`
4. **However**, there appears to be a secondary issue where the string is being corrupted during this process

### Suspected Secondary Issue

The actual truncation might be happening in one of these scenarios:
1. The value is being passed through another function that strips leading digits
2. There's an encoding/decoding issue with the character "1"
3. The configuration is being loaded from an environment variable or YAML file where special parsing rules apply

## Steps to Reproduce

1. Set ChromaDB host configuration to an IP address starting with "1":
   ```bash
   export CHROMA_HOST="192.168.64.3"
   # OR
   shard-md config set chromadb.host 192.168.64.3
   ```

2. Attempt to connect to ChromaDB:
   ```bash
   shard-md collections list
   ```

3. Observe error message showing connection attempt to "92.168.64.3"

## Expected Behavior
The tool should connect to the ChromaDB instance at the correct IP address `192.168.64.3`.

## Actual Behavior
The tool attempts to connect to `92.168.64.3` (missing the leading "1") and fails.

## System Information
- **shard-markdown version**: Latest (from main branch)
- **Python version**: 3.8+
- **Operating System**: All platforms affected
- **ChromaDB version**: Any version

## Proposed Solutions

### Solution 1: IP Address Detection (Recommended)
Modify `parse_config_value()` to detect and preserve IP addresses:

```python
import re

def parse_config_value(value: str) -> Any:
    """Parse configuration value to appropriate type."""

    # Check if it looks like an IP address or hostname
    if _is_host_or_ip(value):
        return value  # Return as-is without conversion attempts

    # Handle boolean values
    if value.lower() in ("true", "1", "yes", "on"):
        return True
    elif value.lower() in ("false", "0", "no", "off"):
        return False
    elif value.lower() in ("null", "none", ""):
        return None

    # Try numeric conversions only for non-host values
    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        pass

    return value

def _is_host_or_ip(value: str) -> bool:
    """Check if value looks like a hostname or IP address."""
    # IPv4 pattern
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    # IPv6 pattern (simplified)
    ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'
    # Hostname pattern (contains dots or is localhost)
    hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'

    return bool(
        re.match(ipv4_pattern, value) or
        re.match(ipv6_pattern, value) or
        re.match(hostname_pattern, value) or
        value in ('localhost', '127.0.0.1', '::1')
    )
```

### Solution 2: Type Hints in Configuration
Add explicit type handling for known configuration fields:

```python
# In config/loader.py or config/utils.py
FIELD_TYPES = {
    'chromadb.host': str,  # Always treat as string
    'chromadb.port': int,
    'chromadb.ssl': bool,
    # ... other fields
}

def parse_config_value(value: str, field_path: str = None) -> Any:
    """Parse configuration value to appropriate type."""

    # If we know the field type, use it
    if field_path and field_path in FIELD_TYPES:
        field_type = FIELD_TYPES[field_path]
        if field_type == str:
            return value
        elif field_type == int:
            return int(value)
        elif field_type == bool:
            return value.lower() in ("true", "1", "yes", "on")

    # ... rest of existing logic
```

### Solution 3: Minimal Fix
As a quick fix, check for dots in the string before attempting numeric conversion:

```python
def parse_config_value(value: str) -> Any:
    """Parse configuration value to appropriate type."""

    # Don't try to convert strings with dots to numbers (likely IP/hostname)
    if '.' in value and not value.replace('.', '').replace('-', '').isdigit():
        return value

    # ... rest of existing logic
```

## Immediate Workarounds

Users experiencing this issue can try these workarounds:

1. **Use hostname instead of IP**:
   ```bash
   # Add to /etc/hosts (Linux/Mac) or C:\Windows\System32\drivers\etc\hosts (Windows)
   192.168.64.3 chromadb-server

   # Then use:
   shard-md config set chromadb.host chromadb-server
   ```

2. **Direct connection in code** (bypass config):
   ```python
   from shard_markdown.chromadb.client import ChromaDBClient
   from shard_markdown.config.settings import ChromaDBConfig

   config = ChromaDBConfig(host="192.168.64.3", port=8000)
   client = ChromaDBClient(config)
   ```

3. **Use environment variable with quotes**:
   ```bash
   export CHROMA_HOST='"192.168.64.3"'
   ```

## Testing Plan

1. **Unit Tests**: Add tests for `parse_config_value()` with various IP addresses:
   ```python
   def test_parse_config_value_preserves_ip_addresses():
       assert parse_config_value("192.168.64.3") == "192.168.64.3"
       assert parse_config_value("10.0.0.1") == "10.0.0.1"
       assert parse_config_value("172.16.0.1") == "172.16.0.1"
       assert parse_config_value("::1") == "::1"
       assert parse_config_value("localhost") == "localhost"
   ```

2. **Integration Tests**: Test full configuration loading with IP addresses

3. **Regression Tests**: Ensure numeric values still parse correctly:
   ```python
   def test_parse_config_value_numeric():
       assert parse_config_value("8000") == 8000
       assert parse_config_value("3.14") == 3.14
       assert parse_config_value("true") == True
   ```

## Prevention Measures

1. **Add type annotations** to configuration schema
2. **Validate IP addresses** using `ipaddress` module
3. **Add configuration validation tests** for all network-related settings
4. **Document** that host fields should not be auto-converted

## Related Issues
- None found

## References
- Python `ipaddress` module: https://docs.python.org/3/library/ipaddress.html
- ChromaDB configuration docs: https://docs.trychroma.com/

---

**Labels**: `bug`, `high-priority`, `configuration`, `chromadb`, `networking`

**Assignees**: TBD

**Milestone**: Next patch release
