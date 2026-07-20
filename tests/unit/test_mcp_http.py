"""Unit tests for the MCP server's HTTP transport: API-key auth + health probe.

The API-key middleware is a raw ASGI wrapper (not BaseHTTPMiddleware, which
buffers responses and breaks the SSE streaming that Streamable HTTP relies on).
Tests exercise it against a dummy ASGI app, and against the real FastMCP
streamable-http app via Starlette's TestClient for the /health path.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from pyghtcast.mcp_server import ApiKeyMiddleware, build_http_app, load_api_keys, main


def _dummy_app() -> Starlette:
    async def ok(request):  # type: ignore[no-untyped-def]
        return JSONResponse({"reached": True})

    return Starlette(routes=[Route("/mcp", ok, methods=["GET", "POST"]), Route("/health", ok)])


def _client(keys: set[str]) -> TestClient:
    app = _dummy_app()
    wrapped = ApiKeyMiddleware(app, api_keys=keys)
    return TestClient(wrapped, raise_server_exceptions=False)


class TestApiKeyMiddleware:
    def test_missing_key_rejected(self) -> None:
        client = _client({"sekrit"})
        resp = client.get("/mcp")
        assert resp.status_code == 401

    def test_wrong_key_rejected(self) -> None:
        client = _client({"sekrit"})
        resp = client.get("/mcp", headers={"X-API-Key": "wrong"})
        assert resp.status_code == 401

    def test_valid_key_accepted(self) -> None:
        client = _client({"sekrit"})
        resp = client.get("/mcp", headers={"X-API-Key": "sekrit"})
        assert resp.status_code == 200
        assert resp.json() == {"reached": True}

    def test_any_of_multiple_keys_accepted(self) -> None:
        client = _client({"alpha", "beta"})
        assert client.get("/mcp", headers={"X-API-Key": "beta"}).status_code == 200

    def test_health_exempt_from_auth(self) -> None:
        client = _client({"sekrit"})
        assert client.get("/health").status_code == 200

    def test_no_keys_configured_rejects_all(self) -> None:
        # Fail closed: empty allowlist means nobody gets in (not everybody).
        client = _client(set())
        assert client.get("/mcp", headers={"X-API-Key": "anything"}).status_code == 401


class TestLoadApiKeys:
    @patch.dict(os.environ, {"PYGHTCAST_API_KEYS": "key1,key2, key3 "})
    def test_parses_comma_separated_and_strips(self) -> None:
        assert load_api_keys() == {"key1", "key2", "key3"}

    @patch.dict(os.environ, {"PYGHTCAST_API_KEYS": ""})
    def test_empty_env_gives_empty_set(self) -> None:
        assert load_api_keys() == set()

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_env_gives_empty_set(self) -> None:
        assert load_api_keys() == set()

    @patch.dict(os.environ, {"PYGHTCAST_API_KEYS": "a,,b,"})
    def test_ignores_empty_entries(self) -> None:
        assert load_api_keys() == {"a", "b"}


class TestBuildHttpApp:
    @patch.dict(os.environ, {"PYGHTCAST_API_KEYS": "goodkey"})
    def test_health_route_no_key_needed(self) -> None:
        client = TestClient(build_http_app(), raise_server_exceptions=False)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    @patch.dict(os.environ, {"PYGHTCAST_API_KEYS": "goodkey"})
    def test_mcp_endpoint_requires_key(self) -> None:
        client = TestClient(build_http_app(), raise_server_exceptions=False)
        resp = client.post("/mcp", json={})
        assert resp.status_code == 401

    @patch.dict(os.environ, {"PYGHTCAST_API_KEYS": "goodkey"})
    def test_mcp_endpoint_with_key_passes_auth(self) -> None:
        client = TestClient(build_http_app(), raise_server_exceptions=False)
        # With a valid key the request reaches the MCP transport layer.
        # It won't be a valid MCP session (no initialize handshake), but it
        # must NOT be a 401 -- any other status proves auth passed.
        resp = client.post("/mcp", json={}, headers={"X-API-Key": "goodkey"})
        assert resp.status_code != 401


class TestMainTransports:
    @patch("pyghtcast.mcp_server.mcp")
    def test_default_is_stdio(self, mock_mcp: MagicMock) -> None:
        with patch("sys.argv", ["pyghtcast-mcp"]):
            main()
        mock_mcp.run.assert_called_once_with()

    @patch("pyghtcast.mcp_server.uvicorn")
    @patch("pyghtcast.mcp_server.build_http_app")
    def test_streamable_http_runs_uvicorn(self, mock_build: MagicMock, mock_uvicorn: MagicMock) -> None:
        mock_app = MagicMock()
        mock_build.return_value = mock_app
        with patch(
            "sys.argv", ["pyghtcast-mcp", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8080"]
        ):
            main()
        mock_uvicorn.run.assert_called_once_with(mock_app, host="0.0.0.0", port=8080)
