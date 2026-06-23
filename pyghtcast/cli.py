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


# --- dataset rendering helpers (normalize list/dict API formats) ---


def _extract_description(desc: str) -> str:
    """Pull the first '# Description' section out of a markdown-ish API description."""
    lines_out = []
    in_description = False
    for line in desc.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# Description"):
            in_description = True
            continue
        if in_description and stripped.startswith("#"):
            break
        if in_description and stripped:
            lines_out.append(stripped)
    return " ".join(lines_out)


def _print_versions(versions: object) -> None:
    if isinstance(versions, list):
        version_str = ", ".join(versions[:5])
        if len(versions) > 5:
            version_str += f" ... (+{len(versions) - 5} more)"
        click.echo(f"  Versions: {version_str}")


def _print_description(info: dict, show: bool) -> None:
    if show and "description" in info:
        summary = _extract_description(info["description"])
        if summary:
            click.echo(
                textwrap.fill(
                    summary,
                    width=100,
                    initial_indent="  Description: ",
                    subsequent_indent="              ",
                )
            )


def _print_dataset_entry(name: str, info: dict, descriptions: bool) -> None:
    click.echo(f"{click.style(name, bold=True, fg='cyan')}")
    if isinstance(info, dict):
        if "title" in info:
            click.echo(f"  {info['title']}")
        if "versions" in info:
            _print_versions(info["versions"])
        _print_description(info, descriptions)
    click.echo()


def _iter_datasets(datasets: object) -> list[tuple[str, dict]]:
    """Normalize list/dict dataset formats into (name, info) pairs."""
    if isinstance(datasets, list):
        return [(d["name"], d) for d in datasets if isinstance(d, dict) and "name" in d]
    if isinstance(datasets, dict):
        return [(n, i if isinstance(i, dict) else {}) for n, i in datasets.items()]
    return []


# --- dimension/metric rendering helpers (list vs dict API formats) ---


def _print_attributes(dataset_info: dict) -> None:
    attrs = dataset_info.get("attributes")
    if not isinstance(attrs, dict):
        return
    if "displayName" in attrs:
        click.echo(f"Dataset: {attrs['displayName']}")
    if "currentYear" in attrs:
        click.echo(f"Current Year: {attrs['currentYear']}")
    click.echo()


def _print_dim_list(dims: list) -> None:
    for dim in dims:
        if isinstance(dim, dict) and "name" in dim:
            click.echo(f"  - {dim['name']}")
            if "levelsStored" in dim:
                click.echo(f"    Levels: {dim['levelsStored']}")


def _print_dim_dict(dims: dict) -> None:
    for dim_name, dim_info in dims.items():
        click.echo(f"  - {dim_name}")
        if isinstance(dim_info, dict):
            if "title" in dim_info:
                click.echo(f"    Title: {dim_info['title']}")
            if "description" in dim_info:
                click.echo(f"    Description: {dim_info['description']}")
            if "hierarchyLevels" in dim_info:
                click.echo(f"    Hierarchy levels: {dim_info['hierarchyLevels']}")


def _print_dimensions_section(dataset_info: dict) -> None:
    dims = dataset_info.get("dimensions")
    if not isinstance(dims, list | dict):
        return
    click.echo(f"{click.style('Dimensions:', bold=True)}")
    if isinstance(dims, list):
        _print_dim_list(dims)
    else:
        _print_dim_dict(dims)
    click.echo()


def _print_metrics_list(metrics: list) -> None:
    for metric in metrics:
        if isinstance(metric, dict) and "name" in metric:
            click.echo(f"  - {metric['name']}")


def _print_metrics_dict(metrics: dict) -> None:
    for metric_name, metric_info in metrics.items():
        if isinstance(metric_info, dict) and "title" in metric_info:
            click.echo(f"  - {metric_name}: {metric_info['title']}")
        else:
            click.echo(f"  - {metric_name}")


def _print_metrics_section(dataset_info: dict) -> None:
    metrics = dataset_info.get("metrics")
    if not isinstance(metrics, list | dict):
        return
    click.echo(f"{click.style('Available Metrics:', bold=True)}")
    if isinstance(metrics, list):
        _print_metrics_list(metrics)
    else:
        _print_metrics_dict(metrics)
    click.echo()


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
            return

        click.echo("\n=== Available Datasets ===\n")

        datasets = definitions.get("datasets") if isinstance(definitions, dict) else None
        entries = _iter_datasets(datasets)
        if not entries:
            click.echo("Raw API response:")
            click.echo(json.dumps(definitions, indent=2))
            return

        for name, info in entries:
            _print_dataset_entry(name, info, descriptions)
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
            return

        click.echo(f"\n=== Dimensions for {click.style(dataset, bold=True, fg='cyan')} ({datarun}) ===\n")
        _print_attributes(dataset_info)
        _print_dimensions_section(dataset_info)
        _print_metrics_section(dataset_info)
    except Exception as e:
        click.echo(f"Error fetching dimensions: {e}", err=True)
        sys.exit(1)


def _hierarchy_level(item: dict) -> int:
    if "level" in item:
        return int(item.get("level", 0))
    if "level_name" in item:
        return int(item.get("level_name", "0")) - 1
    return 0


def _print_hierarchy_item(item: dict) -> None:
    level = _hierarchy_level(item)
    indent = "  " * level
    name = item.get("name", "Unknown")
    code = item.get("display_id") or item.get("child") or item.get("id", "")
    if level == 0:
        click.echo(f"{indent}{click.style(name, bold=True)} [{code}]")
    else:
        click.echo(f"{indent}  {name} [{code}]")


def _print_hierarchy(items: list, limit: int) -> None:
    shown = 0
    for item in items:
        if limit > 0 and shown >= limit:
            click.echo(f"\n... and {len(items) - shown} more items")
            break
        if isinstance(item, dict):
            _print_hierarchy_item(item)
            shown += 1


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
            _print_hierarchy_csv(conn, dataset, dimension, datarun, limit)
            return

        hierarchy_data = conn.get_meta_dataset_dimension(dataset, dimension, datarun)
        if output_json:
            click.echo(json.dumps(hierarchy_data, indent=2))
            return

        click.echo(f"\n=== Hierarchy for {click.style(dimension, bold=True, fg='cyan')} in {dataset} ({datarun}) ===\n")
        if isinstance(hierarchy_data, dict) and "hierarchy" in hierarchy_data:
            _print_hierarchy(hierarchy_data["hierarchy"], limit)
            click.echo()
        else:
            click.echo(json.dumps(hierarchy_data, indent=2))
    except Exception as e:
        click.echo(f"Error fetching hierarchy: {e}", err=True)
        sys.exit(1)


def _print_hierarchy_csv(conn: CoreLMIConnection, dataset: str, dimension: str, datarun: str, limit: int) -> None:
    """Fetch the hierarchy as a DataFrame and print it as CSV (optionally limited)."""
    df = conn.get_dimension_hierarchy_df(dataset, dimension, datarun)
    if limit > 0 and len(df) > limit:
        df = df.head(limit)
        click.echo(f"# Showing first {limit} items", err=True)
    click.echo(df.to_csv(index=False))


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
