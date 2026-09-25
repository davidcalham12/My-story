"""The `changes` rows' cost columns. SQL here, nowhere else in this feature.

A row's figures are **added to as each `result` arrives** (SPEC-EXAM-008 §3),
so a change cut halfway still shows what it spent. NULL means absent: a figure
starts NULL and only a measured `result` makes it a number, so a process that
never reported leaves it NULL rather than 0.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Iterable

from backend.commons.db.connection import tx
from backend.costs.measure import Measured, Meter

#: The note a Python-loop process leaves on its change (§8.3): neither 0 nor absent.
NO_ORCHESTRATOR = "no orchestrator (python loop)"
#: A result without `modelUsage` for a non-zero total: the split cannot be made.
SPLIT_ABSENT = "split absent: a result without modelUsage"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def open_change(conn: sqlite3.Connection, run_id: str, *, kind: str,
                version: int | None = None, chapters: Iterable[int] | None = None,
                label: str | None = None, started_at: str | None = None,
                orchestrator_model: str | None = None, chapter_loop: str | None = None,
                note: str | None = None) -> int:
    """A new row at the run's next `n`; returns that `n`."""
    with tx(conn):
        n = int(conn.execute("SELECT COALESCE(MAX(n), 0) + 1 FROM changes WHERE run_id = ?",
                             (run_id,)).fetchone()[0])
        conn.execute(
            "INSERT INTO changes (run_id, n, kind, label, version, chapters, started_at, "
            "orchestrator_model, chapter_loop, note, results, unresulted, sources) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,0,0,'[]')",
            (run_id, n, kind, label, version,
             json.dumps(sorted(chapters)) if chapters is not None else None,
             started_at or _now(), orchestrator_model, chapter_loop, note))
    return n


def _row(conn, run_id: str, n: int) -> dict | None:
    row = conn.execute("SELECT * FROM changes WHERE run_id = ? AND n = ?",
                       (run_id, n)).fetchone()
    return dict(row) if row else None


def _plus(a, b):
    """Sum that keeps absent absent: None + None is None, a number starts it."""
    if b is None:
        return a
    return b if a is None else a + b


def _models(held: str | None, new: str | None) -> str | None:
    names = [m for m in (held or "").split(", ") if m]
    for m in (new or "").split(", "):
        if m and m not in names:
            names.append(m)
    return ", ".join(names) or None


def _with_note(held: str | None, note: str) -> str:
    parts = [p for p in (held or "").split("; ") if p]
    if note not in parts:
        parts.append(note)
    return "; ".join(parts)


def _incomplete(held: str | None, count: int) -> str:
    parts = [p for p in (held or "").split("; ")
             if p and not p.startswith("incomplete: ")]
    if count:
        noun = "process" if count == 1 else "processes"
        parts.append(f"incomplete: {count} {noun} without a result")
    return "; ".join(parts)


def add_result(conn: sqlite3.Connection, run_id: str, n: int, m: Measured, *,
               source: str | None = None, note: str | None = None) -> None:
    """One `result`, added to change `n`. Its own transaction."""
    with tx(conn):
        row = _row(conn, run_id, n)
        if row is None:
            return
        split_absent = SPLIT_ABSENT in (row["note"] or "") or not m.split
        text = row["note"]
        if not m.split:
            text = _with_note(text, SPLIT_ABSENT)
        if note:
            text = _with_note(text, note)
        sources = json.loads(row["sources"] or "[]")
        if source and source not in sources:
            sources.append(source)
        minutes = _plus(row["minutes"] if row["results"] else None, m.minutes)
        conn.execute(
            "UPDATE changes SET total_usd = ?, minutes = ?, orchestrator_model = ?, "
            "orchestrator_usd = ?, agents_model = ?, agents_usd = ?, provenance = ?, "
            "results = ?, sources = ?, note = ? WHERE run_id = ? AND n = ?",
            (_plus(row["total_usd"] if row["results"] else None, m.total_usd), minutes,
             _models(row["orchestrator_model"] if row["results"] else None,
                     m.orchestrator_model) or row["orchestrator_model"],
             None if split_absent else _plus(row["orchestrator_usd"], m.orchestrator_usd),
             _models(row["agents_model"], m.agents_model),
             None if split_absent else _plus(row["agents_usd"], m.agents_usd),
             "measured", int(row["results"] or 0) + 1, json.dumps(sources), text or None,
             run_id, n))


def add_missing(conn: sqlite3.Connection, run_id: str, n: int, count: int,
                why: str | None = None) -> None:
    """`count` processes of change `n` ended without a `result`: absent."""
    if count <= 0 and not why:
        return
    with tx(conn):
        row = _row(conn, run_id, n)
        if row is None:
            return
        total = int(row["unresulted"] or 0) + max(count, 0)
        text = _incomplete(row["note"], total)
        if why:
            text = _with_note(text, why)
        conn.execute(
            "UPDATE changes SET unresulted = ?, note = ?, provenance = ? "
            "WHERE run_id = ? AND n = ?",
            (total, text or None, row["provenance"] if row["results"] else "absent",
             run_id, n))


def add_note(conn: sqlite3.Connection, run_id: str, n: int, note: str) -> None:
    with tx(conn):
        row = _row(conn, run_id, n)
        if row is not None:
            conn.execute("UPDATE changes SET note = ? WHERE run_id = ? AND n = ?",
                         (_with_note(row["note"], note), run_id, n))


def finish(conn: sqlite3.Connection, run_id: str, n: int) -> None:
    """The change ended. A row that never received a `result` is absent."""
    with tx(conn):
        conn.execute(
            "UPDATE changes SET finished_at = COALESCE(finished_at, ?), "
            "provenance = COALESCE(provenance, 'absent') WHERE run_id = ? AND n = ?",
            (_now(), run_id, n))


def record_stream(conn: sqlite3.Connection, run_id: str | None, n: int | None,
                  events: Iterable[dict], *, meter: Meter | None = None,
                  source: str | None = None, note: str | None = None) -> Meter:
    """Fold a whole finished stream into change `n`: each `result` added, and
    whatever the meter saw start and never finish counted as absent."""
    meter = meter or Meter()
    for event in events:
        measured = meter.observe(event)
        if measured is not None and run_id and n is not None:
            add_result(conn, run_id, n, measured, source=source, note=note)
    if run_id and n is not None:
        add_missing(conn, run_id, n, meter.unresulted)
    return meter


def observe(conn: sqlite3.Connection, run_id: str, n: int, meter: Meter | None,
            event: dict) -> Meter:
    """One stream event of a live process; returns the meter to keep.

    The meter's configured model is the row's `orchestrator_model` — what the
    change was opened with, the `--model` its processes are launched with."""
    if meter is None:
        row = conn.execute("SELECT orchestrator_model FROM changes WHERE run_id = ? "
                           "AND n = ?", (run_id, n)).fetchone()
        meter = Meter(configured=row["orchestrator_model"] if row else None)
    measured = meter.observe(event)
    if measured is not None:
        add_result(conn, run_id, n, measured)
    return meter


def rows(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    out = []
    for row in conn.execute("SELECT * FROM changes WHERE run_id = ? ORDER BY n", (run_id,)):
        r = dict(row)
        r["chapters"] = json.loads(r["chapters"]) if r["chapters"] else None
        r["sources"] = json.loads(r["sources"]) if r.get("sources") else []
        out.append(r)
    return out


def total(change_rows: list[dict]) -> dict:
    """The novel's total across every change: what was measured, summed, and
    how many changes have no figure — counted, never added as 0."""
    known = [r for r in change_rows if r["total_usd"] is not None]
    absent = len(change_rows) - len(known)
    incomplete = sum(1 for r in known if r.get("unresulted"))
    grades = {r["provenance"] for r in known}
    return {
        "usd": float(sum(r["total_usd"] for r in known)) if known else None,
        "provenance": ("absent" if not known else
                       "measured" if grades <= {"measured"} else "reconstructed"),
        "changes": len(change_rows),
        "absent": absent,
        "incomplete": incomplete,
    }
