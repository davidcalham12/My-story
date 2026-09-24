---
name: fastmcp
description: Building a Model Context Protocol (MCP) server in Python with FastMCP — declaring tools from typed functions, read-only annotations, errors a client can read, running over stdio, registering the server in a client, and testing it with the in-memory client. Use when adding or changing a tool on `mcp_server/`, exposing project data to an MCP client, or deciding whether an MCP tool may write.
---

# FastMCP: an MCP server from typed Python functions

Source: FastMCP's own documentation at gofastmcp.com (servers/tools,
deployment/running-server, patterns/testing) and the docstrings of the
installed package, read on 2026-09-24 against `fastmcp==4.0.9`. Licence of
FastMCP: Apache-2.0. This skill carries no code to run and downloads nothing.

## In this project

- The server is `mcp_server/server.py` and it is **read-only** (SPEC-EXAM-005,
  O2). A write tool is out of scope: on this system a write is a reader change,
  and a reader change spends money. Do not add one without a spec that names it.
- It has **its own virtual environment**, `mcp_server/.venv`, pinned in
  `mcp_server/requirements.txt`. Never install FastMCP into the backend's
  Python: its dependency tree is large and the backend suite must not change.
- Its tests are `mcp_server/tests/`, run with the venv's Python. They are
  outside `backend/tests`, which is the root `testpaths`, so the backend suite
  never collects them.

## Declaring a tool

- Create one `FastMCP("name", instructions=...)` instance and decorate plain
  functions with `@mcp.tool`. In this version the decorator returns the
  **original function**, so a test can call it directly as well as over MCP.
- The tool's name is the function's name; its description is the docstring.
  Write the docstring for the client's model: what comes back and what `null`
  means.
- The **input schema is generated from the type hints**, and arguments are
  validated before the function runs: a string where an `int` is declared is
  refused with a validation error and the function is never called. That is a
  boundary, not a courtesy — keep parameters as narrow types (`int`, `str`),
  never a free-form path.
- The **output schema comes from the return annotation**. A `dict` or a Pydantic
  model becomes structured content; a list or a primitive is wrapped as
  `{"result": ...}`.
- Sync functions run in a thread pool by default; async functions run on the
  event loop. A short SQLite read is fine as a sync function.

## Annotations

`annotations=` takes `readOnlyHint`, `destructiveHint`, `idempotentHint`,
`openWorldHint` and `title`. They are **hints to the client**, not enforcement.
Here every tool declares `readOnlyHint: true`, and the enforcement is elsewhere:
the SQLite connection is opened with `mode=ro` and no tool accepts a path.

## Errors

Raise `fastmcp.exceptions.ToolError` for a failure the caller should read
("no run X", "version must be a positive integer"). Its message always reaches
the client, even with `mask_error_details=True`, which hides the details of
every other exception. On the client side the in-memory `Client` raises the same
`ToolError` from `call_tool`.

## Running and registering

- `mcp.run()` defaults to the **stdio** transport. Keep it under
  `if __name__ == "__main__":`. `transport="http"` exists for a networked
  server; this project does not use it.
- On stdio, **stdout belongs to the protocol**. Never `print` to it; logs go to
  stderr. `show_banner=False` suppresses the start-up banner.
- A client registers a stdio server by `command`, `args` and optional `env`
  (the `mcpServers` object of `.mcp.json` or a desktop client's config). Point
  `command` at the venv's Python, not at `python` on the PATH.

## Testing

- Use the in-memory client: `Client(mcp)` as an async context manager, then
  `await client.list_tools()` and `await client.call_tool(name, arguments)`.
  The result's `.data` is the deserialised return value and
  `.structured_content` the raw JSON object. No subprocess, no network.
- Without `pytest-asyncio`, wrap the async body in `asyncio.run(...)` inside an
  ordinary test.
- Test the refusals as well as the answers: a bad type, a missing row, and — for
  a read-only server — a write attempted through the server's own connection.
