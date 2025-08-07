# Type Safety Code Review Checklist

## Pre-Review Requirements

- [ ] **MyPy type checking passes locally** (`mypy src/`)
- [ ] **All Ruff checks pass** (`ruff check src/ tests/`)
- [ ] **Code formatting is correct** (`ruff format --check src/ tests/`)
- [ ] **Pre-commit hooks pass** (`pre-commit run --all-files`)
- [ ] **Verification script passes** (`python scripts/verify.py`)

## Critical Type Safety Patterns (CI/CD Blockers)

### 1. Optional/Union Attribute Access
**ANTI-PATTERN**: Accessing attributes on Optional types without None checks
```python
# ❌ WRONG - Will cause CI/CD failure
def process_result(result: Optional[Result]) -> str:
    return result.error.lower()  # result could be None, result.error could be None
```

**CORRECT PATTERN**: Always check for None before accessing attributes
```python  
# ✅ CORRECT - Safe attribute access
def process_result(result: Optional[Result]) -> str:
    if result is None:
        return "no result"
    if result.error is None:
        return "no error"
    return result.error.lower()

# ✅ ALSO CORRECT - Using walrus operator
def process_result(result: Optional[Result]) -> str:
    if result is None or (error := result.error) is None:
        return "no error"
    return error.lower()
```

**Review Questions:**
- [ ] Are all Optional attribute accesses protected with None checks?
- [ ] Are Union types properly handled with isinstance() checks?
- [ ] Are method calls on Optional types protected?

### 2. Fixture Parameter Typing  
**ANTI-PATTERN**: Missing type annotations on pytest fixture parameters
```python
# ❌ WRONG - Will cause CI/CD failure
@pytest.fixture
def sample_data(request) -> Dict[str, Any]:  # 'request' missing type
    return request.param
```

**CORRECT PATTERN**: Always type fixture parameters
```python
# ✅ CORRECT - Properly typed fixture
import pytest

@pytest.fixture
def sample_data(request: pytest.FixtureRequest) -> Dict[str, Any]:
    return request.param
```

**Review Questions:**
- [ ] Do all pytest fixtures have proper type annotations?
- [ ] Are fixture return types specified?
- [ ] Are parametrized fixtures properly typed?

### 3. Pydantic Decorator Issues
**ANTI-PATTERN**: Pydantic decorators causing type checking issues
```python
# ❌ WRONG - May cause CI/CD failure
@field_validator("field_name")
@classmethod
def validate_field(cls, v: str) -> str:
    return v.lower()
```

**CORRECT PATTERN**: Add type ignore for problematic decorators
```python
# ✅ CORRECT - Type ignore for Pydantic decorators
@field_validator("field_name")  # type: ignore[misc]
@classmethod  
def validate_field(cls, v: str) -> str:
    return v.lower()
```

**Review Questions:**
- [ ] Are Pydantic validators properly typed?
- [ ] Are type ignores used appropriately for decorator issues?
- [ ] Are custom validators following proper patterns?

### 4. Generator Return Types
**ANTI-PATTERN**: Missing Generator type annotations
```python
# ❌ WRONG - Will cause CI/CD failure
def data_generator():
    yield item
```

**CORRECT PATTERN**: Specify complete Generator types
```python
# ✅ CORRECT - Complete Generator typing
from typing import Generator

def data_generator() -> Generator[ItemType, None, None]:
    yield item
```

**Review Questions:**
- [ ] Do all generators have proper return type annotations?
- [ ] Are Generator types complete with [YieldType, SendType, ReturnType]?
- [ ] Are async generators properly typed with AsyncGenerator?

## General Type Safety Review Items

### Function Signatures
- [ ] All function parameters have type annotations
- [ ] All function return types are specified
- [ ] Complex types use proper imports (List, Dict, Optional, Union)
- [ ] Generic types are properly parameterized

### Error Handling
- [ ] Exception types are specific, not bare `except:`
- [ ] Custom exceptions inherit from appropriate base classes
- [ ] Error handling preserves type information

### Class Definitions
- [ ] All class attributes are typed (using ClassVar when appropriate)
- [ ] `__init__` methods have proper parameter typing
- [ ] Abstract methods are properly decorated and typed
- [ ] Properties have return type annotations

### Import Management
- [ ] Type-only imports use `from typing import TYPE_CHECKING`
- [ ] Circular import issues resolved with forward references
- [ ] All typing imports are present and minimal

### Documentation
- [ ] Complex type signatures are documented in docstrings
- [ ] Type relationships are explained when non-obvious
- [ ] Generic type constraints are documented

## MyPy Configuration Compliance

- [ ] Code follows strict MyPy settings in pyproject.toml:
  - `disallow_untyped_defs = true`
  - `disallow_incomplete_defs = true`
  - `no_implicit_optional = true`
  - `strict_equality = true`

- [ ] Any `# type: ignore` comments are:
  - Used sparingly and only when necessary
  - Include specific error codes (e.g., `# type: ignore[attr-defined]`)
  - Have explanatory comments when the reason isn't obvious

## Testing Type Safety

- [ ] Test functions have appropriate typing (can be relaxed per mypy config)
- [ ] Mock objects preserve type information where possible
- [ ] Parametrized tests handle type variations correctly
- [ ] Test fixtures follow typing patterns above

## Performance Considerations

- [ ] Type hints don't impact runtime performance unnecessarily
- [ ] Forward references used to avoid import cycles
- [ ] `from __future__ import annotations` used when beneficial

## Security Review

- [ ] Input validation maintains type safety
- [ ] Type narrowing is secure (no unchecked casts)
- [ ] External data parsing preserves type guarantees

## Final Validation Commands

Before approving the PR, verify these commands pass:

```bash
# Type checking (CRITICAL)
mypy src/

# Linting  
ruff check src/ tests/ scripts/

# Formatting
ruff format --check src/ tests/ scripts/

# Full verification
python scripts/verify.py --fast
```

## Anti-Pattern Examples from PR #49

Reference these specific patterns that were identified and fixed:

1. **Optional attribute access in validation.py**: Always check for None before accessing optional attributes
2. **Untyped fixture parameters**: All pytest fixtures must type their parameters
3. **Pydantic field validators**: Use `# type: ignore[misc]` for decorator typing issues
4. **Generator return types**: Specify complete Generator[YieldType, SendType, ReturnType] types

## Reviewer Signature

- [ ] **All type safety checks completed**
- [ ] **No CI/CD blocking issues identified** 
- [ ] **Type hints are accurate and helpful**
- [ ] **Code follows project type safety standards**

Reviewer: _________________  
Date: _________________