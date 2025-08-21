# Task: Complete Issue #167 - Eliminate ChunkingConfig Blocking Issue

## 🧠 Knowledge Base Usage Instructions

### MANDATORY: Before Starting
1. **Activate Knowledge System**: Start with "🧠 **Knowledge system activated**"
2. **Load Context**: Use `search_knowledge(query="Issue_167", project_id="shard_markdown")` to retrieve:
   - Full requirements from `Issue_167_Config_Consolidation`
   - Dependencies from `ChunkingConfig_Legacy`
   - Target structure from `Settings_Flat_Config`
   - Failure points from `PR_183_Critical_Review`

### MANDATORY: During Implementation
1. **Capture All Changes**: Document each file modification in knowledge graph
2. **Record Errors**: If any error occurs, create correction entity:
   ```python
   create_entities(entities=[{
     name: "Correction_Issue167_[ErrorType]",
     entityType: "preference",
     observations: [
       "Error: [What went wrong]",
       "Correction: [How it was fixed]",
       "File: [Which file had the issue]"
     ],
     tags: ["correction", "issue-167", "config-migration"]
   }])
   ```
3. **Track Progress**: Update observations on `Issue_167_Correction_Task` entity

### MANDATORY: After Completion
1. **Update Status**: Add final observations to `Issue_167_Config_Consolidation`
2. **Create Relations**: Link correction entities to main issue entity
3. **Document Success**: Record which approach worked for future reference

## Purpose
Complete the configuration consolidation by eliminating the ChunkingConfig class that blocks Issue #167 completion.

## Critical Checklist
- [ ] Remove ChunkingConfig class from models.py
- [ ] Update 5 source files to use Settings instead of ChunkingConfig
- [ ] Update 6 test files to use Settings
- [ ] Ensure all pre-commit checks pass
- [ ] Verify no other files are modified

## STRICT CONSTRAINTS
**⚠️ CRITICAL: Only modify the 11 files listed below. ANY other modifications are PROHIBITED.**

## Files Allowed for Modification (ONLY THESE)

### Source Files (5 files ONLY):
1. `src/shard_markdown/core/models.py` - DELETE ChunkingConfig class (lines 130-143)
2. `src/shard_markdown/core/processor.py` - Update imports and constructor
3. `src/shard_markdown/core/chunking/engine.py` - Update imports and constructor  
4. `src/shard_markdown/core/chunking/base.py` - Update to use Settings
5. `src/shard_markdown/cli/commands/process.py` - Update CLI to create Settings

### Test Files (6 files ONLY):
6. `tests/conftest.py` - Update fixtures (3 occurrences)
7. `tests/unit/core/test_processor.py` - Update mocks (3 occurrences)
8. `tests/unit/core/test_models.py` - Remove ChunkingConfig tests (6 occurrences)
9. `tests/performance/test_benchmarks.py` - Update benchmarks (15 occurrences)
10. `tests/unit/test_chunking.py` - Update tests (10 occurrences)
11. `tests/integration/test_document_processing.py` - Update integration (6 occurrences)

## Implementation Instructions

### Phase 1: Core Source Changes
1. **models.py**: 
   - DELETE entire ChunkingConfig class (lines 130-143)
   - DO NOT add any new code here

2. **processor.py**:
   - Remove: `from .models import ..., ChunkingConfig, ...`
   - Add: `from ..config.settings import Settings`
   - Change: `def __init__(self, chunking_config: ChunkingConfig)` 
   - To: `def __init__(self, settings: Settings)`
   - Update all `chunking_config.field` to `settings.chunk_field`

3. **engine.py**:
   - Remove: `from ..models import ChunkingConfig`
   - Add: `from ...config.settings import Settings`
   - Change: `def __init__(self, config: ChunkingConfig)`
   - To: `def __init__(self, settings: Settings)`
   - Update all `config.field` to `settings.chunk_field`

4. **base.py**:
   - Update any ChunkingConfig references to Settings
   - Update field access to use chunk_ prefix

5. **process.py** (CLI - USER FACING):
   - Add: `from ...config.settings import Settings`
   - Remove ChunkingConfig import
   - Replace (lines 146-148):
   ```python
   # OLD CODE TO REMOVE:
   processor = DocumentProcessor(
       ChunkingConfig(
           chunk_size=chunk_size, overlap=chunk_overlap, method=chunk_method
       )
   )
   
   # NEW CODE TO ADD:
   settings = Settings(
       chunk_size=chunk_size,
       chunk_overlap=chunk_overlap,
       chunk_method=chunk_method
   )
   processor = DocumentProcessor(settings)
   ```

### Phase 2: Test File Updates
For each test file, apply the field mapping:

| ChunkingConfig Field | Settings Field |
|---------------------|----------------|
| `chunk_size` | `chunk_size` |
| `overlap` | `chunk_overlap` |
| `method` | `chunk_method` |
| `respect_boundaries` | `chunk_respect_boundaries` |
| `max_tokens` | `chunk_max_tokens` |

### Phase 3: Validation

Run these commands in order:
```bash
# 1. Format check
uv run ruff format --check src/ tests/

# 2. Lint check
uv run ruff check src/ tests/

# 3. Type check
uv run mypy src/

# 4. Run tests
uv run pytest tests/unit/core/test_processor.py -xvs
uv run pytest tests/unit/test_chunking.py -xvs
```

## Success Criteria
1. ✅ ChunkingConfig class no longer exists
2. ✅ All 5 source files use Settings
3. ✅ All 6 test files updated (43 occurrences fixed)
4. ✅ Pre-commit checks pass (ruff, mypy)
5. ✅ Core tests pass
6. ✅ NO other files modified

## Validation Requirements
- Verify Settings has all required fields with chunk_ prefix
- Ensure backward compatibility is not needed (per Issue #167)
- Confirm single configuration paradigm achieved
- Test that CLI still functions correctly

## PROHIBITED ACTIONS
❌ DO NOT create new files
❌ DO NOT modify any file not in the 11-file list above
❌ DO NOT add backward compatibility layers
❌ DO NOT create adapter classes
❌ DO NOT modify configuration loader files
❌ DO NOT update documentation files
❌ DO NOT modify GitHub workflows

## Knowledge Graph References
- Entity: `Issue_167_Config_Consolidation` - Contains full requirements
- Entity: `ChunkingConfig_Legacy` - Lists all dependencies
- Entity: `Settings_Flat_Config` - Target configuration structure
- Entity: `PR_183_Critical_Review` - Lists failure points to address

## Final Verification
After all changes:
1. Run: `git status` - Should show ONLY 11 files modified
2. Run: `uv run pytest -x` - Core tests must pass
3. Run: `pre-commit run --all-files` - Must pass all checks

## Notes
- Settings already contains ALL required chunk_ fields
- Field mapping is direct (just add chunk_ prefix)
- This completes the 87.5% reduction target (8→1 config class)
- Fixes the dual configuration anti-pattern identified in PR #183

## Knowledge Management Requirements (from @guides/knowledge-based.md)

### Information Capture Priority
1. **HIGH VALUE - Must Capture**:
   - Each file modification and its impact
   - Any errors encountered and their solutions
   - Discovered dependencies not documented
   - Test failures and their fixes
   - Performance impacts observed

2. **Project ID**: Use `shard_markdown` consistently for all operations

3. **Search Before Create**: Always check existing entities:
   ```python
   # Check if entity exists before creating
   search_knowledge(query="ChunkingConfig_Migration", project_id="shard_markdown")
   ```

4. **Quality Standards**:
   - Entity names: Be specific (e.g., `Migration_Processor_To_Settings`)
   - Observations: Be factual (e.g., "Changed line 22 from ChunkingConfig to Settings")
   - Relations: Use active voice (e.g., `migration replaces legacy_config`)

### Error Learning Protocol
If you encounter ANY error during implementation:
1. Search for similar past errors
2. Create correction entity with solution
3. Tag with ["correction", "issue-167", "learning"]
4. Link to affected components

### Completion Documentation
Upon successful completion, create summary entity:
```python
create_entities(entities=[{
  name: "Issue_167_Completion_Summary",
  entityType: "event",
  observations: [
    "Completion date: [DATE]",
    "Files modified: 11 (5 source, 6 test)",
    "ChunkingConfig class: Eliminated",
    "Settings adoption: 100% complete",
    "Pre-commit status: Passing",
    "Test status: [X] passing, [Y] skipped"
  ],
  tags: ["completed", "issue-167", "success"]
}])