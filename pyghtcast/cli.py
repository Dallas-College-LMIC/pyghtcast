#!/usr/bin/env python3
"""Command-line interface for pyghtcast library."""

import json
import os
import sys
import textwrap

import click

from .coreLmi import CoreLMIConnection


def get_connection() -> CoreLMIConnection:
    """Get a CoreLMIConnection instance using environment variables."""
    username = os.getenv("LCAPI_USER")
    password = os.getenv("LCAPI_PASS")

    if not username or not password:
        click.echo("Error: Please set LCAPI_USER and LCAPI_PASS environment variables", err=True)
        sys.exit(1)

    try:
        return CoreLMIConnection(username, password)
    except Exception as e:
        click.echo(f"Error connecting to API: {e}", err=True)
        sys.exit(1)


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """pyghtcast - Command-line interface for Lightcast API discovery and querying."""
    pass


@cli.group()
def discover() -> None:
    """Discover available datasets, dimensions, and hierarchies."""
    pass


@discover.command(name="datasets")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--descriptions", "-d", is_flag=True, help="Include full dataset descriptions")
def discover_datasets(output_json: bool, descriptions: bool) -> None:
    """List all available datasets and their versions."""
    conn = get_connection()

    try:
        # Use the definitions endpoint for richer data
        definitions = conn.get_meta_definitions()

        if output_json:
            click.echo(json.dumps(definitions, indent=2))
        else:
            click.echo("\n=== Available Datasets ===\n")

            # Handle the response based on its structure
            if isinstance(definitions, dict) and "datasets" in definitions:
                datasets = definitions["datasets"]

                if isinstance(datasets, list):
                    for dataset_info in datasets:
                        if isinstance(dataset_info, dict) and "name" in dataset_info:
                            dataset_name = dataset_info["name"]

                            # Dataset name
                            click.echo(f"{click.style(dataset_name, bold=True, fg='cyan')}")

                            # Title (if available)
                            if "title" in dataset_info:
                                click.echo(f"  {dataset_info['title']}")

                            # Versions
                            if "versions" in dataset_info:
                                versions = dataset_info["versions"]
                                if isinstance(versions, list):
                                    version_str = ", ".join(versions[:5])
                                    if len(versions) > 5:
                                        version_str += f" ... (+{len(versions) - 5} more)"
                                    click.echo(f"  Versions: {version_str}")

                            # Description (if flag is set)
                            if descriptions and "description" in dataset_info:
                                desc = dataset_info["description"]
                                # Extract the complete description paragraph(s) from the first section
                                lines = desc.split("\n")
                                description_lines = []
                                in_description = False

                                for line in lines:
                                    # Start capturing after "# Description" header
                                    if line.strip().startswith("# Description"):
                                        in_description = True
                                        continue
                                    # Stop at the next section header
                                    elif line.strip().startswith("#") and in_description:
                                        break
                                    # Capture non-empty lines in the description section
                                    elif in_description and line.strip():
                                        description_lines.append(line.strip())

                                # Join the description lines into a paragraph
                                if description_lines:
                                    summary = " ".join(description_lines)
                                    # Wrap long descriptions for better terminal display
                                    wrapped = textwrap.fill(
                                        summary,
                                        width=100,
                                        initial_indent="  Description: ",
                                        subsequent_indent="              ",
                                    )
                                    click.echo(wrapped)

                            click.echo()
                elif isinstance(datasets, dict):
                    # Handle dict format
                    for dataset_name, dataset_info in datasets.items():
                        click.echo(f"{click.style(dataset_name, bold=True, fg='cyan')}")

                        if isinstance(dataset_info, dict):
                            # Title (if available)
                            if "title" in dataset_info:
                                click.echo(f"  {dataset_info['title']}")

                            # Versions
                            if "versions" in dataset_info:
                                versions = dataset_info["versions"]
                                if isinstance(versions, list):
                                    version_str = ", ".join(versions[:5])
                                    if len(versions) > 5:
                                        version_str += f" ... (+{len(versions) - 5} more)"
                                    click.echo(f"  Versions: {version_str}")

                            # Description (if flag is set)
                            if descriptions and "description" in dataset_info:
                                desc = dataset_info["description"]
                                # Extract the complete description paragraph(s) from the first section
                                lines = desc.split("\n")
                                description_lines = []
                                in_description = False

                                for line in lines:
                                    # Start capturing after "# Description" header
                                    if line.strip().startswith("# Description"):
                                        in_description = True
                                        continue
                                    # Stop at the next section header
                                    elif line.strip().startswith("#") and in_description:
                                        break
                                    # Capture non-empty lines in the description section
                                    elif in_description and line.strip():
                                        description_lines.append(line.strip())

                                # Join the description lines into a paragraph
                                if description_lines:
                                    summary = " ".join(description_lines)
                                    # Wrap long descriptions for better terminal display
                                    wrapped = textwrap.fill(
                                        summary,
                                        width=100,
                                        initial_indent="  Description: ",
                                        subsequent_indent="              ",
                                    )
                                    click.echo(wrapped)

                        click.echo()
                else:
                    # Unknown format, show raw data
                    click.echo(json.dumps(definitions, indent=2))
            else:
                # Unknown structure, show raw
                click.echo("Raw API response:")
                click.echo(json.dumps(definitions, indent=2))

    except Exception as e:
        click.echo(f"Error fetching datasets: {e}", err=True)
        sys.exit(1)


@discover.command(name="dimensions")
@click.option("--dataset", required=True, help="Dataset name (e.g., emsi.us.occupation)")
@click.option("--datarun", required=True, help="Data version (e.g., 2025.3)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def discover_dimensions(dataset: str, datarun: str, output_json: bool) -> None:
    """List available dimensions for a specific dataset."""
    conn = get_connection()

    try:
        dataset_info = conn.get_meta_dataset(dataset, datarun)

        if output_json:
            click.echo(json.dumps(dataset_info, indent=2))
        else:
            click.echo(f"\n=== Dimensions for {click.style(dataset, bold=True, fg='cyan')} ({datarun}) ===\n")

            # Show dataset attributes if available
            if "attributes" in dataset_info and isinstance(dataset_info["attributes"], dict):
                attrs = dataset_info["attributes"]
                if "displayName" in attrs:
                    click.echo(f"Dataset: {attrs['displayName']}")
                if "currentYear" in attrs:
                    click.echo(f"Current Year: {attrs['currentYear']}")
                click.echo()

            # Extract dimensions (list format)
            if "dimensions" in dataset_info and isinstance(dataset_info["dimensions"], list):
                click.echo(f"{click.style('Dimensions:', bold=True)}")
                for dim in dataset_info["dimensions"]:
                    if isinstance(dim, dict) and "name" in dim:
                        dim_name = dim["name"]
                        click.echo(f"  - {dim_name}")
                        if "levelsStored" in dim:
                            click.echo(f"    Levels: {dim['levelsStored']}")
                click.echo()

            # Extract dimensions (dict format - old)
            elif "dimensions" in dataset_info and isinstance(dataset_info["dimensions"], dict):
                click.echo(f"{click.style('Dimensions:', bold=True)}")
                for dim_name, dim_info in dataset_info["dimensions"].items():
                    click.echo(f"  - {dim_name}")
                    if isinstance(dim_info, dict):
                        if "title" in dim_info:
                            click.echo(f"    Title: {dim_info['title']}")
                        if "description" in dim_info:
                            click.echo(f"    Description: {dim_info['description']}")
                        if "hierarchyLevels" in dim_info:
                            levels = dim_info["hierarchyLevels"]
                            click.echo(f"    Hierarchy levels: {levels}")
                click.echo()

            # Extract metrics (list format)
            if "metrics" in dataset_info and isinstance(dataset_info["metrics"], list):
                click.echo(f"{click.style('Available Metrics:', bold=True)}")
                for metric in dataset_info["metrics"]:
                    if isinstance(metric, dict) and "name" in metric:
                        click.echo(f"  - {metric['name']}")
                click.echo()

            # Extract metrics (dict format - old)
            elif "metrics" in dataset_info and isinstance(dataset_info["metrics"], dict):
                click.echo(f"{click.style('Available Metrics:', bold=True)}")
                for metric_name, metric_info in dataset_info["metrics"].items():
                    if isinstance(metric_info, dict) and "title" in metric_info:
                        click.echo(f"  - {metric_name}: {metric_info['title']}")
                    else:
                        click.echo(f"  - {metric_name}")
                click.echo()

    except Exception as e:
        click.echo(f"Error fetching dimensions: {e}", err=True)
        sys.exit(1)


@discover.command(name="hierarchy")
@click.option("--dataset", required=True, help="Dataset name (e.g., emsi.us.occupation)")
@click.option("--dimension", required=True, help="Dimension name (e.g., Area, Occupation)")
@click.option("--datarun", required=True, help="Data version (e.g., 2025.3)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--csv", "output_csv", is_flag=True, help="Output as CSV")
@click.option("--limit", default=20, help="Limit number of items shown (default: 20)")
def discover_hierarchy(
    dataset: str, dimension: str, datarun: str, output_json: bool, output_csv: bool, limit: int
) -> None:
    """View the hierarchy of a specific dimension."""
    conn = get_connection()

    try:
        if output_csv:
            # Use DataFrame method for CSV output
            df = conn.get_dimension_hierarchy_df(dataset, dimension, datarun)

            # Limit the output if specified
            if limit > 0 and len(df) > limit:
                df = df.head(limit)
                click.echo(f"# Showing first {limit} items", err=True)

            click.echo(df.to_csv(index=False))
        else:
            hierarchy_data = conn.get_meta_dataset_dimension(dataset, dimension, datarun)

            if output_json:
                click.echo(json.dumps(hierarchy_data, indent=2))
            else:
                click.echo(
                    f"\n=== Hierarchy for {click.style(dimension, bold=True, fg='cyan')} in {dataset} ({datarun}) ===\n"
                )

                if isinstance(hierarchy_data, dict) and "hierarchy" in hierarchy_data:
                    items = hierarchy_data["hierarchy"]

                    # Show hierarchy structure
                    shown = 0
                    for item in items:
                        if limit > 0 and shown >= limit:
                            remaining = len(items) - shown
                            click.echo(f"\n... and {remaining} more items")
                            break

                        if isinstance(item, dict):
                            # Try different keys for level
                            if "level" in item:
                                level = item.get("level", 0)
                            elif "level_name" in item:
                                level = int(item.get("level_name", "0")) - 1
                            else:
                                level = 0

                            indent = "  " * level
                            name = item.get("name", "Unknown")
                            # Try different keys for ID
                            code = item.get("display_id") or item.get("child") or item.get("id", "")

                            # Format output based on level
                            if level == 0:
                                click.echo(f"{indent}{click.style(name, bold=True)} [{code}]")
                            else:
                                click.echo(f"{indent}  {name} [{code}]")

                            shown += 1
                    click.echo()
                else:
                    click.echo(json.dumps(hierarchy_data, indent=2))

    except Exception as e:
        click.echo(f"Error fetching hierarchy: {e}", err=True)
        sys.exit(1)


@cli.group()
def query() -> None:
    """Build and execute queries."""
    pass


@query.command(name="build")
@click.option("--dataset", required=True, help="Dataset name (e.g., emsi.us.occupation)")
@click.option("--datarun", default="2025.3", help="Data version (default: 2025.3)")
def query_build(dataset: str, datarun: str) -> None:
    """Interactive query builder (coming soon)."""
    click.echo(f"\nInteractive query builder for {dataset} ({datarun})")
    click.echo("This feature is coming soon!")
    click.echo("\nFor now, you can use the discover commands to explore available data:")
    click.echo("  - pyghtcast discover dimensions --dataset <dataset> --datarun <version>")
    click.echo("  - pyghtcast discover hierarchy --dataset <dataset> --dimension <dim> --datarun <version>")


@query.command(name="example")
@click.option(
    "--dataset", type=click.Choice(["occupation", "industry"]), default="occupation", help="Example dataset type"
)
def query_example(dataset: str) -> None:
    """Show example queries for common use cases."""
    if dataset == "occupation":
        click.echo("\n=== Example Occupation Query ===\n")
        click.echo("""from pyghtcast.lightcast import Lightcast

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
""")
    else:
        click.echo("\n=== Example Industry Query ===\n")
        click.echo("""from pyghtcast.lightcast import Lightcast

lc = Lightcast(username="your_username", password="your_password")

# Define columns to retrieve
cols = ["Jobs.2023", "Jobs.2024", "Jobs.2033", "Location Quotient.2023"]

# Define constraints (e.g., for specific area and industry)
constraints = [
    {
        "dimensionName": "Area",
        "mapLevel": {
            "level": 4,
            "predicate": ["48113", "48085", "48121"]  # Multiple counties
        }
    },
    {
        "dimensionName": "Industry",
        "mapLevel": {
            "level": 2,
            "predicate": ["54"]  # Professional, Scientific, and Technical Services
        }
    }
]

query = lc.build_query_corelmi(cols=cols, constraints=constraints)
df = lc.query_corelmi(dataset="emsi.us.industry", query=query, datarun="2025.3")
print(df)
""")


if __name__ == "__main__":
    cli()
