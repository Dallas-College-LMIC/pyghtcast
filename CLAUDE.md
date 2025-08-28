# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running Code
```bash
# Run any Python file with UV
uv run python pyghtcast/examples.py

# Run with additional packages
uv run --with jupyter python script.py
```

### Code Quality (Run After Changes)
```bash
# Lint and auto-fix issues
uv run --with ruff ruff check . --fix

# Format code
uv run --with ruff ruff format .

# Type checking
uv run --with mypy mypy pyghtcast

# All checks in one command
uv run --with ruff ruff check . && uv run --with ruff ruff format . && uv run --with mypy mypy pyghtcast
```

### Testing
```bash
# Run all tests with coverage
uv run --with pytest --with pytest-cov pytest

# Run specific test
uv run --with pytest pytest tests/unit/test_file.py::test_function

# Note: Currently no tests exist - add tests in tests/unit/ or tests/integration/
```

## Architecture Overview

The codebase follows a layered architecture for interacting with the Lightcast API:

```
pyghtcast/
├── base.py              # Base connection classes with authentication
├── coreLmi.py           # Core LMI API with rate limiting (300 req/5min)
├── openSkills.py        # Skills Classification API
├── lightcast.py         # Public interface (Lightcast, Skills classes)
└── examples/            # Usage examples
```

### Key Components

1. **Authentication Flow**:
   - `Token` class in `base.py` handles OAuth2 authentication
   - Automatic token refresh before expiration
   - Credentials from environment variables (`LCAPI_USER`, `LCAPI_PASS`)

2. **Rate Limiting**:
   - `Limiter` class in `coreLmi.py` manages API quotas
   - 300 requests per 5-minute window
   - Automatic throttling to prevent hitting limits

3. **Query Building**:
   - `build_query_corelmi()` method constructs JSON queries
   - Supports dimensions (Area, Occupation, Industry)
   - Returns pandas DataFrames for easy data manipulation

## Code Style Requirements

- **Python 3.13+** with modern features
- **Line length**: 120 characters max
- **Quotes**: Double quotes for strings (enforced by ruff)
- **Type hints**: Add for parameters and return types
- **Naming**:
  - Classes: PascalCase (`CoreLMIConnection`)
  - Functions/variables: snake_case (`get_new_token`)
  - Files: snake_case (`coreLmi.py`)

## Important Patterns

### DataFrame Returns
All query methods return pandas DataFrames:
```python
df = lc.query_corelmi('emsi.us.occupation', query, datarun="2025.3")
```

### Error Handling
Print detailed debugging info on API failures:
```python
print("Payload:", json.dumps(payload))
print("URL:", url)
print("Error:", response.text)
```

### Test-Driven Development
Follow Red-Green-Refactor when implementing new features:
1. Write failing test first
2. Implement to make test pass
3. Refactor while keeping tests green

Note: Test infrastructure exists but no tests are currently written. Add tests in `tests/unit/` or `tests/integration/`.
