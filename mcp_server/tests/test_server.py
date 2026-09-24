"""The read-only MCP server, against a temporary archive (SPEC-EXAM-005 AC-3).

Run with the server's own environment, never the backend's:

    mcp_server/.venv/Scripts/python -m pytest mcp_server/tests -q

These tests live outside `backend/tests` and the root `pyproject.toml` points
pytest's `testpaths` there, so the backend suite never collects them.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server  # noqa: E402
from fastmcp import Client  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402

# The minimal slice of backend/commons/db/migrations the tools read:
# 001_runs.sql (columns used), 012_versions.sql, 013_validations.sql.
SCHEMA = """
CREATE TABLE runs (
  id TEXT PRIMARY KEY, slug TEXT NOT NULL UNIQUE, premise TEXT NOT NULL,
  stage TEXT NOT NULL, halted TEXT, started_at TEXT NOT NULL, finished_at TEXT
) STRICT;
CREATE TABLE versions (
  run_id TEXT NOT NULL REFERENCES runs(id), n INTEGER NOT NULL CHECK (n >= 1),
  parent INTEGER CHECK (parent IS NULL OR parent < n), reason TEXT NOT NULL,
  created_at TEXT NOT NULL, PRIMARY KEY (run_id, n),
  CHECK (parent IS NOT NULL OR n = 1)
) STRICT;
CREATE TABLE validations (
  id INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
  version INTEGER NOT NULL, validator TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('a','b','c','d')), criterion TEXT,
  value TEXT, justification TEXT, ts TEXT NOT NULL
) STRICT;
"""


@pytest.fixture
def archive(tmp_path, monkeypatch):
    db = tmp_path / "novaforge.db"
    out = tmp_path / "output"
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO runs VALUES (?,?,?,?,?,?,?)", [
        ("r1", "the-hill", "p", "complete", None, "2026-09-24T10:00:00Z", "2026-09-24T11:00:00Z"),
        ("r2", "no-cost-run", "p", "FLOW-3", "budget", "2026-09-24T12:00:00Z", None),
        ("r3", "../escape", "p", "FLOW-1", None, "2026-09-24T13:00:00Z", None),
    ])
    conn.executemany("INSERT INTO versions VALUES (?,?,?,?,?)", [
        ("r1", 1, None, "first publication", "2026-09-24T11:00:00Z"),
        ("r1", 2, 1, "a reader change", "2026-09-24T12:00:00Z"),
    ])
    conn.executemany(
        "INSERT INTO validations (run_id, version, validator, kind, criterion, value, "
        "justification, ts) VALUES (?,?,?,?,?,?,?,?)", [
            ("r1", 1, "schema_brief", "a", None, "pass", None, "t"),
            ("r1", 1, "human_review", "b", None, None, None, "t"),
            ("r1", 2, "judge_rubric", "b", "mean", "8.33", "because", "t"),
        ])
    conn.commit()
    conn.close()

    hill = out / "the-hill"
    (hill / "dist" / "v1").mkdir(parents=True)
    (hill / "dist" / "v1" / "novel.pdf").write_bytes(b"%PDF-1.4 test")
    (hill / "dist" / "v3").mkdir()                       # a halted regeneration
    (hill / "dist" / "v3" / "novel.pdf").write_bytes(b"%PDF halted")
    (hill / "outline.md").write_text("# Outline — The Other Side of the Hill\n", encoding="utf-8")
    (hill / "cost.json").write_text(json.dumps(
        {"total_cost_usd": 7.5, "provenance": "measured", "turns": 10}), encoding="utf-8")
    (out / "no-cost-run").mkdir()

    monkeypatch.setenv("NOVAFORGE_DB", str(db))
    monkeypatch.setenv("NOVAFORGE_OUTPUT_DIR", str(out))
    return db


def test_a_write_through_the_servers_connection_is_refused(archive):
    conn = server.connect()
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("INSERT INTO versions VALUES ('r2', 1, NULL, 'x', 't')")
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM runs")
    finally:
        conn.close()
    check = sqlite3.connect(archive)
    assert check.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 3
    check.close()


def test_a_missing_database_is_not_created(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVAFORGE_DB", str(tmp_path / "nothing.db"))
    with pytest.raises(ToolError):
        server.list_novels()
    assert not (tmp_path / "nothing.db").exists()


def test_list_novels_titles_from_the_outline_and_the_slug(archive):
    novels = {n["id"]: n for n in server.list_novels()}
    assert novels["r1"]["title"] == "The Other Side of the Hill"
    assert novels["r1"]["versions"] == 2
    assert novels["r2"]["title"] == "No Cost Run"
    assert novels["r2"]["halted"] == "budget"
    assert novels["r3"]["title"] is None          # a slug that is not a slug names no file


def test_novel_versions_reads_pdf_presence_off_the_disk(archive):
    assert server.novel_versions("r1") == [
        {"n": 1, "parent": None, "reason": "first publication",
         "created_at": "2026-09-24T11:00:00Z", "pdf": True},
        {"n": 2, "parent": 1, "reason": "a reader change",
         "created_at": "2026-09-24T12:00:00Z", "pdf": False},
    ]
    assert server.novel_versions("r2") == []
    with pytest.raises(ToolError):
        server.novel_versions("nope")


def test_novel_validations_keeps_null_as_null(archive):
    rows = server.novel_validations("r1", 1)
    assert [(r["validator"], r["value"]) for r in rows] == [
        ("human_review", None), ("schema_brief", "pass")]
    assert server.novel_validations("r1", 2)[0]["justification"] == "because"
    assert server.novel_validations("r1", 9) == []


def test_novel_cost_absent_is_absent_never_zero(archive):
    assert server.novel_cost("r1")["total_usd"] == 7.5
    assert server.novel_cost("r1")["provenance"] == "measured"
    absent = server.novel_cost("r2")
    assert absent["total_usd"] is None and absent["provenance"] == "absent"


def test_novel_pdf_path_and_size(archive, tmp_path):
    pdf = server.novel_pdf("r1", 1)
    assert Path(pdf["path"]) == (tmp_path / "output" / "the-hill" / "dist" / "v1"
                                 / "novel.pdf").resolve()
    assert Path(pdf["path"]).is_absolute()
    assert pdf["bytes"] == len(b"%PDF-1.4 test")


@pytest.mark.parametrize("run_id, version", [
    ("r1", 2),        # published, never printed
    ("r1", 3),        # a directory on disk with no row: a halted regeneration
    ("r1", 0),
    ("r1", -1),
    ("r1", True),
    ("r1", "1/../../x"),
    ("nope", 1),
    ("r3", 1),        # the database's slug would leave the output directory
])
def test_novel_pdf_refuses_anything_but_a_published_printed_version(archive, run_id, version):
    with pytest.raises(ToolError):
        server.novel_pdf(run_id, version)


def test_the_tools_answer_over_mcp_and_declare_themselves_read_only(archive):
    async def call():
        async with Client(server.mcp) as client:
            tools = await client.list_tools()
            result = await client.call_tool("novel_pdf", {"run_id": "r1", "version": 1})
            with pytest.raises(ToolError):
                await client.call_tool("novel_pdf", {"run_id": "r1", "version": "../x"})
            return tools, result

    tools, result = asyncio.run(call())
    assert {t.name for t in tools} == {
        "list_novels", "novel_versions", "novel_validations", "novel_cost", "novel_pdf"}
    assert all(t.annotations.read_only_hint for t in tools)
    assert result.data["bytes"] == len(b"%PDF-1.4 test")
