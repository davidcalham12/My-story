"""Reading runs back. SQL out, behind the service."""

from __future__ import annotations

import sqlite3


def list_runs(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT id, slug, premise, profile, tone, stage, halted, halted_detail, "
        "source, started_at, finished_at FROM runs ORDER BY started_at DESC"
    )]


def get_run(conn: sqlite3.Connection, run_id: str) -> dict | None:
    row = conn.execute(
        "SELECT id, slug, premise, profile, tone, stage, halted, halted_detail, "
        "source, started_at, finished_at FROM runs WHERE id = ?", (run_id,)
    ).fetchone()
    return dict(row) if row else None


def attempts_with_scores(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    rows = [dict(r) for r in conn.execute(
        "SELECT id, chapter, attempt, aggregate, verdict, promoted FROM attempts "
        "WHERE run_id = ? ORDER BY chapter, attempt", (run_id,)
    )]
    for row in rows:
        row["scores"] = {
            s["characteristic"]: s["score"]
            for s in conn.execute(
                "SELECT characteristic, score FROM scores WHERE attempt_id = ?",
                (row.pop("id"),),
            )
        }
        row["promoted"] = bool(row["promoted"])
    return rows


def cost(conn: sqlite3.Connection, run_id: str) -> dict:
    """What the run cost, and how the figures were obtained.

    Imported runs carry one total with no split, graded `reconstructed`; v2 runs
    carry both halves. Mixing them into one number without saying so is how
    $6.21 came to stand in for $49.33.
    """
    row = conn.execute(
        "SELECT COUNT(*) AS calls, COALESCE(SUM(input_tokens),0) AS input_tokens, "
        "COALESCE(SUM(output_tokens),0) AS output_tokens, "
        "COALESCE(SUM(cost_usd),0) AS total_usd FROM calls WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    kinds = [r["provenance"] for r in conn.execute(
        "SELECT DISTINCT provenance FROM calls WHERE run_id = ?", (run_id,))]
    return {**dict(row), "provenance": sorted(kinds)}


def warnings(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT kind, detail, chapter, ts FROM run_warnings WHERE run_id = ? "
        "ORDER BY id", (run_id,))]


def completeness(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    """What an imported run did NOT carry. A gap reads as a gap, never a zero."""
    return [dict(r) for r in conn.execute(
        "SELECT field, state, note FROM run_completeness WHERE run_id = ? "
        "AND state != 'present' ORDER BY field", (run_id,))]
