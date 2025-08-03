# Manual Testing Checklist

## Overview

This document provides comprehensive manual testing checklists for the shard-markdown CLI utility. These tests complement automated testing by validating user experience, edge cases, and scenarios that are difficult to automate.

## Pre-Testing Setup

### Environment Preparation
- [ ] Virtual environment activated
- [ ] Latest dependencies installed (`uv pip install -e ".[dev]"`)
- [ ] ChromaDB running (if testing real integration)
- [ ] Test data directory prepared
- [ ] Previous test artifacts cleaned up

### Test Data Preparation
```bash
# Create test directory structure
mkdir -p manual_tests/{simple,complex,large,edge_cases}

# Simple test documents
echo "# Simple Document
This is a basic test document.
## Section 1
Content here." > manual_tests/simple/basic.md

# Complex document with frontmatter
cat > manual_tests/complex/with_frontmatter.md << 'EOF'
---
title: "Complex Test Document"
author: "Test User"
tags: ["test", "complex"]
---

# Complex Document
This document has frontmatter and code.

```python
def test_function():
    return "Hello World"
```
EOF

# Large document
python -c "
content = '# Large Document\n\n'
for i in range(100):
    content += f'## Section {i}\n'
    content += 'Lorem ipsum dolor sit amet. ' * 50 + '\n\n'
with open('manual_tests/large/large_doc.md', 'w') as f:
    f.write(content)
"
```

## CLI Interface Testing

### Basic Command Functionality

#### Help System
- [ ] `shard-md --help` displays main help
- [ ] `shard-md --version` shows correct version
- [ ] `shard-md process --help` shows process command help
- [ ] Help text is clear and informative
- [ ] All options are documented
- [ ] Examples are provided and accurate

#### Version Information
- [ ] Version number matches expected release
- [ ] Version format is consistent (e.g., "0.1.0")
- [ ] Version command exits with code 0

### Process Command Testing

#### Basic Processing
```bash
# Test basic document processing
shard-md process --collection test-basic manual_tests/simple/basic.md
```
- [ ] Command executes without errors
- [ ] Success message is displayed
- [ ] Processing statistics are shown
- [ ] Collection is created successfully
- [ ] Chunks are generated appropriately

#### Chunking Options
```bash
# Test different chunk sizes
shard-md process --collection test-chunks-500 --chunk-size 500 manual_tests/simple/basic.md
shard-md process --collection test-chunks-1000 --chunk-size 1000 manual_tests/simple/basic.md
shard-md process --collection test-chunks-1500 --chunk-size 1500 manual_tests/simple/basic.md
```
- [ ] Different chunk sizes produce different results
- [ ] Larger chunk sizes create fewer chunks
- [ ] Chunk size validation works correctly
- [ ] Invalid chunk sizes are rejected

#### Overlap Configuration
```bash
# Test overlap settings
shard-md process --collection test-overlap --chunk-size 1000 --chunk-overlap 200 manual_tests/simple/basic.md
```
- [ ] Overlap parameter is accepted
- [ ] Overlap affects chunk generation
- [ ] Invalid overlap values are rejected (e.g., overlap > chunk size)

#### Chunking Methods
```bash
# Test different chunking methods
shard-md process --collection test-structure --chunk-method structure manual_tests/complex/with_frontmatter.md
shard-md process --collection test-fixed --chunk-method fixed manual_tests/complex/with_frontmatter.md
```
- [ ] Structure method preserves markdown structure
- [ ] Fixed method creates consistent chunk sizes
- [ ] Invalid methods are rejected
- [ ] Method choice affects output appropriately

#### File Path Handling
```bash
# Test various file path scenarios
shard-md process --collection test-paths manual_tests/simple/basic.md
shard-md process --collection test-relative ./manual_tests/simple/basic.md
shard-md process --collection test-absolute $PWD/manual_tests/simple/basic.md
```
- [ ] Relative paths work correctly
- [ ] Absolute paths work correctly
- [ ] Non-existent files show clear error messages
- [ ] File permission errors are handled gracefully

#### Multiple File Processing
```bash
# Test multiple files
shard-md process --collection test-multi manual_tests/simple/*.md
shard-md process --collection test-mixed manual_tests/simple/basic.md manual_tests/complex/with_frontmatter.md
```
- [ ] Multiple files are processed successfully
- [ ] Progress is shown for batch processing
- [ ] Individual file failures don't stop entire batch
- [ ] Summary statistics are accurate

#### Recursive Processing
```bash
# Test recursive directory processing
shard-md process --collection test-recursive --recursive manual_tests/
```
- [ ] All markdown files in subdirectories are found
- [ ] Non-markdown files are ignored
- [ ] Directory structure is traversed correctly
- [ ] Empty directories are handled gracefully

### Error Handling Testing

#### Invalid Arguments
- [ ] `shard-md process` (no arguments) shows helpful error
- [ ] `shard-md process --collection` (missing collection name) shows error
- [ ] `shard-md process --collection test` (no files) shows error
- [ ] `shard-md --invalid-option` shows appropriate error

#### File System Errors
```bash
# Test various error conditions
shard-md process --collection test-errors /nonexistent/file.md
shard-md process --collection test-errors /etc/passwd  # Permission denied
echo "" > manual_tests/edge_cases/empty.md
shard-md process --collection test-empty manual_tests/edge_cases/empty.md
```
- [ ] Non-existent files show clear error messages
- [ ] Permission denied errors are handled gracefully
- [ ] Empty files are handled appropriately
- [ ] Binary files are rejected with clear messages

#### Invalid Content
```bash
# Create problematic content
echo -e "\xff\xfe# Invalid encoding" > manual_tests/edge_cases/bad_encoding.md
shard-md process --collection test-encoding manual_tests/edge_cases/bad_encoding.md
```
- [ ] Invalid encoding is detected and handled
- [ ] Error messages are user-friendly
- [ ] Processing continues with other files in batch

### Configuration Testing

#### Configuration File Usage
```bash
# Create test configuration
cat > test_config.yaml << 'EOF'
chromadb:
  host: localhost
  port: 8000
chunking:
  default_size: 1200
  default_overlap: 240
EOF

shard-md --config test_config.yaml process --collection test-config manual_tests/simple/basic.md
```
- [ ] Configuration file is loaded correctly
- [ ] Settings override defaults appropriately
- [ ] Invalid configuration files show clear errors
- [ ] Missing configuration files are handled gracefully

#### Environment Variables
```bash
# Test environment variable override
SHARD_MD_CHROMADB_HOST=localhost SHARD_MD_CHROMADB_PORT=8001 shard-md process --collection test-env manual_tests/simple/basic.md
```
- [ ] Environment variables override configuration
- [ ] Invalid environment values are validated
- [ ] Environment variable names follow convention

### Output and Verbosity Testing

#### Verbosity Levels
```bash
# Test different verbosity levels
shard-md -v process --collection test-verbose manual_tests/simple/basic.md
shard-md -vv process --collection test-very-verbose manual_tests/simple/basic.md
shard-md -q process --collection test-quiet manual_tests/simple/basic.md
```
- [ ] Verbose mode shows more detailed output
- [ ] Very verbose mode shows debug information
- [ ] Quiet mode suppresses non-essential output
- [ ] Output levels are appropriate for each verbosity

#### Progress Reporting
```bash
# Test progress reporting with larger dataset
shard-md process --collection test-progress manual_tests/large/large_doc.md
```
- [ ] Progress is shown for long-running operations
- [ ] Progress indicators are clear and accurate
- [ ] Estimated time remaining is reasonable
- [ ] Progress updates don't interfere with output

## Edge Case Testing

### Document Content Edge Cases

#### Special Characters and Unicode
```bash
# Create documents with special content
cat > manual_tests/edge_cases/unicode.md << 'EOF'
# Unicode Test 🚀
Testing with émojis and spéciál characters.
## Section with 中文
Content with various Unicode: ñáéíóú αβγδε
EOF

shard-md process --collection test-unicode manual_tests/edge_cases/unicode.md
```
- [ ] Unicode characters are preserved correctly
- [ ] Emojis are handled properly
- [ ] Various character encodings work
- [ ] No corruption of special characters

#### Extremely Large Documents
```bash
# Create very large document
python -c "
content = '# Huge Document\n\n'
for i in range(10000):
    content += f'## Section {i}\n'
    content += 'Content line. ' * 100 + '\n\n'
with open('manual_tests/edge_cases/huge.md', 'w') as f:
    f.write(content)
"

shard-md process --collection test-huge manual_tests/edge_cases/huge.md
```
- [ ] Very large documents are processed successfully
- [ ] Memory usage remains reasonable
- [ ] Processing time is acceptable
- [ ] Progress is shown for long operations

#### Malformed Markdown
```bash
# Create malformed markdown
cat > manual_tests/edge_cases/malformed.md << 'EOF'
# Unclosed Code Block
```python
def function():
    return "no closing backticks"

## Header in Code Block?
Still in code block...

# Another header
```

### Normal content after malformed section
EOF

shard-md process --collection test-malformed manual_tests/edge_cases/malformed.md
```
- [ ] Malformed markdown doesn't crash the application
- [ ] Parsing errors are handled gracefully
- [ ] Warnings are shown for problematic content
- [ ] Valid content is still processed

### System Resource Testing

#### Memory Usage Monitoring
```bash
# Monitor memory usage during processing
ps aux | grep shard-md &
shard-md process --collection test-memory manual_tests/large/large_doc.md
```
- [ ] Memory usage is reasonable during processing
- [ ] Memory is released after processing
- [ ] No memory leaks during repeated operations
- [ ] Memory usage scales appropriately with document size

#### Concurrent Processing
```bash
# Test multiple simultaneous processes
shard-md process --collection test-concurrent-1 manual_tests/large/large_doc.md &
shard-md process --collection test-concurrent-2 manual_tests/complex/with_frontmatter.md &
wait
```
- [ ] Multiple processes can run simultaneously
- [ ] No resource conflicts between processes
- [ ] Database operations don't interfere
- [ ] Performance is reasonable with concurrent access

## Performance Testing

### Processing Speed Validation
```bash
# Time processing operations
time shard-md process --collection perf-test-1 manual_tests/simple/basic.md
time shard-md process --collection perf-test-2 manual_tests/complex/with_frontmatter.md
time shard-md process --collection perf-test-3 manual_tests/large/large_doc.md
```
- [ ] Small documents process in <1 second
- [ ] Medium documents process in <5 seconds
- [ ] Large documents process in <30 seconds
- [ ] Performance is consistent across runs

### Batch Processing Performance
```bash
# Create multiple test files
for i in {1..20}; do
    cp manual_tests/simple/basic.md manual_tests/simple/basic_$i.md
done

time shard-md process --collection batch-perf manual_tests/simple/basic_*.md
```
- [ ] Batch processing is faster than individual processing
- [ ] Progress is shown for batch operations
- [ ] Memory usage doesn't grow linearly with batch size
- [ ] Error in one file doesn't affect others

## Integration Testing

### ChromaDB Integration
```bash
# Test with real ChromaDB instance (if available)
docker run -p 8000:8000 chromadb/chroma:latest &
sleep 10  # Wait for startup

shard-md process --collection integration-test manual_tests/simple/basic.md
```
- [ ] Connects to ChromaDB successfully
- [ ] Collections are created properly
- [ ] Documents are inserted correctly
- [ ] Connection errors are handled gracefully

### Configuration Integration
```bash
# Test full configuration workflow
shard-md config init test_full_config.yaml
shard-md --config test_full_config.yaml process --collection config-integration manual_tests/simple/basic.md
```
- [ ] Configuration initialization works
- [ ] Configuration is loaded and applied
- [ ] Settings are validated properly
- [ ] Configuration errors are clear

## User Experience Testing

### Error Message Quality
- [ ] Error messages are clear and actionable
- [ ] Help text is comprehensive and accurate
- [ ] Examples in help are working and relevant
- [ ] Error codes are consistent and documented

### Documentation Validation
- [ ] README instructions are accurate
- [ ] Installation steps work on clean system
- [ ] Examples produce expected results
- [ ] Troubleshooting guide is helpful

### Accessibility and Usability
- [ ] Command structure is intuitive
- [ ] Option names are clear and consistent
- [ ] Default values are reasonable
- [ ] Common use cases are easy to accomplish

## Final Validation Checklist

### Pre-Release Validation
- [ ] All manual tests pass on target platforms
- [ ] Performance meets established benchmarks
- [ ] Error handling is comprehensive and user-friendly
- [ ] Documentation is accurate and complete
- [ ] Installation process is smooth
- [ ] Uninstallation process is clean

### Platform-Specific Testing
#### Linux
- [ ] All functionality works on Ubuntu/CentOS
- [ ] File permissions are handled correctly
- [ ] Path separators work properly

#### macOS
- [ ] All functionality works on latest macOS
- [ ] Case-sensitive file system handling
- [ ] Homebrew installation compatibility

#### Windows
- [ ] All functionality works on Windows 10/11
- [ ] Path handling with drive letters
- [ ] PowerShell compatibility

### Security Validation
- [ ] No sensitive information in logs
- [ ] File permissions are respected
- [ ] Input validation prevents injection
- [ ] Dependencies are secure

## Test Execution Log

### Test Session Information
- **Date**: ___________
- **Tester**: ___________
- **Environment**: ___________
- **Version**: ___________

### Results Summary
- **Total Tests**: ___________
- **Passed**: ___________
- **Failed**: ___________
- **Skipped**: ___________

### Issues Found
1. **Issue**: ________________
   **Severity**: ________________
   **Steps to Reproduce**: ________________
   **Expected**: ________________
   **Actual**: ________________

2. **Issue**: ________________
   **Severity**: ________________
   **Steps to Reproduce**: ________________
   **Expected**: ________________
   **Actual**: ________________

### Recommendations
- ________________________________
- ________________________________
- ________________________________

### Sign-off
- [ ] All critical functionality tested
- [ ] All found issues documented
- [ ] Test environment cleaned up
- [ ] Results communicated to team

**Tester Signature**: ___________
**Date**: ___________
