# ChromaDB 1.0.16 E2E Test Failure Investigation Report

## Executive Summary

**Issue**: E2E tests are failing with ChromaDB 1.0.16 due to incorrect API version detection.

**Root Cause**: ChromaDB 1.0.16 has **deprecated the v1 API entirely** and only supports v2 API endpoints. Our code incorrectly assumes v1 API for ChromaDB 1.0.x versions.

**Impact**: Critical - All CI/CD E2E tests fail when using ChromaDB 1.0.16.

**Priority**: HIGH - Blocks all PR merges and deployments.

## Issue Details

### Problem Description
The E2E test workflow `e2e-cli (ubuntu-latest, 1.0.16)` consistently fails during ChromaDB connection attempts. The failure occurs when our client attempts to connect using v1 API endpoints, which ChromaDB 1.0.16 no longer supports.

### Affected Components
- `src/shard_markdown/chromadb/version_detector.py` - Incorrect version detection logic
- `.github/actions/setup-chromadb/action.yml` - Hardcoded v1 API assumption for 1.0.16
- E2E test workflows in GitHub Actions

### Evidence of the Issue
Direct testing against ChromaDB 1.0.16 container reveals:

```bash
# v1 endpoint returns 410 (Gone) with deprecation message
curl http://localhost:8000/api/v1/heartbeat
Response: {"error":"Unimplemented","message":"The v1 API is deprecated. Please use /v2 apis"}
Status: 410 Gone

# v2 endpoint works correctly
curl http://localhost:8000/api/v2/heartbeat
Response: {"nanosecond heartbeat": 1754795294785820252}
Status: 200 OK

# Root endpoint doesn't exist
curl http://localhost:8000/heartbeat
Status: 404 Not Found
```

## Investigation Findings

### 1. ChromaDB 1.0.16 API Architecture

**FACT**: ChromaDB 1.0.16 exclusively uses v2 API endpoints:
- `/api/v2/heartbeat` - Working health check endpoint
- `/api/v2/version` - Returns "1.0.0" (semantic versioning)
- `/api/v2/*` - All other API operations

**DEPRECATED**: v1 API endpoints return HTTP 410 (Gone) with explicit deprecation message.

### 2. Current Code Assumptions

Our `ChromaDBVersionDetector` class tests endpoints in this order:
1. v2 API - `/api/v2/heartbeat` (ChromaDB 1.0+)
2. v1 API - `/api/v1/heartbeat` (ChromaDB 0.5.x)
3. Root API - `/heartbeat` (older versions)

However, the GitHub Actions setup script hardcodes v1 for ChromaDB 1.0.16:

```yaml
# Line 233-236 in .github/actions/setup-chromadb/action.yml
api_version="v1"
heartbeat_url="${base_url}/api/v1"
version_url="${base_url}/api/v1/version"
```

### 3. Version Detection Mismatch

The version detector should work correctly (tests v2 first), but the CI/CD action overrides this with incorrect assumptions about ChromaDB 1.0.16 using v1 API.

### 4. Client-Server Compatibility

- **Client Version**: chromadb>=1.0.16 (in pyproject.toml)
- **Server Version**: chromadb/chroma:1.0.16 (Docker image)
- **Compatibility**: MATCHED - Both are 1.0.16

The issue is not a version mismatch but incorrect API endpoint detection.

## Technical Analysis

### Why the Tests Fail

1. **CI/CD Health Check**: The setup-chromadb action incorrectly defaults to v1 API for ChromaDB 1.0.16
2. **410 vs 200**: When checking `/api/v1/heartbeat`, it gets 410 (Gone) instead of 200 (OK)
3. **Connection Validation**: Our client connection validation fails because heartbeat returns an error

### ChromaDB Version History

Based on testing and documentation:
- **ChromaDB 0.5.x and earlier**: Used v1 API (`/api/v1/*`)
- **ChromaDB 1.0.0+**: Transitioned to v2 API (`/api/v2/*`)
- **ChromaDB 1.0.16**: v1 API completely deprecated, returns 410 with deprecation message

## Recommended Solutions

### Immediate Fix (Priority 1)

Update `.github/actions/setup-chromadb/action.yml` to correctly detect v2 API for ChromaDB 1.0.x:

```yaml
# Around line 100-107 (macOS) and similar sections
# Try v2 API first for ChromaDB 1.0+
if wget --spider -q http://localhost:${{ inputs.port }}/api/v2/heartbeat 2>/dev/null; then
  echo "✅ ChromaDB v2 API heartbeat is ready"
  detected_version="v2"
  api_ready=true
  break
fi

# Then try v1 API for older versions
if wget --spider -q http://localhost:${{ inputs.port }}/api/v1/heartbeat 2>/dev/null; then
  echo "✅ ChromaDB v1 API heartbeat is ready"
  detected_version="v1"
  api_ready=true
  break
fi
```

### Long-term Solution (Priority 2)

1. **Version-aware Detection**: Update the setup script to properly detect API version based on ChromaDB semantic version:
   - ChromaDB >= 1.0.0: Use v2 API
   - ChromaDB < 1.0.0: Use v1 API

2. **Remove Hardcoded Assumptions**: Around line 233-236, replace the hardcoded v1 assumption with dynamic detection.

3. **Enhanced Error Handling**: Handle 410 (Gone) responses specifically as API deprecation indicators.

### Preventive Measures

1. **Add Version Matrix Testing**: Test against multiple ChromaDB versions (0.5.x, 1.0.x, latest)
2. **Document API Transitions**: Create documentation about ChromaDB version compatibility
3. **Monitor ChromaDB Releases**: Set up alerts for ChromaDB releases that might affect API compatibility

## Testing & Validation Plan

### Immediate Validation

```bash
# Test ChromaDB 1.0.16 with v2 endpoints
docker run -d --name chromadb-test -p 8000:8000 chromadb/chroma:1.0.16
curl http://localhost:8000/api/v2/heartbeat  # Should return 200
curl http://localhost:8000/api/v1/heartbeat  # Should return 410
```

### Post-Fix Testing

1. Run E2E tests locally with ChromaDB 1.0.16
2. Verify GitHub Actions CI passes with the fix
3. Test backward compatibility with older ChromaDB versions

## Implementation Priority

1. **URGENT**: Fix `.github/actions/setup-chromadb/action.yml` to use v2 API for ChromaDB 1.0.16
2. **HIGH**: Update version detection logic to be more robust
3. **MEDIUM**: Add comprehensive ChromaDB version compatibility tests
4. **LOW**: Document ChromaDB API version requirements

## Risk Assessment

- **Current Risk**: HIGH - All E2E tests fail, blocking development
- **Fix Risk**: LOW - Simple endpoint URL change
- **Rollback Plan**: Revert to previous commit if issues arise

## Conclusion

ChromaDB 1.0.16 has completely deprecated the v1 API in favor of v2. Our CI/CD setup incorrectly assumes v1 API for this version, causing all E2E tests to fail. The fix is straightforward: update the endpoint detection to use v2 API for ChromaDB 1.0.x versions.

The Python client code (`ChromaDBVersionDetector`) already correctly tests v2 first, but the GitHub Actions setup script overrides this with incorrect hardcoded assumptions. Fixing the action script will resolve the E2E test failures immediately.
