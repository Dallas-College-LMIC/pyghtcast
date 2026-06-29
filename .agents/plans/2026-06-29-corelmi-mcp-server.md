# Plan: CoreLMI MCP Server for pyghtcast

**Date:** 2026-06-29
**Status:** Approved, ready to execute

## Goal

Expose pyghtcast's CoreLMI (Agnitio) read/query surface to LLMs over the Model Context Protocol (stdio transport), letting Claude Desktop / Claude Code / other MCP hosts call Lightcast labor-market data as tools.

## Locked decisions

| Decision | Choice |
|---|---|
| MCP library | Official `mcp` SDK, v1.x stable — `from mcp.server.fastmcp import FastMCP` |
| Version pin | `mcp[cli]>=1.27,<2` (v2 is alpha until ~2026-07-27) |
| Tool scope | Curated CoreLMI subset only (no skills, no job-postings/profiles) |
| Transport | stdio only (`mcp.run()` default) |
| Packaging | Optional `[mcp]` extra + `pyghtcast-mcp` console script |
| Method | Red-Green-Refactor TDD (project rule) |

### Why not alternatives
- **Standalone FastMCP 2.x/3.0 (Prefect):** composition, proxying, OpenAPI ingest, sampling — all YAGNI for one fixed local tool set.
- **FastAPI-MCP:** wraps existing FastAPI apps; pyghtcast has none.
- **Official SDK v2 alpha:** breaking changes each pre-release; stable in ~4 weeks; revisit then (migration = class rename + minor tweaks).
- **Official low-level server:** protocol-level control unnecessary here.

## Tool surface (4 tools, all read-only)

| Tool | Wraps | Returns |
|---|---|---|
| `list_datasets()` | `get_meta_definitions()` | datasets + versions (JSON) |
| `describe_dataset(dataset, datarun)` | `get_meta_dataset()` | dimensions + metrics (JSON) |
| `dimension_hierarchy(dataset, dimension, datarun, limit=50)` | `get_meta_dataset_dimension()` | hierarchy items (JSON, capped) |
| `query_corelmi(dataset, metrics, constraints, datarun="2025.3", limit=50)` | `build_query_corelmi` + `query_corelmi` | DataFrame → JSON records (capped) |

- `limit` on query/hierarchy = LLM-context-window guard, not pagination (real result sets can be 10k rows). `ponytail:`-style knob.
- `constraints` passed through verbatim — same shape as library/CLI examples, no new schema for the LLM to learn.

## Credentials handling

Same as existing CLI: env vars `LCAPI_USER` / `LCAPI_PASS`. MCP adds nothing new.

**Flow:**
1. User sets creds in MCP host config under `env`:
   ```json
   {
     "mcpServers": {
       "pyghtcast": {
         "command": "uvx",
         "args": ["--from", "pyghtcast[mcp]", "pyghtcast-mcp"],
         "env": { "LCAPI_USER": "...", "LCAPI_PASS": "..." }
       }
     }
   }
   ```
2. Host spawns server as stdio subprocess, injects `env`.
3. Server reads `os.environ` in `get_connection()` — mirrors `cli.py`'s `get_connection()`, reuses `EmsiBaseConnection.__init__` fallback.
4. `CoreLMIConnection.__init__` does OAuth2 `client_credentials` POST (`base.py:get_new_token`). Token cached on instance, auto-refreshed at 59min by `Token.is_expired()` check inside `download_data`. **MCP layer never touches the token.**

**Two design rules:**
1. **No `sys.exit` on missing creds.** CLI does `sys.exit(1)` — fine for one-shot, **kills the whole long-running server** if copied in. Raise a clear error instead; LLM gets the message, server stays up.
2. **Cache connection as module global, not per-call.**
   - `CoreLMIConnection.__init__` calls `get_new_token()` in constructor → per-call = 1 auth request per tool call (waste).
   - `Limiter` (300/5min rate state) lives on instance → per-call = fresh limiter = loses throttling = 429 risk.
   - Solution: lazy singleton. Construct on first tool call, reuse. Lib handles refresh + rate-limit internally.

**Security:** creds plaintext in host config (inherent to stdio MCP model); same exposure as CLI's gitignored `.env`. Creds never in code/git/logs.

---

## Steps

### 1. pyproject.toml — declare deps + script
- [x] Add `[project.optional-dependencies] mcp = ["mcp[cli]>=1.27,<2"]`
- [x] Add `anyio` and `mcp[cli]>=1.27,<2` to `dev` extra (async MCP tests + mypy typechecks the new module). Skipped `inline-snapshot` (YAGNI — explicit asserts).
- [x] Add console script: `pyghtcast-mcp = "pyghtcast.mcp_server:main"`
- [x] Run `uv lock` to refresh `uv.lock` (resolved `mcp v1.28.1`)
- [x] Verified flake.nix needs NO change to devShell: pre-commit mypy `binPath` extended with `p.mcp` (nixpkgs provides mcp 1.12.4) so the hook typechecks mcp too. **Decision journey:** initially tried a `[[tool.mypy.overrides]]` for `mcp.*` (3-line suppression), then tried switching the hook to `uv run --extra dev mypy` (uv-as-source-of-truth) for zero version drift — but that broke `nix build .#checks.x86_64-linux.pre-commit-check` / `nix flake check` because uv cannot run in the pure sandbox (no /bin/sh, no network, no .venv). Final fix: add `p.mcp` to the existing nix `withPackages` env (sandbox-compatible, override removed). nix mcp is 1.12.4 vs runtime 1.28.1, but **verified equivalent** — both catch identical API-misuse errors (FastMCP `.run()` transport Literal type, `@tool` return types). uv remains source of truth for the dev workflow (`uv run --extra dev mypy pyghtcast`).

### 2. RED — write `tests/unit/test_mcp.py` first (fails: module doesn't exist)
- [x] Import `from pyghtcast.mcp_server import mcp, get_connection, main`
- [x] Use `create_connected_server_and_client_session(mcp)` + `ClientSession`, async via anyio (`@pytest.mark.anyio`, `anyio_backend = "asyncio"` fixture)
- [x] `test_tools_registered` — `list_tools()` contains the 4 names
- [x] `test_list_datasets` — patch `get_connection` → mock returns definitions dict; call `list_datasets`; assert passthrough
- [x] `test_describe_dataset` — mock `get_meta_dataset`; assert dims/metrics passed through + correct args
- [x] `test_dimension_hierarchy_limit` — mock returns 100 items, `limit=5`; assert exactly 5 returned + `count`/`truncated`
- [x] `test_query_corelmi` — mock `post_retrieve_df` returns a DataFrame; assert built query shape + rows capped by `limit` + `row_count`/`truncated`
- [x] `test_query_corelmi_builds_constraints` — split into `test_query_builds_payload_and_caps_rows` (payload shape) + `test_query_default_constraints_empty` (constraints default to `[]`)
- [x] `test_missing_credentials` — empty env → `get_connection` raises `RuntimeError` matching `LCAPI_USER`
- [x] Run: confirmed red (`ModuleNotFoundError: No module named 'pyghtcast.mcp_server'`)

**Finding during RED (pre-emptive):** verified in mcp 1.28.1 that dict/list returns serialize to `content[0].text` (JSON), NOT `structuredContent` (only scalars get structuredContent). Tests parse `content[0].text`. `json_response=True` does not change this. Structured outputs would require per-tool Pydantic output models → YAGNI.

### 3. GREEN — create `pyghtcast/mcp_server.py` (single module)
- [x] `from mcp.server.fastmcp import FastMCP`
- [x] `mcp = FastMCP("pyghtcast")`
- [x] `get_connection()` factory reading `LCAPI_USER`/`LCAPI_PASS` from env, raising `RuntimeError` if missing (no `sys.exit`). Lazy singleton via module-global `_conn`.
- [x] 4 `@mcp.tool()` functions; DataFrames → `df.to_dict(orient="records")` with `limit` cap; `count`/`row_count` + `truncated` flags reported back
- [x] `def main() -> None: mcp.run()` + `if __name__ == "__main__": main()`
- [x] **Design call:** used `CoreLMIConnection` directly (matches CLI), inlined the 4-line query builder rather than the `Lightcast` wrapper (which lacks the meta methods). One connection class, one auth, one rate limiter.
- [x] Run tests → green (10/10)

### 4. REFACTOR — quality gate
- [x] `uv run --with ruff ruff check . --fix && ruff format .` (1 file reformatted)
- [x] `uv run --extra dev mypy pyghtcast` — clean, no issues in 8 source files
- [x] `uv run --extra dev pytest` — 24/24 pass; `mcp_server.py` at 100% coverage; nothing regressed
- [x] Kept module to one file (no `pyghtcast/mcp/` package — YAGNI)

### 5. Docs + dogfood
- [x] README: added "Using the MCP server" section — install (`pip install "pyghtcast[mcp]"` or `uvx --from pyghtcast[mcp] pyghtcast-mcp`), Claude Desktop/Claude Code config snippet with `LCAPI_USER`/`LCAPI_PASS` env, 4-tool table, `limit`/`truncated` semantics
- [x] Skipped dogfooding `.mcp.json`: requires real creds; would break the repo's own AI tooling on a fresh clone. User can opt in by copying the snippet from the README.

### 6. Sanity-run
- [x] Console script `pyghtcast-mcp` resolves via `importlib.metadata`
- [x] Live in-memory `list_tools` confirms 4 tools register: `describe_dataset`, `dimension_hierarchy`, `list_datasets`, `query_corelmi`
- [x] Full suite green under `uv run --extra dev pytest` (24/24)

---

## Skipped / add-when-needed

- Skills API tools (out of scope now)
- Job-postings/profiles tools
- Streamable HTTP transport (add `--transport` flag later)
- OpenAPI auto-ingest / server composition (standalone FastMCP territory)
- Pagination beyond a `limit` cap
- OAuth bearer passthrough from host, vault integration, per-user auth
- Migration to official `mcp` v2 stable (~2026-07-27): class rename `FastMCP` → `MCPServer` + minor transport-arg tweaks
