# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pyghtcast is a Python wrapper for the Lightcast API, providing simplified access to labor market data and skills classification. It borrows heavily from EmsiApiPy.

## Development Commands

### Package Management
- **Install dependencies**: `poetry install`
- **Add dependency**: `poetry add <package>`
- **Update dependencies**: `poetry update`

### Running Code
- **Run example**: `python -m pyghtcast.examples.skills_example`
- **Python REPL with package**: `poetry run python`

### Environment Setup
- **Required environment variables**:
  - `LCAPI_USER`: Lightcast API username
  - `LCAPI_PASS`: Lightcast API password

## Architecture

### Core Components

1. **Base Connection Layer** (`pyghtcast/base.py`):
   - `EmsiBaseConnection`: Base class for all API connections
   - `Token`: Token management with automatic expiration checking
   - Handles authentication, GET/POST requests, and error responses
   - Auto-refreshes tokens when expired

2. **Core LMI API** (`pyghtcast/coreLmi.py`):
   - `CoreLMIConnection`: Access to Lightcast's Core Labor Market Intelligence datasets
   - `Limiter`: Smart rate limiting (300 requests per 5-minute window)
   - Endpoints: meta data, dataset definitions, dimension hierarchies, data retrieval
   - Returns pandas DataFrames for easy manipulation

3. **Skills Classification API** (`pyghtcast/openSkills.py`):
   - `SkillsClassificationConnection`: Access to skills extraction and classification
   - Methods for skill search, extraction from text, related skills, version management

4. **Main Interface** (`pyghtcast/lightcast.py`):
   - `Lightcast`: Simplified interface for Core LMI queries
   - `Skills`: Simplified interface for Skills Classification
   - `build_query_corelmi()`: Helper to construct JSON queries from simple parameters

### API Interaction Pattern

1. Initialize connection with credentials → auto-fetches OAuth token
2. Build query using helper methods or raw JSON
3. Execute query against specific dataset/version
4. Receive pandas DataFrame or JSON response
5. Token auto-refreshes on expiration, rate limiting handled automatically

### Key Design Decisions

- **Token Management**: Tokens auto-refresh after 59 minutes
- **Rate Limiting**: Smart distribution of requests to avoid 429 errors
- **Error Handling**: Prints full request details on failure for debugging
- **DataFrame Returns**: Most methods return pandas DataFrames for easy data manipulation
- **Inheritance Structure**: All connections inherit from `EmsiBaseConnection` for consistent auth/request handling

## Testing Approach

When implementing new features or fixing bugs:
1. Test authentication first with valid credentials
2. Test against real API endpoints (no mocking framework present)
3. Verify rate limiting works correctly under load
4. Check DataFrame outputs match expected schema

## Common API Datasets

- `emsi.us.occupation`: Occupation-level employment data
- `emsi.us.industry`: Industry-level employment data
- `emsi.us.occupation.education`: Occupation by education level
- `emsi.us.occupation.demographics`: Occupation demographics

## API Versioning

- Always specify `datarun` parameter (e.g., "2025.3") for Core LMI queries
- Use "latest" for Skills Classification API unless specific version needed