# The MCP server — query and download the novels

SPEC-EXAM-005, item O2. The exam's optional "MCP server to query and download
novels", added beside the system and never inside it.

## 1. Purpose

An MCP client (Claude Code, a desktop client, any MCP host) can ask which
novels storyMaker has written, which versions of each were published, what
every validator said about a version, what the run cost, and where a version's
PDF is so it can be downloaded. It answers from the same SQLite archive and
`output/` directory the backend writes. It never writes to either, and it
never calls a model.

## 2. Where it is

| file | what |
|---|---|
| `mcp_server/server.py` | the server: five tools, FastMCP, stdio |
| `mcp_server/tests/test_server.py` | its tests, against a temporary archive |
| `mcp_server/requirements.txt` | its pinned dependencies (`fastmcp==4.0.9`, `pytest==9.1.1`) |
| `mcp_server/.gitignore` | keeps its virtual environment out of git |
| `.claude/skills/fastmcp/SKILL.md` | the skill for the new technology (AGENTS.md §5) |

No existing file was changed. The backend, frontend, config, agents and schema
are untouched.

## 3. Installing and running

The server has **its own virtual environment**, so the backend's Python and its
dependencies stay exactly as they were:

```bash
python -m venv mcp_server/.venv
mcp_server/.venv/Scripts/python -m pip install -r mcp_server/requirements.txt   # Windows
# mcp_server/.venv/bin/python on Linux/macOS
```

Run it over stdio (an MCP client normally launches it for you):

```bash
mcp_server/.venv/Scripts/python mcp_server/server.py
```

Configuration, both read at call time:

| variable | default | meaning |
|---|---|---|
| `NOVAFORGE_DB` | `<repo>/novaforge.db` | the archive; the same variable the backend reads |
| `NOVAFORGE_OUTPUT_DIR` | `<repo>/output` | where each run's files and `dist/v{n}/novel.pdf` live |

## 4. Registering it in a client

A snippet for a project `.mcp.json` (the repository's own `.mcp.json` is **not**
edited by this change; merge the entry by hand if wanted). Use absolute paths
on Windows:

```json
{
  "mcpServers": {
    "storymaker-novels": {
      "command": "C:/path/to/storyMaker/mcp_server/.venv/Scripts/python.exe",
      "args": ["C:/path/to/storyMaker/mcp_server/server.py"],
      "env": {
        "NOVAFORGE_DB": "C:/path/to/storyMaker/novaforge.db",
        "NOVAFORGE_OUTPUT_DIR": "C:/path/to/storyMaker/output"
      }
    }
  }
}
```

## 5. The tools

Every tool is annotated `readOnlyHint: true, destructiveHint: false,
idempotentHint: true, openWorldHint: false`. A `null` is absent, never zero.
Errors come back as MCP tool errors with a readable message.

| tool | input | output |
|---|---|---|
| `list_novels` | — | list of `{id, slug, title, stage, halted, started_at, finished_at, versions}` — `title` from `backend.commons.title.title_of` (book heading, `state.json` title, outline heading, humanised slug); `versions` is the count of published versions |
| `novel_versions` | `run_id: str` | list of `{n, parent, reason, created_at, pdf}` from the `versions` table; `pdf` is whether `dist/v{n}/novel.pdf` exists on disk |
| `novel_validations` | `run_id: str`, `version: int` | list of `{validator, kind, criterion, value, justification, ts}` from the `validations` table, as stored (`value` is text; `null` means the validator ran and had no answer) |
| `novel_cost` | `run_id: str` | `{total_usd, provenance, turns, duration_ms, subagent_dispatches}` from `output/<slug>/cost.json`, provenance as stored in the file; with no `cost.json`, `{total_usd: null, provenance: "absent", why}` |
| `novel_pdf` | `run_id: str`, `version: int` | `{path, bytes, media_type}` — the absolute path and size of the PDF of a **published** version |

`novel_pdf` refuses: an unknown run; a version that is not a positive integer
(the input schema rejects a string before the function runs); a version with no
row in `versions` (a halted regeneration leaves a `dist/v{n}/` and no row, and
is not a published version); a version whose PDF was never printed; a slug in
the database that is not of the pipeline's shape or would resolve outside the
output directory.

## 6. Why read-only, and how it is enforced

The spec's reason: a write tool would be a reader change, and a reader change
spends money (SPEC-EXAM-005 §3). The enforcement does not rest on the
annotation, which is only a hint to the client:

1. **The database is opened read-only by SQLite**:
   `sqlite3.connect("file:<path>?mode=ro", uri=True)`. An `INSERT` or `DELETE`
   through that connection raises `sqlite3.OperationalError`; a test proves it,
   and a mutation check (the same test with `?mode=ro` removed) fails, so the
   test is testing something. A missing database is reported, not created.
2. **No tool takes a filesystem path.** A PDF is reached by run id and version
   number; the path is derived from the run's slug in the database, the same
   decision `backend/publish/router_versions.py` made for the panel.
3. **No model is called.** Every answer is a query or a file stat.

## 7. Verification

| check | result | letter |
|---|---|---|
| `mcp_server/tests` with the venv's Python | 16 passed | T |
| a write through the server's connection raises `OperationalError` | passes; fails when `mode=ro` is removed | T |
| backend suite unchanged: `USE_RECORDED_STREAM=true python -m pytest backend/tests -q -p no:faulthandler` | 791 passed, 5 skipped | T |
| smoke test over stdio against the real archive | below | D |

### Smoke test, 2026-09-24

The server was launched over stdio by a FastMCP client with the owner's real
`novaforge.db` and `output/`, and every tool was called for every run. The
database file's SHA-256 and modification time were identical before and after.

| run | title | stage / halted | versions (PDF bytes) | validations | cost |
|---|---|---|---|---|---|
| `02412b7fe29e` | The Other Side of the Hill | complete | v1 (159,829), v2 (192,854) | 16, 25 | 74.20 USD, measured |
| `8ab6c57af9f6` | Stone Collector Birthday Adventure | FLOW-4 / user | v1 (59,757) | 9 | null, absent (no `cost.json`) |
| `8834d0ab189a` | The Key | FLOW-3 / budget | v1 (65,563) | 9 | 25.80 USD, measured |
| `8dc162a1d8ec` | (title carries a first name; not repeated here) | complete | none | — | 14.86 USD, measured |
| `db2fed5bd97a` | (title carries a first name; not repeated here) | FLOW-3 / context | none | — | 1.40 USD, measured |

Every returned PDF path existed. A `novel_pdf` call with `version: "../../x"`
was refused with a tool error.

## 8. Gaps

| gap | level | why accepted |
|---|---|---|
| local (stdio) and read-only | incidental | SPEC-EXAM-005 §5: the exam asks to query and download; writing costs money |
| the client downloads by reading the returned local path; the server does not stream the PDF's bytes | incidental | the server and the client share a machine over stdio; the path is derived, never supplied |
| the tests use a minimal copy of the schema, not the migrations | incidental | the smoke test runs against the real, migrated archive |
