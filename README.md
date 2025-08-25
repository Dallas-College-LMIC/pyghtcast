# Pyghtcast

A Python wrapper for the Lightcast API, providing simplified access to labor market data and skills classification.

Borrows heavily from [EmsiApiPy](https://github.com/calebjcourtney/EmsiApiPy/tree/master).

## Installation

```bash
pip install git+https://github.com/Dallas-College-LMIC/pyghtcast
```

## Quick Start

```python
from pyghtcast.lightcast import Lightcast

# Initialize with your credentials
lc = Lightcast(username="your_username", password="your_password")

# Build a query for occupation data
cols = ["Jobs.2023", "Openings.2023", "Replacements.2023"]
constraints = [
    {
        "dimensionName": "Area",
        "map": {"Dallas-Fort Worth-Arlington, TX": ["MSA19100"]}
    },
    {
        "dimensionName": "Occupation",
        "mapLevel": {"level": 5, "predicate": ["00-0000"]}
    }
]

query = lc.build_query_corelmi(cols, constraints)
df = lc.query_corelmi('emsi.us.occupation', query, datarun="2025.3")
```

## Features

### Core LMI (Labor Market Intelligence) API

The main `Lightcast` class provides access to Lightcast's Core LMI datasets:

#### Basic Usage

```python
from pyghtcast.lightcast import Lightcast

# Initialize client
lc = Lightcast(username="your_username", password="your_password")

# Get available datasets and metadata
meta_info = lc.conn.get_meta()
datasets = lc.conn.get_meta_definitions()

# Get specific dataset information
dataset_info = lc.conn.get_meta_dataset("emsi.us.occupation", "2025.3")
```

#### Building Queries

The library simplifies query construction by abstracting the JSON structure required by the API:

```python
# Define columns (metrics) you want
columns = [
    "Jobs.2023",
    "Openings.2023", 
    "Replacements.2023",
    "MeanEarnings.2023"
]

# Define constraints to filter data
constraints = [
    # Geographic filter
    {
        "dimensionName": "Area",
        "map": {
            "Dallas-Fort Worth-Arlington, TX": ["MSA19100"]
        }
    },
    # Occupation filter - all 5-digit SOC codes
    {
        "dimensionName": "Occupation",
        "mapLevel": {"level": 5, "predicate": ["00-0000"]}
    }
]

# Build and execute query
query = lc.build_query_corelmi(columns, constraints)
df = lc.query_corelmi('emsi.us.occupation', query, datarun="2025.3")
```

#### Working with Time Series Data

For time series data across multiple years:

```python
start_year = 2020
end_year = 2025
metrics = ["Jobs", "Openings", "Replacements"]

# Generate column list for all years
columns = []
for year in range(start_year, end_year + 1):
    for metric in metrics:
        columns.append(f"{metric}.{year}")

# Query with the columns
query = lc.build_query_corelmi(columns, constraints)
df = lc.query_corelmi('emsi.us.occupation', query)
```

#### Available Dimensions for Filtering

Common dimensions you can filter on:
- `Area`: Geographic regions (MSA, State, County, etc.)
- `Occupation`: SOC occupation codes
- `Industry`: NAICS industry codes
- `Education`: Education levels
- `Experience`: Experience levels

### Skills Classification API

Access Lightcast's Skills Classification system:

```python
from pyghtcast.lightcast import Skills

# Initialize Skills client
skills = Skills(username="your_username", password="your_password")

# Get all available versions
versions = skills.conn.get_versions()

# Get metadata for latest version
metadata = skills.conn.get_version_metadata(version="latest")

# Search for skills
results = skills.conn.get_list_all_skills(
    version="latest",
    q="python programming"  # Search query
)

# Get specific skill by ID
skill_info = skills.conn.get_skill_by_id("KS125QC6K0QLLKCTPJQ0", version="latest")

# Find related skills
related = skills.conn.post_find_related_skills(
    skill_ids=["KS125QC6K0QLLKCTPJQ0"],
    limit=10,
    version="latest"
)

# Extract skills from text
job_description = "Looking for a Python developer with experience in Django and PostgreSQL..."
extracted_skills = skills.conn.post_extract(
    description=job_description,
    version="latest",
    confidenceThreshold=0.5
)

# Extract skills with source tracking
skills_with_source = skills.conn.post_extract_with_source(
    description=job_description,
    version="latest",
    includeNormalizedText=True
)
```

## Advanced Usage

### Custom Queries with DataFrame Output

All query methods return pandas DataFrames for easy data manipulation:

```python
# Query Core LMI data
df = lc.query_corelmi('emsi.us.occupation', query, datarun="2025.3")

# The returned DataFrame can be manipulated with pandas
# Filter high-growth occupations
high_growth = df[df['Jobs.2025'] > df['Jobs.2023'] * 1.1]

# Calculate growth rates
df['growth_rate'] = (df['Jobs.2025'] - df['Jobs.2023']) / df['Jobs.2023'] * 100
```

### Getting Dimension Hierarchies

Explore available values for filtering:

```python
# Get hierarchy for a dimension (e.g., all occupation codes)
hierarchy_df = lc.conn.get_dimension_hierarchy_df(
    dataset="emsi.us.occupation",
    dimension="Occupation", 
    datarun="2025.3"
)
```

### Rate Limiting

The library includes automatic rate limiting to prevent hitting API limits:
- Implements smart limiting to evenly distribute requests
- Automatically handles quota resets
- Maximum 300 requests per 5-minute window

### Environment Variables

For security, store credentials in environment variables:

```python
import os
from pyghtcast.lightcast import Lightcast

user = os.environ.get("LCAPI_USER")
pwd = os.environ.get("LCAPI_PASS")

lc = Lightcast(user, pwd)
```

## API Datasets

Common datasets available through the Core LMI API:
- `emsi.us.occupation`: Occupation-level employment data
- `emsi.us.industry`: Industry-level employment data  
- `emsi.us.occupation.education`: Occupation by education level
- `emsi.us.occupation.demographics`: Occupation demographics

Check available datasets for your account:
```python
datasets = lc.conn.get_meta_definitions()
```

## Complete Example

See the [Jupyter notebook demo](pyghtcast/examples/Lightcast%20API%20Occupations%20Demo.ipynb) for a comprehensive example showing how to:
1. Build complex queries with multiple constraints
2. Query occupation data for specific geographies
3. Work with time series data across multiple years
4. Process and analyze the returned data

## Error Handling

The library will print error details when API calls fail:
```python
# If a query fails, it will print:
# - The JSON payload sent
# - The URL endpoint
# - The error response text
```

## Requirements

- Python 3.7+
- pandas
- requests

## License

Provided as-is. See repository for license details
