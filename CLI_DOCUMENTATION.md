# Pyghtcast CLI Documentation

The `pyghtcast` CLI provides a command-line interface for discovering and querying Lightcast API datasets directly from your terminal.

## Table of Contents
- [Installation](#installation)
- [Authentication](#authentication)
- [Command Overview](#command-overview)
- [Discovery Commands](#discovery-commands)
  - [List Datasets](#list-datasets)
  - [List Dimensions](#list-dimensions)
  - [View Dimension Hierarchy](#view-dimension-hierarchy)
- [Query Commands](#query-commands)
  - [View Query Examples](#view-query-examples)
- [Common Workflows](#common-workflows)
- [Output Formats](#output-formats)
- [Troubleshooting](#troubleshooting)

## Installation

The CLI is automatically available after installing pyghtcast:

```bash
# Install from GitHub
pip install git+https://github.com/Dallas-College-LMIC/pyghtcast

# Or with UV
uv pip install git+https://github.com/Dallas-College-LMIC/pyghtcast
```

## Authentication

The CLI requires Lightcast API credentials. You can provide them in two ways:

### Method 1: Environment Variables (Recommended)

Set your credentials as environment variables:

```bash
export LCAPI_USER="your_username"
export LCAPI_PASS="your_password"
```

Add these to your `.bashrc`, `.zshrc`, or `.env` file for persistence.

### Method 2: Credentials File

Create a `.env` file in your project directory:

```bash
LCAPI_USER=your_username
LCAPI_PASS=your_password
```

The CLI will automatically load credentials from environment variables when you run any command.

## Command Overview

The CLI is organized into two main command groups:

```bash
# View CLI help and version
pyghtcast --help
pyghtcast --version

# Discovery commands - explore available data
pyghtcast discover datasets     # List all available datasets
pyghtcast discover dimensions   # List dimensions for a dataset
pyghtcast discover hierarchy    # View hierarchy of a dimension

# Query commands - build and execute queries
pyghtcast query example         # Show example queries
pyghtcast query build          # Interactive query builder (coming soon)
```

## Discovery Commands

### List Datasets

Discover all available datasets in your Lightcast subscription:

```bash
# Basic listing
pyghtcast discover datasets

# Output as JSON for processing
pyghtcast discover datasets --json

# Include full dataset descriptions
pyghtcast discover datasets --descriptions
pyghtcast discover datasets -d
```

**Example Output:**
```
=== Available Datasets ===

emsi.us.occupation
  US Occupation Data
  Versions: 2025.3, 2025.2, 2025.1, 2024.4, 2024.3 ... (+12 more)

emsi.us.industry
  US Industry Data
  Versions: 2025.3, 2025.2, 2025.1, 2024.4, 2024.3 ... (+12 more)

emsi.us.occupation.education
  US Occupation by Education Level
  Versions: 2025.3, 2025.2, 2025.1, 2024.4, 2024.3 ... (+12 more)
```

With descriptions flag:
```bash
pyghtcast discover datasets -d
```
```
emsi.us.occupation
  US Occupation Data
  Versions: 2025.3, 2025.2, 2025.1, 2024.4, 2024.3 ... (+12 more)
  Description: Provides detailed occupation-level employment data including jobs, openings,
              replacements, and earnings across all US geographies and time periods.
```

### List Dimensions

View available dimensions (filters) for a specific dataset:

```bash
# List dimensions for a dataset
pyghtcast discover dimensions emsi.us.occupation

# Specify a particular version
pyghtcast discover dimensions emsi.us.occupation --version 2025.3

# Output as JSON
pyghtcast discover dimensions emsi.us.occupation --json

# Include dimension metadata
pyghtcast discover dimensions emsi.us.occupation --metadata
```

**Example Output:**
```
=== Dimensions for emsi.us.occupation (2025.3) ===

Area
  Type: Hierarchy
  Levels: Nation (1), State (2), MSA (3), County (4)

Occupation
  Type: Hierarchy
  Levels: Major Group (2), Minor Group (3), Broad (4), Detailed (5), Extended (6)

Education
  Type: Categorical
  Values: High School, Associate's, Bachelor's, Master's, Doctoral
```

### View Dimension Hierarchy

Explore the hierarchical structure of a dimension to find valid filter values:

```bash
# View occupation hierarchy
pyghtcast discover hierarchy emsi.us.occupation Occupation

# View area hierarchy
pyghtcast discover hierarchy emsi.us.occupation Area

# Filter to specific level
pyghtcast discover hierarchy emsi.us.occupation Occupation --level 2

# Search for specific values
pyghtcast discover hierarchy emsi.us.occupation Occupation --search "computer"

# Output as JSON
pyghtcast discover hierarchy emsi.us.occupation Area --json
```

**Example Output:**
```
=== Hierarchy for Occupation in emsi.us.occupation ===

Level 2 - Major Groups:
  11-0000: Management Occupations
  13-0000: Business and Financial Operations Occupations
  15-0000: Computer and Mathematical Occupations
  17-0000: Architecture and Engineering Occupations
  19-0000: Life, Physical, and Social Science Occupations
  ...

Level 5 - Detailed Occupations (filtered: computer):
  15-1211: Computer Systems Analysts
  15-1212: Information Security Analysts
  15-1221: Computer and Information Research Scientists
  15-1231: Computer Network Support Specialists
  15-1232: Computer User Support Specialists
  ...
```

## Query Commands

### View Query Examples

Get example code for common query patterns:

```bash
# Show occupation query example
pyghtcast query example --dataset occupation

# Show industry query example
pyghtcast query example --dataset industry
```

**Example Output:**
```python
=== Example Occupation Query ===

from pyghtcast.lightcast import Lightcast

lc = Lightcast(username="your_username", password="your_password")

# Define columns to retrieve
cols = ["Jobs.2022", "ResidenceJobs.2022", "MedianHourlyEarnings.2022"]

# Define constraints (e.g., for a specific area and occupation group)
constraints = [
    {
        "dimensionName": "Area",
        "mapLevel": {
            "level": 4,
            "predicate": ["48113"]  # Dallas County FIPS code
        }
    },
    {
        "dimensionName": "Occupation",
        "mapLevel": {
            "level": 2,
            "predicate": ["15-0000"]  # Computer and Mathematical Occupations
        }
    }
]

query = lc.build_query_corelmi(cols=cols, constraints=constraints)
df = lc.query_corelmi(dataset="emsi.us.occupation", query=query, datarun="2025.3")
print(df)
```

## Common Workflows

### 1. Explore Available Data

Start by discovering what datasets and dimensions are available:

```bash
# See all datasets
pyghtcast discover datasets

# Pick a dataset and explore its dimensions
pyghtcast discover dimensions emsi.us.occupation

# Find specific area codes
pyghtcast discover hierarchy emsi.us.occupation Area --search "Dallas"

# Find occupation codes
pyghtcast discover hierarchy emsi.us.occupation Occupation --level 2
```

### 2. Build Queries from CLI Examples

Use the CLI to generate query templates:

```bash
# Get example code
pyghtcast query example --dataset occupation > my_query.py

# Edit the generated file with your specific parameters
# Then run it
python my_query.py
```

### 3. JSON Output for Scripting

Use JSON output for automation and scripting:

```bash
# Get datasets as JSON
datasets=$(pyghtcast discover datasets --json)

# Process with jq or other tools
echo "$datasets" | jq '.datasets[].name'

# Save hierarchy for reference
pyghtcast discover hierarchy emsi.us.occupation Area --json > area_codes.json
```

### 4. Quick Reference Lookup

Create aliases for common lookups:

```bash
# Add to .bashrc or .zshrc
alias lc-datasets='pyghtcast discover datasets'
alias lc-areas='pyghtcast discover hierarchy emsi.us.occupation Area'
alias lc-occupations='pyghtcast discover hierarchy emsi.us.occupation Occupation'

# Usage
lc-occupations --search "software"
```

## Output Formats

The CLI supports two output formats:

### Human-Readable (Default)

Formatted text output with colors and structure, optimized for terminal reading:
- Dataset names in cyan
- Clear hierarchical indentation
- Wrapped descriptions for readability
- Progress indicators for long operations

### JSON Format

Machine-readable JSON for scripting and automation:

```bash
# Any discovery command supports --json flag
pyghtcast discover datasets --json
pyghtcast discover dimensions emsi.us.occupation --json
pyghtcast discover hierarchy emsi.us.occupation Area --json
```

Pipe to `jq` for processing:
```bash
# Get just dataset names
pyghtcast discover datasets --json | jq -r '.datasets[].name'

# Count available versions
pyghtcast discover datasets --json | jq '.datasets[0].versions | length'
```

## Troubleshooting

### Authentication Errors

If you get authentication errors:

1. Verify credentials are set:
```bash
echo $LCAPI_USER
echo $LCAPI_PASS
```

2. Test credentials with a simple command:
```bash
pyghtcast discover datasets
```

3. Check for typos in environment variable names (must be `LCAPI_USER` and `LCAPI_PASS`)

### Connection Issues

For connection or timeout errors:

1. Check your internet connection
2. Verify Lightcast API status
3. Try with `--json` flag for raw error details
4. Check if you're behind a proxy/firewall

### Rate Limiting

The CLI includes automatic rate limiting (300 requests per 5 minutes). If you hit limits:

1. Wait for the rate limit window to reset (5 minutes)
2. Use more specific queries to reduce API calls
3. Cache results using JSON output

### Missing Data

If datasets or dimensions appear empty:

1. Verify your subscription includes the dataset
2. Check the version is available: `pyghtcast discover datasets`
3. Try without version flag to use latest
4. Contact Lightcast support for subscription issues

## Advanced Usage

### Combining with Other Tools

The CLI works well with Unix tools:

```bash
# Find all occupation codes containing "engineer"
pyghtcast discover hierarchy emsi.us.occupation Occupation --json | \
  jq -r '.[] | select(.name | contains("Engineer")) | "\(.code): \(.name)"'

# Count datasets by type
pyghtcast discover datasets --json | \
  jq '.datasets | group_by(.type) | map({type: .[0].type, count: length})'

# Export specific columns to CSV
pyghtcast discover dimensions emsi.us.occupation --json | \
  jq -r '.dimensions[] | [.name, .type, .levels] | @csv' > dimensions.csv
```

### Scripting Examples

Create a script to monitor dataset updates:

```bash
#!/bin/bash
# check_versions.sh

current=$(pyghtcast discover datasets --json | jq -r '.datasets[0].versions[0]')
echo "Latest version: $current"

if [ "$current" != "$LAST_VERSION" ]; then
    echo "New version available!"
    # Send notification or trigger update process
fi
```

### Integration with Python Scripts

Use CLI output in Python:

```python
import subprocess
import json

# Get datasets from CLI
result = subprocess.run(
    ["pyghtcast", "discover", "datasets", "--json"],
    capture_output=True,
    text=True
)

datasets = json.loads(result.stdout)
for dataset in datasets["datasets"]:
    print(f"{dataset['name']}: {len(dataset['versions'])} versions")
```

## See Also

- [Main README](README.md) - Python API documentation
- [Examples](pyghtcast/examples/) - Jupyter notebooks with detailed examples
- [Lightcast API Documentation](https://api.lightcast.io/) - Official API reference
