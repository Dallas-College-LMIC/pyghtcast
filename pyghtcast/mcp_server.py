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

import argparse
import logging
import os
import secrets as _secrets
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

from .coreLmi import CoreLMIConnection

logger = logging.getLogger("pyghtcast.mcp")

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


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    """Liveness/readiness probe for k8s. Unauthenticated by design."""
    return JSONResponse({"status": "ok"})


def load_api_keys() -> set[str]:
    """Parse the PYGHTCAST_API_KEYS env var (comma-separated) into a key set."""
    raw = os.environ.get("PYGHTCAST_API_KEYS", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


class ApiKeyMiddleware:
    """Raw ASGI middleware gating requests on an X-API-Key header allowlist.

    Deliberately not Starlette's BaseHTTPMiddleware: that buffers responses,
    which breaks the SSE streaming the Streamable HTTP transport uses.
    /health stays open so the k8s probe works without a key. An empty
    allowlist fails closed (rejects everything) rather than open.
    """

    def __init__(self, app: Any, api_keys: set[str], exempt_paths: tuple[str, ...] = ("/health",)) -> None:
        self.app = app
        self.api_keys = api_keys
        self.exempt_paths = exempt_paths

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope["path"] in self.exempt_paths:
            await self.app(scope, receive, send)
            return

        provided = ""
        for name, value in scope.get("headers", []):
            if name == b"x-api-key":
                provided = value.decode()
                break

        # compare_digest over every key (no early exit) to stay timing-safe.
        valid = False
        for key in self.api_keys:
            if _secrets.compare_digest(key, provided):
                valid = True
        if valid:
            logger.info("authorized request key=%s… path=%s", provided[:8], scope["path"])
            await self.app(scope, receive, send)
            return

        logger.warning("rejected request key=%s… path=%s", provided[:8] if provided else "<none>", scope["path"])
        response = JSONResponse({"error": "invalid or missing API key"}, status_code=401)
        await response(scope, receive, send)


def _transport_security() -> TransportSecuritySettings | None:
    """DNS-rebinding protection config from PYGHTCAST_ALLOWED_HOSTS.

    FastMCP validates the Host header on the /mcp endpoint when binding
    non-localhost; without this, requests arriving via a public hostname get
    "Invalid Host header". Comma-separated hostnames; port variants are
    allowed automatically.
    """
    raw = os.environ.get("PYGHTCAST_ALLOWED_HOSTS", "")
    hosts = [h.strip() for h in raw.split(",") if h.strip()]
    if not hosts:
        return None
    allowed_hosts: list[str] = []
    for h in hosts:
        allowed_hosts += [h, f"{h}:80", f"{h}:443"]
    return TransportSecuritySettings(
        allowed_hosts=allowed_hosts,
        allowed_origins=[f"https://{h}" for h in hosts],
    )


def build_http_app() -> ApiKeyMiddleware:
    """The Streamable HTTP ASGI app wrapped in API-key auth."""
    security = _transport_security()
    if security is not None:
        mcp.settings.transport_security = security
    return ApiKeyMiddleware(mcp.streamable_http_app(), api_keys=load_api_keys())


def main() -> None:
    """Entry point for the `pyghtcast-mcp` console script.

    Default is stdio (local hosts spawn us as a subprocess). --transport
    streamable-http serves HTTP with the API-key gate, for remote deployment.
    """
    parser = argparse.ArgumentParser(prog="pyghtcast-mcp")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run()
        return

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    if not load_api_keys():
        logger.warning("PYGHTCAST_API_KEYS is empty: all MCP requests will be rejected (fail-closed)")
    uvicorn.run(build_http_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
