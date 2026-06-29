"""Unit tests for the MCP server module.

Exercises the pyghtcast MCP server over an in-memory transport (no stdio, no
network) and mocks out the underlying CoreLMIConnection so no real Lightcast
credentials or calls are needed.

Note on result shape: in mcp 1.28.1 a tool returning a dict serializes the
dict as JSON text content (content[0].text); structuredContent stays None for
non-scalar returns. Tests therefore parse content[0].text.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from mcp.client.session import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session

from pyghtcast.mcp_server import get_connection, main, mcp

EXPECTED_TOOLS = {"list_datasets", "describe_dataset", "dimension_hierarchy", "query_corelmi"}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def session() -> AsyncGenerator[ClientSession]:
    async with create_connected_server_and_client_session(mcp) as s:
        yield s


def _text(result: object) -> str:
    """Pull the first text content block from a CallToolResult."""
    content = getattr(result, "content", [])
    for block in content:
        text = getattr(block, "text", None)
        if text is not None:
            return text
    raise AssertionError(f"no text content in {result!r}")


def _json(result: object) -> object:
    return json.loads(_text(result))


class TestToolRegistration:
    @pytest.mark.anyio
    async def test_all_tools_registered(self, session: ClientSession) -> None:
        result = await session.list_tools()
        names = {t.name for t in result.tools}
        assert EXPECTED_TOOLS <= names, f"missing tools: {EXPECTED_TOOLS - names}"


class TestListDatasets:
    @pytest.mark.anyio
    @patch("pyghtcast.mcp_server.get_connection")
    async def test_list_datasets_passthrough(self, mock_get_conn: MagicMock, session: ClientSession) -> None:
        mock_conn = MagicMock()
        mock_conn.get_meta_definitions.return_value = {
            "datasets": {"emsi.us.occupation": {"title": "US Occupation Data", "versions": ["2025.3"]}}
        }
        mock_get_conn.return_value = mock_conn

        result = await session.call_tool("list_datasets", {})

        mock_conn.get_meta_definitions.assert_called_once_with()
        data = _json(result)
        assert "datasets" in data
        assert "emsi.us.occupation" in data["datasets"]


class TestDescribeDataset:
    @pytest.mark.anyio
    @patch("pyghtcast.mcp_server.get_connection")
    async def test_describe_dataset_passthrough(self, mock_get_conn: MagicMock, session: ClientSession) -> None:
        mock_conn = MagicMock()
        mock_conn.get_meta_dataset.return_value = {
            "dimensions": {"Area": {"title": "Area"}},
            "metrics": {"Jobs.2022": {"title": "Jobs"}},
        }
        mock_get_conn.return_value = mock_conn

        result = await session.call_tool("describe_dataset", {"dataset": "emsi.us.occupation", "datarun": "2025.3"})

        mock_conn.get_meta_dataset.assert_called_once_with("emsi.us.occupation", "2025.3")
        data = _json(result)
        assert "dimensions" in data
        assert "metrics" in data


class TestDimensionHierarchy:
    @pytest.mark.anyio
    @patch("pyghtcast.mcp_server.get_connection")
    async def test_hierarchy_truncated_to_limit(self, mock_get_conn: MagicMock, session: ClientSession) -> None:
        mock_conn = MagicMock()
        mock_conn.get_meta_dataset_dimension.return_value = {
            "hierarchy": [{"id": str(i), "name": f"row{i}"} for i in range(100)]
        }
        mock_get_conn.return_value = mock_conn

        result = await session.call_tool(
            "dimension_hierarchy",
            {
                "dataset": "emsi.us.occupation",
                "dimension": "Occupation",
                "datarun": "2025.3",
                "limit": 5,
            },
        )

        mock_conn.get_meta_dataset_dimension.assert_called_once_with("emsi.us.occupation", "Occupation", "2025.3")
        data = _json(result)
        assert isinstance(data, dict)
        assert len(data["hierarchy"]) == 5
        assert data["count"] == 100
        assert data["truncated"] is True
        assert data["limit"] == 5

    @pytest.mark.anyio
    @patch("pyghtcast.mcp_server.get_connection")
    async def test_hierarchy_not_truncated_when_under_limit(
        self, mock_get_conn: MagicMock, session: ClientSession
    ) -> None:
        mock_conn = MagicMock()
        mock_conn.get_meta_dataset_dimension.return_value = {"hierarchy": [{"id": "0"}, {"id": "1"}]}
        mock_get_conn.return_value = mock_conn

        result = await session.call_tool(
            "dimension_hierarchy",
            {"dataset": "d", "dimension": "Occupation", "datarun": "2025.3"},
        )

        data = _json(result)
        assert len(data["hierarchy"]) == 2
        assert data["count"] == 2
        assert data["truncated"] is False


class TestQueryCorelmi:
    @pytest.mark.anyio
    @patch("pyghtcast.mcp_server.get_connection")
    async def test_query_builds_payload_and_caps_rows(self, mock_get_conn: MagicMock, session: ClientSession) -> None:
        mock_conn = MagicMock()
        mock_conn.post_retrieve_df.return_value = pd.DataFrame({"Jobs.2022": [10, 20, 30], "Area": ["a", "b", "c"]})
        mock_get_conn.return_value = mock_conn

        constraints = [{"dimensionName": "Area", "mapLevel": {"level": 4, "predicate": ["48113"]}}]
        result = await session.call_tool(
            "query_corelmi",
            {
                "dataset": "emsi.us.occupation",
                "metrics": ["Jobs.2022", "Area"],
                "constraints": constraints,
                "datarun": "2025.3",
                "limit": 2,
            },
        )

        # Built query shape: metrics -> [{name:...}], constraints passed through.
        mock_conn.post_retrieve_df.assert_called_once_with(
            "emsi.us.occupation",
            {
                "metrics": [{"name": "Jobs.2022"}, {"name": "Area"}],
                "constraints": constraints,
            },
            "2025.3",
        )
        data = _json(result)
        assert isinstance(data, dict)
        assert data["row_count"] == 3
        assert data["truncated"] is True
        assert data["limit"] == 2
        assert len(data["rows"]) == 2
        assert data["rows"][0]["Jobs.2022"] == 10

    @pytest.mark.anyio
    @patch("pyghtcast.mcp_server.get_connection")
    async def test_query_default_constraints_empty(self, mock_get_conn: MagicMock, session: ClientSession) -> None:
        mock_conn = MagicMock()
        mock_conn.post_retrieve_df.return_value = pd.DataFrame({"Jobs.2022": [1]})
        mock_get_conn.return_value = mock_conn

        await session.call_tool(
            "query_corelmi",
            {"dataset": "emsi.us.occupation", "metrics": ["Jobs.2022"]},
        )

        _args, payload, _dr = mock_conn.post_retrieve_df.call_args.args
        assert payload["metrics"] == [{"name": "Jobs.2022"}]
        assert payload["constraints"] == []


class TestGetConnection:
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials_raises(self) -> None:
        # No cached connection from prior tests.
        with patch("pyghtcast.mcp_server._conn", None):
            with pytest.raises(RuntimeError, match="LCAPI_USER"):
                get_connection()

    @patch.dict(os.environ, {"LCAPI_USER": "u", "LCAPI_PASS": "p"})
    @patch("pyghtcast.mcp_server.CoreLMIConnection")
    def test_caches_connection_across_calls(self, mock_cls: MagicMock) -> None:
        with patch("pyghtcast.mcp_server._conn", None):
            first = get_connection()
            second = get_connection()
        assert first is second
        mock_cls.assert_called_once()


class TestMain:
    @patch("pyghtcast.mcp_server.mcp")
    def test_main_invokes_run(self, mock_mcp: MagicMock) -> None:
        main()
        mock_mcp.run.assert_called_once_with()
