"""MCP server exposing pyghtcast's CoreLMI (Lightcast Agnitio) surface to LLMs.

Run locally over stdio (default transport) after installing the optional extra:

    uv run --with "pyghtcast[mcp]" pyghtcast-mcp          # or, once installed:
    pyghtcast-mcp

Credentials are read from LCAPI_USER / LCAPI_PASS, mirroring the CLI. The
CoreLMIConnection is constructed lazily and cached as a module global so the
OAuth token and the per-instance rate limiter (300 req / 5 min) survive across
tool calls; constructing a fresh connection per call would burn an auth request
every time and reset the limiter.

Results are returned as plain dicts; in mcp 1.x these serialize to JSON text
content, which LLM hosts read directly. The `limit` on the data-returning tools
is a context-window guard, not pagination -- real responses can hold thousands
of rows.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from .coreLmi import CoreLMIConnection

mcp = FastMCP("pyghtcast")

# Cached CoreLMIConnection (lazy singleton). See module docstring.
_conn: CoreLMIConnection | None = None


def get_connection() -> CoreLMIConnection:
    """Return the cached CoreLMIConnection, creating it from env creds on first use.

    Raises RuntimeError if LCAPI_USER / LCAPI_PASS are not set.
    """
    global _conn
    if _conn is not None:
        return _conn

    username = os.environ.get("LCAPI_USER")
    password = os.environ.get("LCAPI_PASS")
    if not username or not password:
        raise RuntimeError("LCAPI_USER and LCAPI_PASS environment variables must be set")

    _conn = CoreLMIConnection(username, password)
    return _conn


@mcp.tool()
def list_datasets() -> dict:
    """List every available Lightcast CoreLMI (Agnitio) dataset with its versions.

    Use this first to discover which datasets (e.g. emsi.us.occupation,
    emsi.us.industry) your credentials can access and which dataruns/versions
    each one offers before calling describe_dataset or query_corelmi.
    """
    return get_connection().get_meta_definitions()


@mcp.tool()
def describe_dataset(dataset: str, datarun: str) -> dict:
    """Describe one dataset for a given datarun: its dimensions and available metrics.

    Args:
        dataset: dataset name, e.g. "emsi.us.occupation" or "emsi.us.industry".
        datarun: data version, e.g. "2025.3" (find valid values via list_datasets).

    The metrics names returned here are the column names you pass to
    query_corelmi (e.g. "Jobs.2022", "MedianHourlyEarnings.2022").
    """
    return get_connection().get_meta_dataset(dataset, datarun)


@mcp.tool()
def dimension_hierarchy(dataset: str, dimension: str, datarun: str, limit: int = 50) -> dict:
    """View the hierarchy (tree of codes/names) of one dimension within a dataset.

    Args:
        dataset: dataset name, e.g. "emsi.us.occupation".
        dimension: dimension name, e.g. "Area", "Occupation", "Industry".
        datarun: data version, e.g. "2025.3".
        limit: cap on items returned (default 50). Use the codes/ids in the
            returned items as predicates in query_corelmi constraints.

    Returns count (total available) and truncated (whether `limit` was hit), so
    callers can tell a full result from a sliced one.
    """
    raw = get_connection().get_meta_dataset_dimension(dataset, dimension, datarun)
    hierarchy = raw.get("hierarchy", []) if isinstance(raw, dict) else []
    count = len(hierarchy)
    truncated = count > limit
    return {
        "dataset": dataset,
        "dimension": dimension,
        "datarun": datarun,
        "hierarchy": hierarchy[:limit] if truncated else hierarchy,
        "count": count,
        "truncated": truncated,
        "limit": limit,
    }


@mcp.tool()
def query_corelmi(
    dataset: str,
    metrics: list[str],
    constraints: list[dict] | None = None,
    datarun: str = "2025.3",
    limit: int = 50,
) -> dict:
    """Query a CoreLMI dataset and get back rows as JSON records.

    Args:
        dataset: dataset name, e.g. "emsi.us.occupation".
        metrics: column names to retrieve (see describe_dataset), e.g.
            ["Jobs.2022", "MedianHourlyEarnings.2022"].
        constraints: optional list of filter objects, each shaped like
            {"dimensionName": "Area", "mapLevel": {"level": 4, "predicate": ["48113"]}}.
            Omit for totals across the whole dataset.
        datarun: data version, e.g. "2025.3" (default "2025.3").
        limit: cap on rows returned (default 50) to keep the response small.

    Returns row_count (total rows the query matched), truncated (whether `limit`
    was hit), columns, and the rows themselves.
    """
    constraints = constraints or []
    query = {"metrics": [{"name": c} for c in metrics], "constraints": constraints}
    df = get_connection().post_retrieve_df(dataset, query, datarun)

    count = len(df)
    truncated = count > limit
    if truncated:
        df = df.head(limit)
    return {
        "dataset": dataset,
        "datarun": datarun,
        "columns": list(df.columns),
        "rows": df.to_dict(orient="records"),
        "row_count": count,
        "truncated": truncated,
        "limit": limit,
    }


def main() -> None:
    """Entry point for the `pyghtcast-mcp` console script. Runs the stdio server."""
    mcp.run()


if __name__ == "__main__":
    main()
