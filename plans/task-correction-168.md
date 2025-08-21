# Issue #168 CLI Simplification - Correction Task

## Developer: Ultra-Strict Execution Mode

### Purpose
Complete and correct the CLI simplification implementation to meet ALL Issue #168 requirements, particularly the missed 30% line reduction target and missing backward compatibility.

### Pre-Task Checklist
- [ ] Verify line count baseline: 1,367 lines (target: ~950 lines)
- [ ] Identify line reduction opportunities in data.py consolidation
- [ ] Plan backward compatibility aliases for breaking changes
- [ ] Confirm exactly 18 files modification constraint
- [ ] Review E2E test failure for collections/query commands
- [ ] Validate __init__.py and utils.py modification requirements

---

## CRITICAL CONSTRAINTS

### File Modification Limits (STRICT - 18 FILES MAXIMUM)

**ALLOWED TO MODIFY (11 files):**
```
Source Files (6):
1. src/shard_markdown/cli/main.py
2. src/shard_markdown/cli/commands/data.py
3. src/shard_markdown/cli/commands/config.py
4. src/shard_markdown/cli/commands/process.py
5. src/shard_markdown/cli/commands/__init__.py
6. src/shard_markdown/cli/utils.py

Test Files (5):
7. tests/unit/cli/commands/test_collections.py
8. tests/unit/cli/commands/test_query.py
9. tests/unit/cli/commands/test_config.py
10. tests/unit/cli/test_main.py
11. tests/e2e/test_cli_workflows.py
```

**DO NOT MODIFY:**
- ANY file not listed above
- tests/unit/cli/test_process_command.py (not required)
- tests/unit/cli/test_utils.py (not required)
- Any configuration files
- Any documentation files
- Any files outside cli/ directory

---

## Instructions

### Phase 1: Knowledge Graph Integration (5 minutes)
```python
# MANDATORY: Query before starting
search_knowledge(query="Issue_168", project_id="shard_markdown")
search_knowledge(query="Issue_168_Completion_Summary", project_id="shard_markdown")
open_nodes(names=["Issue_168_Affected_Files", "Issue_168_Current_Structure"])
```

### Phase 2: Line Reduction Analysis (15 minutes)
1. **Analyze current data.py** (619 lines):
   - Identify duplicate code between collections and query sections
   - Find shared utility functions that can be extracted
   - Look for verbose implementations that can be simplified

2. **Target reductions**:
   - data.py: Must reduce from 619 to ~400 lines
   - config.py: Must reduce from 384 to ~300 lines
   - main.py: Already optimal at 111 lines
   - utils.py: Must clean to <50 lines

3. **Techniques to apply**:
   - Extract common table display functions
   - Consolidate error handling patterns
   - Remove redundant docstrings (keep only essential)
   - Simplify verbose click decorators

### Phase 3: Implement Line Reductions (45 minutes)

#### 3.1 Optimize data.py
```python
# MANDATORY optimizations:
- Merge duplicate display functions (_display_collections_table, _display_search_results_table)
- Extract common ChromaDB client initialization
- Consolidate similar command patterns
- Remove excessive comments and docstrings
- Target: 619 → 400 lines (35% reduction)
```

#### 3.2 Optimize config.py
```python
# MANDATORY optimizations:
- Simplify option handling logic
- Reduce validation verbosity
- Consolidate file operations
- Target: 384 → 300 lines (22% reduction)
```

#### 3.3 Clean utils.py
```python
# MANDATORY actions:
- Verify only 2 functions remain (handle_chromadb_errors, get_connected_chromadb_client)
- Remove any commented code
- Minimize docstrings
- Target: Current → <50 lines
```

### Phase 4: Add Backward Compatibility (20 minutes)

#### 4.1 Update main.py
```python
# Add command aliases with deprecation warnings:
@cli.command(hidden=True)
def collections():
    """Deprecated: Use 'data' command instead."""
    click.echo("Warning: 'collections' is deprecated. Use 'shard-md data' instead.", err=True)
    ctx = click.get_current_context()
    ctx.invoke(data)

@cli.command(hidden=True)
def query():
    """Deprecated: Use 'data' command instead."""
    click.echo("Warning: 'query' is deprecated. Use 'shard-md data' instead.", err=True)
    ctx = click.get_current_context()
    ctx.invoke(data)
```

### Phase 5: Fix E2E Test (10 minutes)

#### 5.1 Update test_cli_workflows.py
```python
# Fix test_help_and_version_commands:
- Replace: cli_runner.invoke(cli, ["collections", "--help"])
- With: cli_runner.invoke(cli, ["data", "--help"])

- Replace: cli_runner.invoke(cli, ["query", "--help"])
- With: cli_runner.invoke(cli, ["data", "--help"])

# Verify backward compatibility:
- Add test for deprecated command warning
```

### Phase 6: Update __init__.py (5 minutes)
```python
# Update imports in src/shard_markdown/cli/commands/__init__.py:
- Remove imports for deleted modules (collections, query)
- Add import for new data module
- Update __all__ export list
```

### Phase 7: Validation (10 minutes)

#### 7.1 Line Count Verification
```bash
# MUST show ~30% reduction:
wc -l src/shard_markdown/cli/commands/*.py | tail -1
# Expected: ~950 lines (from 1,367)
```

#### 7.2 Test Execution
```bash
# ALL must pass:
uv run pytest tests/unit/cli/ -v
uv run pytest tests/e2e/ -v
uv run pre-commit run --all-files
uv run mypy src/shard_markdown/cli/
```

#### 7.3 Command Verification
```bash
# Test new commands:
uv run shard-md data list
uv run shard-md data --help

# Test deprecated aliases:
uv run shard-md collections --help  # Should show warning
uv run shard-md query --help        # Should show warning
```

---

## Success Criteria (ALL MANDATORY)

### Quantitative Metrics
- [ ] Line count: 1,367 → ~950 lines (30% reduction) ✅
- [ ] Module count: 4 → 3 (excluding __init__.py) ✅
- [ ] Command nesting: Max 2 levels ✅
- [ ] File modifications: ≤11 files ✅

### Functional Requirements
- [ ] All 98 unit tests passing ✅
- [ ] All E2E tests passing (including fixed test) ✅
- [ ] Backward compatibility aliases working ✅
- [ ] Deprecation warnings displayed ✅
- [ ] All original functionality preserved ✅

### Quality Requirements
- [ ] `uv run pre-commit run --all-files` - PASS ✅
- [ ] `uv run mypy src/shard_markdown/cli/` - PASS ✅
- [ ] `uv run ruff check src/shard_markdown/cli/` - PASS ✅

---

## STOP Conditions

**IMMEDIATELY STOP if:**
1. Attempting to modify any file not in the allowed list
2. Line count reduction cannot be achieved without breaking functionality
3. Tests fail after modifications and cannot be fixed
4. Pre-commit checks fail repeatedly
5. Any scope creep beyond Issue #168 requirements

---

## Post-Completion Actions

1. **Update Knowledge Graph**:
```python
add_observations(
    observations=[{
        "entityName": "Issue_168_Completion_Summary",
        "observations": [
            f"Corrected implementation: {date}",
            f"Line reduction achieved: 1367 → {actual} lines",
            "Backward compatibility aliases added",
            "All tests passing including E2E",
            f"Files modified: {count}/11"
        ]
    }],
    project_id="shard_markdown"
)
```

2. **Git Commit Message**:
```
fix: complete Issue #168 CLI simplification with line reduction

- Achieved 30% line reduction target (1367 → ~950 lines)
- Added backward compatibility aliases for collections/query commands
- Fixed failing E2E test for deprecated commands
- Optimized data.py consolidation to reduce code duplication
- Updated __init__.py and utils.py as required
- All 98 unit tests and 22 E2E tests passing
```

---

## Execution Mode
**ULTRA-STRICT**: Zero tolerance for deviations. Follow instructions exactly.
**Time Limit**: 2 hours maximum
**Priority**: Line reduction > Backward compatibility > Test fixes
**Validation**: Every phase must be validated before proceeding

---

**BEGIN IMPLEMENTATION IMMEDIATELY**
