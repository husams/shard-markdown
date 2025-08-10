# Migration: Removal of Custom Configuration Value Parsing

## Overview

This migration documents the removal of custom configuration value parsing logic that was causing IP address corruption and other type conversion issues.

## What Changed

### Removed Components

1. **Function**: `parse_config_value()` from `src/shard_markdown/config/utils.py`
   - Previously attempted to parse string values into Python types (int, float, bool)
   - Caused IP address corruption by truncating leading digits
   - Replaced with direct string passing to Pydantic models

### Updated Components

1. **Environment Variable Handling**: `_apply_env_overrides()` in `src/shard_markdown/config/loader.py`
   - Environment variables now passed as strings directly to Pydantic models
   - Type conversion handled by Pydantic based on field definitions
   - No more custom parsing logic

2. **Configuration Setting**: `set()` command in `src/shard_markdown/cli/commands/config.py`
   - CLI configuration values passed as strings to Pydantic models
   - Pydantic handles type validation and conversion
   - Better error messages for invalid values

## Technical Details

### Before (Problematic)
```python
def parse_config_value(value: str) -> Any:
    """Parse configuration value from string to appropriate type."""
    # Try to parse as integer
    try:
        return int(value)
    except ValueError:
        pass
    # ... more parsing logic
    # This caused IP addresses like "192.168.64.3" to become "92.168.64.3"
```

### After (Fixed)
```python
# Environment variables passed directly as strings
set_nested_value(result, config_path, env_value)

# Pydantic models handle type conversion
config = AppConfig(**config_dict)  # Type validation happens here
```

## Benefits

1. **IP Address Safety**: No more truncation of IP addresses or other string values
2. **Better Type Safety**: Pydantic provides better type validation and error messages
3. **Simpler Code**: Removed custom parsing logic reduces complexity
4. **Consistent Behavior**: All configuration values handled the same way

## Impact Assessment

### Breaking Changes
- **None**: This is an internal implementation change with no API changes

### Fixed Issues
- IP address corruption (e.g., "192.168.64.3" becoming "92.168.64.3")
- Inconsistent type conversion behavior
- Poor error messages for invalid configuration values

### Validation Required
- Environment variable handling works correctly
- CLI `config set` command validates input properly  
- All configuration types (string, int, bool, etc.) are handled correctly

## Migration Actions

No user action required. This is an internal bug fix that maintains the same external API.

## Testing

Verify the fix by:

1. Setting IP addresses via environment variables:
   ```bash
   export CHROMA_HOST=192.168.64.3
   shard-md collections list
   ```

2. Setting configuration via CLI:
   ```bash
   shard-md config set chromadb.host 192.168.64.3
   shard-md config show --section chromadb
   ```

3. Checking that all configuration types work:
   ```bash
   shard-md config set chromadb.port 8000        # integer
   shard-md config set chunking.overlap true     # boolean  
   shard-md config set chunking.strategy semantic # string
   ```

All values should be preserved exactly as entered.