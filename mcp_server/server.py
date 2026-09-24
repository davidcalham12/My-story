"""A read-only MCP server over the novels storyMaker has written (SPEC-EXAM-005, O2).

An MCP client can list the novels, see each one's published versions, what
every validator said about a version, what the run cost, and where the PDF of
a version is so it can be downloaded. Nothing else.

Read-only on purpose, and by construction rather than by promise:

- the database is opened with `mode=ro`, so a write through this server's
  connection is refused by SQLite itself (`sqlite3.OperationalError`);
- no tool takes a filesystem path. A PDF is reached by run id and version
  number, and the path is derived here from the run's own slug in the
  database, the same decision `backend/publish/router_versions.py` made;
- no tool calls a model. A write tool would be a reader change, and a reader
  change spends money (SPEC-EXAM-005 §3).

Configuration, read at call time so a test can point it elsewhere:

- `NOVAFORGE_DB` — the SQLite database (default `<repo>/novaforge.db`), the
  same variable the backend reads;
- `NOVAFORGE_OUTPUT_DIR` — the output directory (default `<repo>/output`).

Run over stdio: `mcp_server/.venv/Scripts/python mcp_server/server.py`.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

REPO = Path(__file__).resolve().parent.parent

# The title is the backend's own function when it can be imported, so the
# client sees the title the PDF cover and the panel show. It is standard
# library only; importing it pulls in nothing the backend runs on.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
try:
    from backend.commons.title import title_of
except ImportError:  # pragma: no cover - only when the server is moved out of the repo
    _SMALL = {"a", "an", "and", "at", "by", "for", "in", "of", "on", "or", "the", "to", "with"}

    def title_of(run_dir: Path) -> str:
        """Minimal fallback: the outline's first heading, else the humanised slug."""
        outline = run_dir / "outline.md"
        if outline.is_file():
            for line in outline.read_text(encoding="utf-8").splitlines():
                if line.startswith("# "):
                    return line[2:].strip()
        words = [w for w in re.split(r"[-_\s]+", run_dir.name) if w]
        return " ".join(w if (i and w in _SMALL) else w[:1].upper() + w[1:]
                        for i, w in enumerate(words))

#: A slug as the pipeline writes it. Anything else coming out of the database
#: is refused before it is joined onto a path.
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

_READ_ONLY = {"readOnlyHint": True, "destructiveHint": False,
              "idempotentHint": True, "openWorldHint": False}

mcp = FastMCP(
    "storymaker-novels",
    instructions=(
        "Read-only access to the novels storyMaker has written: list them, see "
        "their published versions, validator verdicts and cost, and get the "
        "absolute path of a version's PDF to download it. No tool writes, and "
        "none calls a model. A null value means absent, never zero."
    ),
)


def db_path() -> Path:
    return Path(os.environ.get("NOVAFORGE_DB") or REPO / "novaforge.db")


def output_dir() -> Path:
    return Path(os.environ.get("NOVAFORGE_OUTPUT_DIR") or REPO / "output")


def connect() -> sqlite3.Connection:
    """The only connection this server opens: read-only, enforced by SQLite."""
    path = db_path()
    if not path.is_file():
        # `mode=ro` will not create a file, but say it plainly rather than
        # surface SQLite's "unable to open database file".
        raise ToolError(f"no database at {path}")
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _run(conn: sqlite3.Connection, run_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT id, slug FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise ToolError(f"no run {run_id!r}")
    return row


def _run_dir(slug: str) -> Path:
    """`<output>/<slug>`, only for a slug of the pipeline's own shape, and only
    if the result stays inside the output directory."""
    if not _SLUG.fullmatch(slug or ""):
        raise ToolError(f"run slug {slug!r} is not a pipeline slug; refused")
    root = output_dir().resolve()
    path = (root / slug).resolve()
    if path.parent != root:
        raise ToolError("path escapes the output directory; refused")
    return path


def _version_number(version: int) -> int:
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ToolError(f"version must be a positive integer, got {version!r}")
    return version


def _pdf(run_dir: Path, n: int) -> Path:
    return run_dir / "dist" / f"v{n}" / "novel.pdf"


@mcp.tool(annotations=_READ_ONLY)
def list_novels() -> list[dict]:
    """Every run in the archive: id, slug, title, stage, why it halted (null
    while running or when it completed) and how many versions were published."""
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT r.id, r.slug, r.stage, r.halted, r.started_at, r.finished_at, "
            "(SELECT COUNT(*) FROM versions v WHERE v.run_id = r.id) AS versions "
            "FROM runs r ORDER BY r.started_at").fetchall()
    novels = []
    for row in rows:
        try:
            title = title_of(_run_dir(row["slug"]))
        except ToolError:
            title = None
        novels.append({"id": row["id"], "slug": row["slug"], "title": title,
                       "stage": row["stage"], "halted": row["halted"],
                       "started_at": row["started_at"], "finished_at": row["finished_at"],
                       "versions": row["versions"]})
    return novels


@mcp.tool(annotations=_READ_ONLY)
def novel_versions(run_id: str) -> list[dict]:
    """The published versions of one run, oldest first: number, parent, why it
    was published, when, and whether its PDF was actually printed (read off the
    disk, not assumed from the row)."""
    with closing(connect()) as conn:
        run = _run(conn, run_id)
        rows = conn.execute(
            "SELECT n, parent, reason, created_at FROM versions "
            "WHERE run_id = ? ORDER BY n", (run_id,)).fetchall()
    run_dir = _run_dir(run["slug"])
    return [{**dict(row), "pdf": _pdf(run_dir, row["n"]).is_file()} for row in rows]


@mcp.tool(annotations=_READ_ONLY)
def novel_validations(run_id: str, version: int) -> list[dict]:
    """Every validator's verdict on one version, as stored. `value` is text
    because validators do not share a scale; null means the validator ran and
    had no answer, and a missing row means nobody ran it."""
    n = _version_number(version)
    with closing(connect()) as conn:
        _run(conn, run_id)
        rows = conn.execute(
            "SELECT validator, kind, criterion, value, justification, ts "
            "FROM validations WHERE run_id = ? AND version = ? "
            "ORDER BY validator, criterion, id", (run_id, n)).fetchall()
    return [dict(row) for row in rows]


@mcp.tool(annotations=_READ_ONLY)
def novel_cost(run_id: str) -> dict:
    """What the run cost, from output/<slug>/cost.json with its provenance as
    stored there. With no cost.json the total is null and the provenance is
    `absent`: a run that reported no total is not a free run."""
    with closing(connect()) as conn:
        run = _run(conn, run_id)
    path = _run_dir(run["slug"]) / "cost.json"
    if not path.is_file():
        return {"total_usd": None, "provenance": "absent",
                "why": "no cost.json: the run reported no total"}
    raw = json.loads(path.read_text(encoding="utf-8"))
    cost = {"total_usd": raw.get("total_cost_usd"),
            "provenance": raw.get("provenance"),
            "turns": raw.get("turns"),
            "duration_ms": raw.get("duration_ms", raw.get("wall_clock_ms")),
            "subagent_dispatches": raw.get("subagent_dispatches")}
    if cost["provenance"] is None:
        cost["why"] = ("cost.json does not state its provenance"
                       + (f"; its source is {raw['source']!r}" if raw.get("source") else ""))
    return cost


@mcp.tool(annotations=_READ_ONLY)
def novel_pdf(run_id: str, version: int) -> dict:
    """The absolute path and size in bytes of a published version's PDF, for
    the client to download. The path is derived only from the run's slug in the
    database and the version number; no path is accepted from the caller."""
    n = _version_number(version)
    with closing(connect()) as conn:
        run = _run(conn, run_id)
        published = conn.execute(
            "SELECT 1 FROM versions WHERE run_id = ? AND n = ?", (run_id, n)).fetchone()
    if published is None:
        # A halted regeneration leaves a dist/v{n}/ behind and no row; it is not
        # a version anybody published.
        raise ToolError(f"run {run_id!r} has no published version {n}")
    path = _pdf(_run_dir(run["slug"]), n)
    if not path.is_file():
        raise ToolError(f"version {n} of run {run_id!r} has no printed PDF")
    return {"path": str(path), "bytes": path.stat().st_size,
            "media_type": "application/pdf"}


if __name__ == "__main__":
    # stdio; no banner, because it advertises a hosting service and says nothing
    # about the novels.
    mcp.run(show_banner=False)
